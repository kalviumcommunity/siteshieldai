"""Internal data structures used across the document ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.schemas.documents import ContentType, ExtractionMethod


@dataclass(slots=True)
class ExtractedLine:
    """Single extracted text line with layout and typography metadata."""

    page_number: int
    text: str
    y_top: float
    y_bottom: float
    font_size: float = 11.0
    is_bold: bool = False
    is_heading_hint: bool = False


@dataclass(slots=True)
class ExtractedTable:
    """Extracted tabular grid with normalized header and data rows."""

    page_start: int
    page_end: int
    headers: list[str]
    rows: list[list[str]]
    y_top: float
    y_bottom: float


@dataclass(slots=True)
class PageElement:
    """Ordered block on a page representing either a text line or a table."""

    kind: Literal["line", "table"]
    page_number: int
    y_top: float
    line: ExtractedLine | None = None
    table: ExtractedTable | None = None


@dataclass(slots=True)
class ExtractedPage:
    """Extracted content and triage telemetry for one document page."""

    page_number: int
    page_height: float
    extraction_method: ExtractionMethod
    ocr_confidence: float | None = None
    printed_page_label: str | None = None
    elements: list[PageElement] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExtractedDocument:
    """Full extracted intermediate representation prior to chunking."""

    source_filename: str
    extension: str
    sha256_checksum: str
    page_count: int
    pages: list[ExtractedPage]
    body_font_size: float = 11.0
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DocumentChunk:
    """Prepared chunk with verified provenance metadata ready for indexing."""

    chunk_id: str
    doc_id: str
    chunk_index: int
    page_start: int
    page_end: int
    printed_page_label: str | None
    section_id: str | None
    section_path: list[str]
    content_type: ContentType
    extraction_method: ExtractionMethod
    ocr_confidence: float | None
    char_start: int
    char_end: int
    token_estimate: int
    text_for_embedding: str
    text_verbatim: str

