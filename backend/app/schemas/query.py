"""Pydantic schemas for compliance queries, citations, conflicts, and abstention."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.schemas.documents import ContentType, DocumentType, ExtractionMethod


class QueryStatus(StrEnum):
    """Outcome classification for compliance query responses."""

    SUPPORTED = "supported"
    CONFLICT_FLAGGED = "conflict_flagged"
    NEEDS_REVIEW = "needs_review"
    ABSTAINED = "abstained"


class ConflictType(StrEnum):
    """Category of detected cross-document or cross-version conflict."""

    VERSION_SUPERSESSION = "version_supersession"
    CROSS_DOCUMENT_VALUE_MISMATCH = "cross_document_value_mismatch"
    REPORT_VS_CODE_DIVERGENCE = "report_vs_code_divergence"


class QueryFilters(BaseModel):
    """Optional metadata filters applied prior to vector retrieval."""

    project_id: str | None = Field(default=None, max_length=100)
    jurisdiction: str | None = Field(default=None, max_length=100)
    doc_types: list[DocumentType] | None = None
    include_superseded: bool = False

    @field_validator("project_id", "jurisdiction")
    @classmethod
    def _normalize_optional_filter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class QueryRequest(BaseModel):
    """Request contract for POST /query."""

    query: str = Field(..., min_length=1, max_length=1000)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False

    @field_validator("query")
    @classmethod
    def _validate_non_blank_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be blank.")
        return cleaned


class CitationItem(BaseModel):
    """Source chunk provenance attached to a grounded compliance claim."""

    evidence_id: str = Field(..., min_length=1)
    chunk_id: str = Field(..., min_length=1)
    doc_id: str = Field(..., min_length=1)
    doc_title: str
    doc_type: DocumentType
    version: str
    effective_date: date | None = None
    jurisdiction: str
    project_id: str | None = None
    section_id: str | None = None
    section_path: list[str] = Field(default_factory=list)
    page_start: int = Field(..., ge=1)
    page_end: int = Field(..., ge=1)
    content_type: ContentType
    extraction_method: ExtractionMethod
    retrieval_score: float = Field(..., ge=0.0)
    text_verbatim: str


class ConflictSourceRef(BaseModel):
    """Reference to one side of a detected compliance conflict."""

    doc_id: str
    doc_title: str
    version: str
    effective_date: date | None = None
    section_id: str | None = None
    page_start: int = Field(..., ge=1)
    excerpt: str


class ConflictItem(BaseModel):
    """Detected contradiction or revision conflict surfaced to the user."""

    conflict_type: ConflictType
    source_a: ConflictSourceRef
    source_b: ConflictSourceRef
    summary: str
    precedence_note: str


class LatencyBreakdown(BaseModel):
    """Stage-level latency telemetry in milliseconds."""

    embedding: int = Field(default=0, ge=0)
    retrieval: int = Field(default=0, ge=0)
    rerank: int = Field(default=0, ge=0)
    generation: int = Field(default=0, ge=0)
    validation: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)


class QueryResponse(BaseModel):
    """Response contract for POST /query."""

    query_id: str
    status: QueryStatus
    answer: str
    citations: list[CitationItem] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)
    abstention_reason: str | None = None
    latency_ms: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    disclaimer: str = (
        "AI-generated decision support. Verify cited source clauses and governing "
        "revisions before site execution."
    )
