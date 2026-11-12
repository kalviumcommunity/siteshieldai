"""Page-level extractors for PDF (PyMuPDF + pdfplumber) and Markdown/text files."""

from __future__ import annotations

import hashlib
import io
import re
from collections.abc import Callable
from statistics import median

import pdfplumber
import pymupdf

from app.core.config import Settings
from app.core.exceptions import ValidationAppError
from app.ingestion.cleaner import clean_cell_text, clean_line_text, strip_running_headers_footers
from app.ingestion.models import (
    ExtractedDocument,
    ExtractedLine,
    ExtractedPage,
    ExtractedTable,
    PageElement,
)
from app.ingestion.validator import validate_document_input
from app.schemas.documents import ExtractionMethod

OcrCallback = Callable[[bytes, int], tuple[str, float | None]]

_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_MD_TABLE_SEP_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")


def _line_inside_any_bbox(
    line_bbox: tuple[float, float, float, float],
    table_bboxes: list[tuple[float, float, float, float]],
) -> bool:
    """Check whether the center of a text line lies inside an extracted table bbox."""
    cx = (line_bbox[0] + line_bbox[2]) / 2.0
    cy = (line_bbox[1] + line_bbox[3]) / 2.0
    for x0, y0, x1, y1 in table_bboxes:
        if (x0 - 2.0) <= cx <= (x1 + 2.0) and (y0 - 2.0) <= cy <= (y1 + 2.0):
            return True
    return False


def _extract_pdf_page_lines(
    page: pymupdf.Page,
    page_number: int,
    table_bboxes: list[tuple[float, float, float, float]],
) -> tuple[list[ExtractedLine], list[float]]:
    """Extract non-table lines and body font sizes from a digital PDF page."""
    text_dict = page.get_text("dict")
    lines: list[ExtractedLine] = []
    font_sizes: list[float] = []

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            raw_text = "".join(span.get("text", "") for span in spans)
            cleaned = clean_line_text(raw_text)
            if not cleaned:
                continue

            bbox = tuple(float(v) for v in line.get("bbox", (0.0, 0.0, 0.0, 0.0)))
            if _line_inside_any_bbox(bbox, table_bboxes):
                continue

            span_sizes = [float(span.get("size", 11.0)) for span in spans if span.get("text")]
            avg_size = sum(span_sizes) / len(span_sizes) if span_sizes else 11.0
            is_bold = any(
                (int(span.get("flags", 0)) & 16) or ("bold" in str(span.get("font", "")).lower())
                for span in spans
                if str(span.get("text", "")).strip()
            )
            font_sizes.append(avg_size)
            lines.append(
                ExtractedLine(
                    page_number=page_number,
                    text=cleaned,
                    y_top=bbox[1],
                    y_bottom=bbox[3],
                    font_size=round(avg_size, 2),
                    is_bold=is_bold,
                )
            )
    return lines, font_sizes


def _extract_pdf_tables(
    plumber_page: pdfplumber.page.Page,
    page_number: int,
) -> tuple[list[ExtractedTable], list[tuple[float, float, float, float]]]:
    """Extract vector-bordered tables from a pdfplumber page."""
    tables: list[ExtractedTable] = []
    bboxes: list[tuple[float, float, float, float]] = []

    for table in plumber_page.find_tables():
        raw_rows = table.extract() or []
        cleaned_rows = [[clean_cell_text(cell) for cell in row] for row in raw_rows]
        non_empty_rows = [row for row in cleaned_rows if any(cell for cell in row)]
        if len(non_empty_rows) < 2:
            continue

        bbox = tuple(float(v) for v in table.bbox)
        headers = non_empty_rows[0]
        data_rows = non_empty_rows[1:]
        tables.append(
            ExtractedTable(
                page_start=page_number,
                page_end=page_number,
                headers=headers,
                rows=data_rows,
                y_top=bbox[1],
                y_bottom=bbox[3],
            )
        )
        bboxes.append((bbox[0], bbox[1], bbox[2], bbox[3]))

    return tables, bboxes


