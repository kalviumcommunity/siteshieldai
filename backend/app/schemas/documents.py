"""Pydantic schemas for document manifests, ingestion responses, and metadata records."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class DocumentType(StrEnum):
    """Canonical construction document category."""

    CODE = "code"
    SPEC = "spec"
    REPORT = "report"
    SAFETY_MANUAL = "safety_manual"


class DocumentStatus(StrEnum):
    """Lifecycle status of an indexed document."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DRAFT = "draft"


class ConfidentialityTier(StrEnum):
    """Data handling classification governing external API transfer."""

    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class ExtractionMethod(StrEnum):
    """How text was extracted from a document page."""

    NATIVE = "native"
    OCR = "ocr"


class ContentType(StrEnum):
    """Structural type of an extracted chunk."""

    PROSE = "prose"
    LIST = "list"
    TABLE = "table"


def _strip_required_text(value: str) -> str:
    """Strip whitespace and reject empty strings."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Field must not be blank.")
    return cleaned


class DocumentIngestMetadata(BaseModel):
    """Metadata manifest supplied with document ingestion."""

    doc_title: str = Field(..., min_length=1, max_length=255)
    doc_type: DocumentType
    jurisdiction: str = Field(default="UNSPECIFIED", min_length=1, max_length=100)
    project_id: str | None = Field(default=None, max_length=100)
    standard_code: str | None = Field(default=None, max_length=100)
    version: str = Field(..., min_length=1, max_length=64)
    publication_date: date | None = None
    effective_date: date | None = None
    supersedes_doc_id: str | None = Field(default=None, max_length=128)
    confidentiality_tier: ConfidentialityTier = ConfidentialityTier.INTERNAL

    @field_validator("doc_title", "jurisdiction", "version")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        return _strip_required_text(value)

    @field_validator("project_id", "standard_code", "supersedes_doc_id")
    @classmethod
    def _normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def _validate_date_order(self) -> DocumentIngestMetadata:
        if (
            self.publication_date is not None
            and self.effective_date is not None
            and self.effective_date < self.publication_date
        ):
            raise ValueError("effective_date cannot be earlier than publication_date.")
        return self


class ExtractionSummary(BaseModel):
    """Page-level native vs OCR extraction breakdown."""

    native_pages: int = Field(..., ge=0)
    ocr_pages: int = Field(..., ge=0)


class DocumentIngestResponse(BaseModel):
    """Response contract for POST /documents/ingest."""

    doc_id: str
    sha256_checksum: str
    page_count: int = Field(..., ge=0)
    chunks_created: int = Field(..., ge=0)
    tables_extracted: int = Field(..., ge=0)
    extraction_summary: ExtractionSummary
    warnings: list[str] = Field(default_factory=list)


class DocumentRecord(BaseModel):
    """Persisted document manifest record returned by GET /documents endpoints."""

    doc_id: str
    doc_title: str
    doc_type: DocumentType
    jurisdiction: str
    project_id: str | None = None
    standard_code: str | None = None
    version: str
    publication_date: date | None = None
    effective_date: date | None = None
    supersedes_doc_id: str | None = None
    status: DocumentStatus = DocumentStatus.ACTIVE
    confidentiality_tier: ConfidentialityTier
    source_filename: str
    sha256_checksum: str
    page_count: int = Field(..., ge=0)
    chunk_count: int = Field(..., ge=0)
    ingested_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated response contract for GET /documents."""

    items: list[DocumentRecord] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)
