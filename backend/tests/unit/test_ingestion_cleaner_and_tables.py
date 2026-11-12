"""Unit tests for text cleaning, margin filtering, and cross-page table stitching."""

from __future__ import annotations

from app.ingestion.cleaner import clean_line_text, strip_running_headers_footers
from app.ingestion.models import ExtractedLine, ExtractedPage, ExtractedTable, PageElement
from app.ingestion.table_stitcher import format_table_markdown, stitch_document_elements
from app.schemas.documents import ExtractionMethod


def test_clean_line_text_strips_zwsp_and_preserves_regulatory_symbols() -> None:
    raw = (
        "●\u200b  Minimum curing ≥ 7 days at 20°C; load ≤ 15 kN/m²; "
        "see IS-456 & anti-hallucination."
    )
    cleaned = clean_line_text(raw)
    assert "\u200b" not in cleaned
    assert cleaned == (
        "- Minimum curing ≥ 7 days at 20°C; load ≤ 15 kN/m2; see IS-456 & anti-hallucination."
    )


def test_strip_running_headers_footers_removes_recurring_margins() -> None:
    pages: list[ExtractedPage] = []
    for pno in range(1, 5):
        elems = [
            PageElement(
                kind="line",
                page_number=pno,
                y_top=20.0,
                line=ExtractedLine(pno, "NATIONAL BUILDING CODE 2025", 20.0, 32.0),
            ),
            PageElement(
                kind="line",
                page_number=pno,
                y_top=120.0,
                line=ExtractedLine(pno, f"Clause {pno}.1 Structural Concrete", 120.0, 134.0),
            ),
            PageElement(
                kind="line",
                page_number=pno,
                y_top=760.0,
                line=ExtractedLine(pno, f"Page {pno}", 760.0, 772.0),
            ),
        ]
        pages.append(
            ExtractedPage(
                page_number=pno,
                page_height=792.0,
                extraction_method=ExtractionMethod.NATIVE,
                elements=elems,
            )
        )

    cleaned_pages = strip_running_headers_footers(pages)
    for pno, page in enumerate(cleaned_pages, 1):
        texts = [e.line.text for e in page.elements if e.line]
        assert texts == [f"Clause {pno}.1 Structural Concrete"]
        assert page.printed_page_label == str(pno)


def test_stitch_cross_page_table_merges_blank_leading_key_continuation() -> None:
    t_page4 = ExtractedTable(
        page_start=4,
        page_end=4,
        headers=["Phase / Week", "Focus Area", "Key Deliverables"],
        rows=[
            ["Week 4", "UI Integration", "Streamlit/Next.js UI"],
            ["Week 5", "Evaluation, Hardening", "Accuracy benchmarking against test queries,"],
        ],
        y_top=468.0,
        y_bottom=715.0,
    )
    t_page5 = ExtractedTable(
        page_start=5,
        page_end=5,
        headers=["Phase / Week", "Focus Area", "Key Deliverables"],
        rows=[["", "", "performance optimization, final viva & product submission."]],
        y_top=72.0,
        y_bottom=114.0,
    )
    pages = [
        ExtractedPage(
            page_number=4,
            page_height=792.0,
            extraction_method=ExtractionMethod.NATIVE,
            elements=[PageElement(kind="table", page_number=4, y_top=468.0, table=t_page4)],
        ),
        ExtractedPage(
            page_number=5,
            page_height=792.0,
            extraction_method=ExtractionMethod.NATIVE,
            elements=[PageElement(kind="table", page_number=5, y_top=72.0, table=t_page5)],
        ),
    ]

    stitched = stitch_document_elements(pages)
    assert len(stitched) == 1
    merged = stitched[0].table
    assert merged is not None
    assert merged.page_start == 4
    assert merged.page_end == 5
    assert len(merged.rows) == 2
    assert merged.rows[1][0] == "Week 5"
    expected = (
        "Accuracy benchmarking against test queries, performance optimization, "
        "final viva & product submission."
    )
    assert merged.rows[1][2] == expected
    md = format_table_markdown(merged)
    assert "| Week 5 | Evaluation, Hardening |" in md