def _extract_pdf(
    clean_name: str,
    data: bytes,
    checksum: str,
    ocr_fn: OcrCallback | None,
) -> ExtractedDocument:
    """Extract per-page text and tables from a PDF stream."""
    try:
        pdf_doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValidationAppError(
            f"Malformed PDF '{clean_name}': unable to parse file.",
            error_code="MALFORMED_DOCUMENT",
        ) from exc

    if pdf_doc.is_encrypted or pdf_doc.needs_pass:
        pdf_doc.close()
        raise ValidationAppError(
            f"PDF '{clean_name}' is encrypted or password-protected.",
            error_code="ENCRYPTED_DOCUMENT",
        )

    if len(pdf_doc) == 0:
        pdf_doc.close()
        raise ValidationAppError(
            f"PDF '{clean_name}' contains 0 pages.",
            error_code="EMPTY_DOCUMENT",
        )

    pages: list[ExtractedPage] = []
    all_font_sizes: list[float] = []
    doc_warnings: list[str] = []

    try:
        with pdfplumber.open(io.BytesIO(data)) as plumber_doc:
            for idx, page in enumerate(pdf_doc):
                page_num = idx + 1
                plumber_page = plumber_doc.pages[idx]
                page_height = float(page.rect.height)
                tables, table_bboxes = _extract_pdf_tables(plumber_page, page_num)
                lines, page_sizes = _extract_pdf_page_lines(page, page_num, table_bboxes)

                alnum_count = sum(ch.isalnum() for line in lines for ch in line.text)
                table_alnum = sum(
                    ch.isalnum()
                    for tbl in tables
                    for row in [tbl.headers, *tbl.rows]
                    for ch in "".join(row)
                )
                image_count = len(page.get_images())
                page_warnings: list[str] = []

                if (alnum_count + table_alnum) < 20 and image_count > 0:
                    extraction_method = ExtractionMethod.OCR
                    ocr_conf: float | None = None
                    if ocr_fn is not None:
                        png_bytes = page.get_pixmap(dpi=300).tobytes("png")
                        ocr_text, ocr_conf = ocr_fn(png_bytes, page_num)
                        for offset, raw_ocr_line in enumerate(ocr_text.splitlines()):
                            cleaned_ocr = clean_line_text(raw_ocr_line)
                            if cleaned_ocr:
                                y_pos = 72.0 + offset * 14.0
                                lines.append(
                                    ExtractedLine(
                                        page_number=page_num,
                                        text=cleaned_ocr,
                                        y_top=y_pos,
                                        y_bottom=y_pos + 12.0,
                                    )
                                )
                    else:
                        msg = (
                            f"Page {page_num} appears scanned/image-only; "
                            "local OCR engine is not configured."
                        )
                        page_warnings.append(msg)
                        doc_warnings.append(msg)
                else:
                    extraction_method = ExtractionMethod.NATIVE
                    ocr_conf = None

                all_font_sizes.extend(page_sizes)
                elements: list[PageElement] = [
                    PageElement(kind="line", page_number=page_num, y_top=ln.y_top, line=ln)
                    for ln in lines
                ]
                elements.extend(
                    PageElement(kind="table", page_number=page_num, y_top=tbl.y_top, table=tbl)
                    for tbl in tables
                )
                elements.sort(key=lambda item: item.y_top)

                pages.append(
                    ExtractedPage(
                        page_number=page_num,
                        page_height=page_height,
                        extraction_method=extraction_method,
                        ocr_confidence=ocr_conf,
                        elements=elements,
                        warnings=page_warnings,
                    )
                )
    except ValidationAppError:
        raise
    except Exception as exc:
        raise ValidationAppError(
            f"Malformed PDF '{clean_name}': error extracting pages.",
            error_code="MALFORMED_DOCUMENT",
        ) from exc
    finally:
        pdf_doc.close()

    pages = strip_running_headers_footers(pages)
    has_content = any(
        (elem.line and elem.line.text) or (elem.table and elem.table.rows)
        for page in pages
        for elem in page.elements
    )
    if not has_content:
        raise ValidationAppError(
            f"PDF '{clean_name}' produced no extractable text or tables.",
            error_code="EMPTY_DOCUMENT",
        )

    body_font_size = round(median(all_font_sizes), 2) if all_font_sizes else 11.0
    return ExtractedDocument(
        source_filename=clean_name,
        extension=".pdf",
        sha256_checksum=checksum,
        page_count=len(pages),
        pages=pages,
        body_font_size=body_font_size,
        warnings=doc_warnings,
    )


