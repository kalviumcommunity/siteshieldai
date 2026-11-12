"""Unit tests for structure-aware hierarchical chunking and table splitting."""

from __future__ import annotations

from app.ingestion.chunker import chunk_extracted_document
from app.ingestion.models import (
    ExtractedDocument,
    ExtractedLine,
    ExtractedPage,
    ExtractedTable,
    PageElement,
)
from app.schemas.documents import (
    ContentType,
    DocumentIngestMetadata,
    DocumentType,
    ExtractionMethod,
)


def _sample_metadata() -> DocumentIngestMetadata:
    return DocumentIngestMetadata(
        doc_title="Concrete Code IS 456",
        doc_type=DocumentType.CODE,
        jurisdiction="IN",
        version="2024",
    )


def test_chunker_preserves_section_stack_across_page_break() -> None:
    p1 = ExtractedPage(
        page_number=1,
        page_height=792.0,
        extraction_method=ExtractionMethod.NATIVE,
        elements=[
            PageElement(
                kind="line",
                page_number=1,
                y_top=100.0,
                line=ExtractedLine(1, "2. Objectives & Metrics", 100.0, 120.0, 18.0, True),
            ),
            PageElement(
                kind="line",
                page_number=1,
                y_top=140.0,
                line=ExtractedLine(1, "2.1 Primary Objectives", 140.0, 156.0, 14.0, True),
            ),
            PageElement(
                kind="line",
                page_number=1,
                y_top=170.0,
                line=ExtractedLine(
                    1, "- Process heterogeneous documents.", 170.0, 182.0, 11.0, False
                ),
            ),
        ],
    )
    p2 = ExtractedPage(
        page_number=2,
        page_height=792.0,
        extraction_method=ExtractionMethod.NATIVE,
        elements=[
            PageElement(
                kind="line",
                page_number=2,
                y_top=80.0,
                line=ExtractedLine(2, "- Enforce strict guardrails.", 80.0, 92.0, 11.0, False),
            ),
            PageElement(
                kind="line",
                page_number=2,
                y_top=110.0,
                line=ExtractedLine(2, "2.2 KPIs", 110.0, 126.0, 14.0, True),
            ),
            PageElement(
                kind="line",
                page_number=2,
                y_top=140.0,
                line=ExtractedLine(2, "1. Pipeline: Loader -> Chunker.", 140.0, 152.0, 11.0, True),
            ),
        ],
    )
    extracted = ExtractedDocument(
        source_filename="code.pdf",
        extension=".pdf",
        sha256_checksum="abc123",
        page_count=2,
        pages=[p1, p2],
        body_font_size=11.0,
    )

    chunks = chunk_extracted_document(extracted, _sample_metadata(), "doc_test")
    assert len(chunks) == 2
    assert chunks[0].section_id == "2.1"
    assert chunks[0].section_path == ["2. Objectives & Metrics", "2.1 Primary Objectives"]
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 2
    assert chunks[0].content_type == ContentType.LIST

    # Numbered list item at body font size under 2.2 must NOT overwrite section 2.2
    assert chunks[1].section_id == "2.2"
    assert chunks[1].section_path == ["2. Objectives & Metrics", "2.2 KPIs"]
    assert chunks[1].content_type == ContentType.LIST


def test_large_table_splits_with_repeated_header_and_metadata() -> None:
    rows = [[f"Row {i}", f"Concrete curing requirement {i} minimum 14 days"] for i in range(1, 25)]
    tbl = ExtractedTable(
        page_start=1,
        page_end=1,
        headers=["Item", "Requirement"],
        rows=rows,
        y_top=120.0,
        y_bottom=600.0,
    )
    extracted = ExtractedDocument(
        source_filename="spec.pdf",
        extension=".pdf",
        sha256_checksum="def456",
        page_count=1,
        pages=[
            ExtractedPage(
                page_number=1,
                page_height=792.0,
                extraction_method=ExtractionMethod.NATIVE,
                elements=[PageElement(kind="table", page_number=1, y_top=120.0, table=tbl)],
            )
        ],
    )

    chunks = chunk_extracted_document(
        extracted,
        _sample_metadata(),
        "doc_tbl",
        atomic_table_tokens=120,
    )
    assert len(chunks) >= 2
    for chk in chunks:
        assert chk.content_type == ContentType.TABLE
        assert chk.text_verbatim.startswith("| Item | Requirement |\n| --- | --- |")
        assert chk.text_for_embedding.startswith("[Doc: Concrete Code IS 456 | Section: General]")
