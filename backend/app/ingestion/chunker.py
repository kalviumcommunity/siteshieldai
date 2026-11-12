"""Structure-aware hierarchical chunker with atomic and header-repeated tables."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from app.ingestion.models import (
    DocumentChunk,
    ExtractedDocument,
    ExtractedLine,
    ExtractedTable,
    PageElement,
)
from app.ingestion.table_stitcher import format_table_markdown, stitch_document_elements
from app.schemas.documents import ContentType, DocumentIngestMetadata, ExtractionMethod

_DECIMAL_SECTION_RE = re.compile(r"^(\d+(?:\.\d+)+)\s+(.+)$")
_TOP_NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.+)$")
_CLAUSE_PREFIX_RE = re.compile(
    r"^(?:Section|Clause|Article|Part|Annex)\s+([A-Z0-9]+(?:\.[A-Z0-9]+)*)\b[:\-\s]*(.*)$",
    re.IGNORECASE,
)
_FEATURE_HEADING_RE = re.compile(r"^(Feature\s+\d+)\s*:\s*(.+)$", re.IGNORECASE)
_LIST_LINE_RE = re.compile(r"^(?:-\s+|\d+\.\s+)")

DEFAULT_TARGET_TOKENS = 420
DEFAULT_HARD_CAP_TOKENS = 600
DEFAULT_OVERLAP_TOKENS = 50
DEFAULT_ATOMIC_TABLE_TOKENS = 600


@dataclass(slots=True)
class _SectionHeading:
    level: int
    section_id: str | None
    title: str


def estimate_tokens(text: str) -> int:
    """Estimate token count deterministically without external tokenizer dependencies."""
    if not text.strip():
        return 1
    return max(len(text.split()), math.ceil(len(text) / 4))


def _detect_heading(line: ExtractedLine, body_font_size: float) -> _SectionHeading | None:
    """Detect section/clause headings using numbering patterns and typography."""
    text = line.text.strip()
    if not text or len(text) > 140:
        return None

    dec_match = _DECIMAL_SECTION_RE.match(text)
    if dec_match and (line.is_heading_hint or line.is_bold or line.font_size > body_font_size):
        sec_id = dec_match.group(1)
        level = len(sec_id.split("."))
        return _SectionHeading(level=level, section_id=sec_id, title=text)

    clause_match = _CLAUSE_PREFIX_RE.match(text)
    if clause_match and (line.is_heading_hint or line.is_bold or line.font_size > body_font_size):
        sec_id = clause_match.group(1)
        level = max(1, len(sec_id.split(".")))
        return _SectionHeading(level=level, section_id=sec_id, title=text)

    feat_match = _FEATURE_HEADING_RE.match(text)
    if feat_match and (line.is_heading_hint or line.is_bold or line.font_size > body_font_size):
        return _SectionHeading(level=3, section_id=feat_match.group(1), title=text)

    top_match = _TOP_NUMBERED_RE.match(text)
    if top_match:
        looks_like_heading = (
            line.is_heading_hint
            or line.font_size >= body_font_size + 1.5
            or (line.is_bold and ":" not in text and "→" not in text and not text.endswith("."))
        )
        if looks_like_heading:
            return _SectionHeading(level=1, section_id=top_match.group(1), title=text)

    if line.is_heading_hint or (
        line.is_bold and line.font_size >= body_font_size + 2.0 and not text.endswith(".")
    ):
        level = 1 if line.font_size >= body_font_size + 5.0 else 2
        return _SectionHeading(level=level, section_id=None, title=text)

    return None


def _classify_prose_or_list(lines: list[ExtractedLine], body_font_size: float) -> ContentType:
    content_lines = [ln for ln in lines if _detect_heading(ln, body_font_size) is None]
    if not content_lines:
        return ContentType.PROSE
    list_starts = sum(1 for ln in content_lines if _LIST_LINE_RE.match(ln.text.strip()))
    if list_starts >= 2 or list_starts * 2 >= len(content_lines):
        return ContentType.LIST
    return ContentType.PROSE


def _make_chunk_id(doc_id: str, chunk_index: int, text_verbatim: str) -> str:
    digest = hashlib.sha256(f"{doc_id}:{chunk_index}:{text_verbatim}".encode()).hexdigest()
    return f"chk_{digest[:16]}"


def _format_embedding_text(doc_title: str, section_path: list[str], text_verbatim: str) -> str:
    section_label = " > ".join(section_path) if section_path else "General"
    return f"[Doc: {doc_title} | Section: {section_label}]\n{text_verbatim}"


def _build_chunk(
    *,
    doc_id: str,
    doc_title: str,
    chunk_index: int,
    page_start: int,
    page_end: int,
    printed_page_label: str | None,
    section_id: str | None,
    section_path: list[str],
    content_type: ContentType,
    extraction_method: ExtractionMethod,
    ocr_confidence: float | None,
    char_start: int,
    text_verbatim: str,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=_make_chunk_id(doc_id, chunk_index, text_verbatim),
        doc_id=doc_id,
        chunk_index=chunk_index,
        page_start=page_start,
        page_end=page_end,
        printed_page_label=printed_page_label,
        section_id=section_id,
        section_path=list(section_path),
        content_type=content_type,
        extraction_method=extraction_method,
        ocr_confidence=ocr_confidence,
        char_start=char_start,
        char_end=char_start + len(text_verbatim),
        token_estimate=estimate_tokens(text_verbatim),
        text_for_embedding=_format_embedding_text(doc_title, section_path, text_verbatim),
        text_verbatim=text_verbatim,
    )


def _select_overlap_lines(lines: list[ExtractedLine], overlap_tokens: int) -> list[ExtractedLine]:
    if overlap_tokens <= 0 or not lines:
        return []
    selected: list[ExtractedLine] = []
    running_tokens = 0
    for ln in reversed(lines):
        tok = estimate_tokens(ln.text)
        if selected and running_tokens + tok > overlap_tokens:
            break
        selected.append(ln)
        running_tokens += tok
    selected.reverse()
    return selected


def chunk_extracted_document(
    extracted: ExtractedDocument,
    metadata: DocumentIngestMetadata,
    doc_id: str,
    *,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    hard_cap_tokens: int = DEFAULT_HARD_CAP_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    atomic_table_tokens: int = DEFAULT_ATOMIC_TABLE_TOKENS,
) -> list[DocumentChunk]:
    """Chunk an extracted document preserving section hierarchy, pages, and tables."""
    stream: list[PageElement] = stitch_document_elements(extracted.pages)
    page_lookup = {page.page_number: page for page in extracted.pages}

    chunks: list[DocumentChunk] = []
    stack: list[_SectionHeading] = []
    buffer_lines: list[ExtractedLine] = []
    char_cursor = 0

    def current_section_path() -> list[str]:
        return [item.title for item in stack]

    def current_section_id() -> str | None:
        for item in reversed(stack):
            if item.section_id:
                return item.section_id
        return None

    def page_method_and_label(
        page_start: int, page_end: int
    ) -> tuple[ExtractionMethod, float | None, str | None]:
        methods = {
            page_lookup[p].extraction_method
            for p in range(page_start, page_end + 1)
            if p in page_lookup
        }
        method = (
            ExtractionMethod.OCR if ExtractionMethod.OCR in methods else ExtractionMethod.NATIVE
        )
        confs = [
            page_lookup[p].ocr_confidence
            for p in range(page_start, page_end + 1)
            if p in page_lookup and page_lookup[p].ocr_confidence is not None
        ]
        avg_conf = round(sum(confs) / len(confs), 3) if confs else None
        printed = page_lookup[page_start].printed_page_label if page_start in page_lookup else None
        return method, avg_conf, printed

    def flush_line_buffer(*, keep_overlap: bool) -> None:
        nonlocal buffer_lines, char_cursor
        if not buffer_lines:
            return
        # Skip bodyless heading stubs; parent heading context remains on stack for child chunks.
        if all(_detect_heading(ln, extracted.body_font_size) is not None for ln in buffer_lines):
            buffer_lines = []
            return
        text_verbatim = "\n".join(ln.text for ln in buffer_lines).strip()
        if not text_verbatim:
            buffer_lines = []
            return
        p_start = min(ln.page_number for ln in buffer_lines)
        p_end = max(ln.page_number for ln in buffer_lines)
        method, avg_conf, printed = page_method_and_label(p_start, p_end)
        chunk = _build_chunk(
            doc_id=doc_id,
            doc_title=metadata.doc_title,
            chunk_index=len(chunks),
            page_start=p_start,
            page_end=p_end,
            printed_page_label=printed,
            section_id=current_section_id(),
            section_path=current_section_path(),
            content_type=_classify_prose_or_list(buffer_lines, extracted.body_font_size),
            extraction_method=method,
            ocr_confidence=avg_conf,
            char_start=char_cursor,
            text_verbatim=text_verbatim,
        )
        chunks.append(chunk)
        char_cursor += len(text_verbatim) + 1
        buffer_lines = _select_overlap_lines(buffer_lines, overlap_tokens) if keep_overlap else []

    def emit_table(table: ExtractedTable) -> None:
        nonlocal char_cursor
        full_md = format_table_markdown(table)
        method, avg_conf, printed = page_method_and_label(table.page_start, table.page_end)

        if estimate_tokens(full_md) <= atomic_table_tokens or len(table.rows) <= 1:
            row_batches = [table.rows]
        else:
            row_batches = []
            batch: list[list[str]] = []
            for row in table.rows:
                candidate = [*batch, row]
                if (
                    batch
                    and estimate_tokens(format_table_markdown(table, candidate))
                    > atomic_table_tokens
                ):
                    row_batches.append(batch)
                    batch = [row]
                else:
                    batch = candidate
            if batch:
                row_batches.append(batch)

        for batch_rows in row_batches:
            table_md = format_table_markdown(table, batch_rows)
            chunk = _build_chunk(
                doc_id=doc_id,
                doc_title=metadata.doc_title,
                chunk_index=len(chunks),
                page_start=table.page_start,
                page_end=table.page_end,
                printed_page_label=printed,
                section_id=current_section_id(),
                section_path=current_section_path(),
                content_type=ContentType.TABLE,
                extraction_method=method,
                ocr_confidence=avg_conf,
                char_start=char_cursor,
                text_verbatim=table_md,
            )
            chunks.append(chunk)
            char_cursor += len(table_md) + 1

    for elem in stream:
        if elem.kind == "table" and elem.table is not None:
            flush_line_buffer(keep_overlap=False)
            emit_table(elem.table)
            continue

        if elem.kind != "line" or elem.line is None:
            continue

        line = elem.line
        heading = _detect_heading(line, extracted.body_font_size)
        if heading is not None:
            flush_line_buffer(keep_overlap=False)
            while stack and stack[-1].level >= heading.level:
                stack.pop()
            stack.append(heading)
            buffer_lines = [line]
            continue

        buffer_lines.append(line)
        current_tokens = estimate_tokens("\n".join(ln.text for ln in buffer_lines))
        if current_tokens >= target_tokens and (
            current_tokens >= hard_cap_tokens or line.text.endswith((".", "!", "?", ":"))
        ):
            flush_line_buffer(keep_overlap=True)

    flush_line_buffer(keep_overlap=False)
    return chunks
