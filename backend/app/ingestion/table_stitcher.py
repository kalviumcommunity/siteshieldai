"""Cross-page table stitching and Markdown table serialization."""

from __future__ import annotations

from app.ingestion.models import ExtractedPage, ExtractedTable, PageElement


def _headers_match(a: list[str], b: list[str]) -> bool:
    """Compare two table header rows case-insensitively."""
    if len(a) != len(b) or not a:
        return False
    return [col.strip().lower() for col in a] == [col.strip().lower() for col in b]


def _merge_continuation_rows(target: ExtractedTable, continuation: ExtractedTable) -> None:
    """Merge rows from a cross-page continuation table into the parent table."""
    if not continuation.rows:
        target.page_end = max(target.page_end, continuation.page_end)
        return

    first_row = continuation.rows[0]
    has_blank_leading_key = (
        len(first_row) >= 2
        and first_row[0].strip() == ""
        and any(cell.strip() for cell in first_row[1:])
        and bool(target.rows)
    )

    if has_blank_leading_key:
        prev_row = target.rows[-1]
        for col_idx, cell in enumerate(first_row):
            cell_clean = cell.strip()
            if cell_clean:
                existing = prev_row[col_idx].strip()
                prev_row[col_idx] = f"{existing} {cell_clean}".strip() if existing else cell_clean
        remaining_rows = continuation.rows[1:]
    else:
        remaining_rows = continuation.rows

    target.rows.extend(remaining_rows)
    target.page_end = max(target.page_end, continuation.page_end)


def stitch_document_elements(pages: list[ExtractedPage]) -> list[PageElement]:
    """Flatten pages into an ordered stream and stitch split tables across page breaks."""
    stream: list[PageElement] = []

    for page in pages:
        for elem in page.elements:
            if (
                elem.kind == "table"
                and elem.table is not None
                and stream
                and stream[-1].kind == "table"
                and stream[-1].table is not None
                and stream[-1].table.page_end + 1 == elem.table.page_start
                and _headers_match(stream[-1].table.headers, elem.table.headers)
            ):
                _merge_continuation_rows(stream[-1].table, elem.table)
                continue
            stream.append(elem)

    return stream


def _escape_md_cell(value: str) -> str:
    return value.replace("|", "\\|").strip()


def format_table_markdown(table: ExtractedTable, rows: list[list[str]] | None = None) -> str:
    """Serialize a table (or row slice) as a clean Markdown pipe table."""
    target_rows = table.rows if rows is None else rows
    col_count = len(table.headers)
    header_line = "| " + " | ".join(_escape_md_cell(h) for h in table.headers) + " |"
    sep_line = "| " + " | ".join("---" for _ in table.headers) + " |"
    body_lines: list[str] = []

    for row in target_rows:
        padded = [*row, *([""] * max(0, col_count - len(row)))][:col_count]
        body_lines.append("| " + " | ".join(_escape_md_cell(cell) for cell in padded) + " |")

    return "\n".join([header_line, sep_line, *body_lines])