def _split_md_row(line: str) -> list[str]:
    trimmed = line.strip().strip("|")
    return [clean_cell_text(part) for part in trimmed.split("|")]


def _extract_text_or_markdown(
    clean_name: str,
    ext: str,
    data: bytes,
    checksum: str,
) -> ExtractedDocument:
    """Extract ordered lines and Markdown tables from UTF-8 `.md` or `.txt` files."""
    raw_lines = data.decode("utf-8-sig").splitlines()
    elements: list[PageElement] = []
    idx = 0
    y_cursor = 0.0

    while idx < len(raw_lines):
        raw = raw_lines[idx]
        stripped = raw.strip()
        # Detect Markdown pipe tables (header row + separator row)
        if (
            ext == ".md"
            and stripped.startswith("|")
            and idx + 1 < len(raw_lines)
            and _MD_TABLE_SEP_RE.match(raw_lines[idx + 1])
        ):
            headers = _split_md_row(raw)
            rows: list[list[str]] = []
            start_y = y_cursor
            idx += 2
            y_cursor += 2.0
            while idx < len(raw_lines) and raw_lines[idx].strip().startswith("|"):
                row = _split_md_row(raw_lines[idx])
                if len(row) < len(headers):
                    row.extend([""] * (len(headers) - len(row)))
                rows.append(row[: len(headers)])
                idx += 1
                y_cursor += 1.0
            if rows:
                tbl = ExtractedTable(
                    page_start=1,
                    page_end=1,
                    headers=headers,
                    rows=rows,
                    y_top=start_y,
                    y_bottom=y_cursor,
                )
                elements.append(PageElement(kind="table", page_number=1, y_top=start_y, table=tbl))
            continue

        cleaned = clean_line_text(raw)
        if cleaned:
            md_match = _MD_HEADING_RE.match(cleaned) if ext == ".md" else None
            if md_match:
                level = len(md_match.group(1))
                text = md_match.group(2).strip()
                font_size = max(12.0, 20.0 - (level * 1.5))
                is_bold = True
                is_heading_hint = True
            else:
                text = cleaned
                font_size = 11.0
                is_bold = False
                is_heading_hint = False

            line_obj = ExtractedLine(
                page_number=1,
                text=text,
                y_top=y_cursor,
                y_bottom=y_cursor + 1.0,
                font_size=font_size,
                is_bold=is_bold,
                is_heading_hint=is_heading_hint,
            )
            elements.append(PageElement(kind="line", page_number=1, y_top=y_cursor, line=line_obj))
        idx += 1
        y_cursor += 1.0

    page = ExtractedPage(
        page_number=1,
        page_height=max(1.0, y_cursor),
        extraction_method=ExtractionMethod.NATIVE,
        elements=elements,
    )
    return ExtractedDocument(
        source_filename=clean_name,
        extension=ext,
        sha256_checksum=checksum,
        page_count=1,
        pages=[page],
        body_font_size=11.0,
    )


def extract_document(
    filename: str,
    data: bytes,
    settings: Settings,
    ocr_fn: OcrCallback | None = None,
) -> ExtractedDocument:
    """Validate and extract structured page elements from supported formats."""
    clean_name, ext = validate_document_input(filename, data, settings)
    checksum = hashlib.sha256(data).hexdigest()

    if ext == ".pdf":
        return _extract_pdf(clean_name, data, checksum, ocr_fn=ocr_fn)
    return _extract_text_or_markdown(clean_name, ext, data, checksum)
