"""End-to-end document ingestion service orchestrator."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import ConflictAppError
from app.ingestion.chunker import chunk_extracted_document
from app.ingestion.extractors import OcrCallback, extract_document
from app.ingestion.store import IngestionStore
from app.ingestion.validator import validate_document_input
from app.schemas.documents import (
    ContentType,
    DocumentIngestMetadata,
    DocumentIngestResponse,
    DocumentRecord,
    DocumentStatus,
    ExtractionMethod,
    ExtractionSummary,
)

logger = logging.getLogger(__name__)


def _derive_doc_id(source_filename: str, doc_type: str, project_id: str | None) -> str:
    """Create a deterministic document identifier tied to logical source identity."""
    identity = f"{source_filename}:{doc_type}:{project_id or ''}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"doc_{digest}"


def _manifest_matches(existing: DocumentRecord, metadata: DocumentIngestMetadata) -> bool:
    """Check whether key manifest metadata matches an existing persisted record."""
    return (
        existing.doc_title == metadata.doc_title
        and existing.doc_type == metadata.doc_type
        and existing.jurisdiction == metadata.jurisdiction
        and existing.project_id == metadata.project_id
        and existing.standard_code == metadata.standard_code
        and existing.version == metadata.version
        and existing.publication_date == metadata.publication_date
        and existing.effective_date == metadata.effective_date
        and existing.supersedes_doc_id == metadata.supersedes_doc_id
        and existing.confidentiality_tier == metadata.confidentiality_tier
    )


class IngestionService:
    """Repeatable document ingestion pipeline without embedding generation."""

    def __init__(
        self,
        settings: Settings,
        store: IngestionStore,
        ocr_fn: OcrCallback | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.ocr_fn = ocr_fn

    def ingest_bytes(
        self,
        filename: str,
        data: bytes,
        metadata: DocumentIngestMetadata,
    ) -> DocumentIngestResponse:
        """Validate, extract, clean, chunk, and store a document idempotently."""
        clean_name, _ = validate_document_input(filename, data, self.settings)
        checksum = hashlib.sha256(data).hexdigest()

        existing_by_hash = self.store.get_by_checksum(checksum)
        if existing_by_hash is not None:
            existing_doc, stats = existing_by_hash
            if existing_doc.source_filename != clean_name:
                raise ConflictAppError(
                    f"Identical content already ingested as '{existing_doc.source_filename}'.",
                    error_code="DUPLICATE_DOCUMENT_CONTENT",
                    details={
                        "existing_doc_id": existing_doc.doc_id,
                        "sha256_checksum": checksum,
                    },
                )
            if _manifest_matches(existing_doc, metadata):
                logger.info(
                    "Unchanged document skipped",
                    extra={
                        "doc_id": existing_doc.doc_id,
                        "sha256_checksum": checksum,
                        "source_filename": clean_name,
                    },
                )
                return DocumentIngestResponse(
                    doc_id=existing_doc.doc_id,
                    status="unchanged",
                    unchanged=True,
                    sha256_checksum=checksum,
                    page_count=existing_doc.page_count,
                    chunks_created=existing_doc.chunk_count,
                    tables_extracted=stats["tables_extracted"],
                    extraction_summary=ExtractionSummary(
                        native_pages=stats["native_pages"],
                        ocr_pages=stats["ocr_pages"],
                    ),
                    warnings=[
                        "Document unchanged (matching SHA-256 checksum); skipped re-ingestion."
                    ],
                )

        existing_identity = self.store.get_by_identity(
            source_filename=clean_name,
            doc_type=metadata.doc_type,
            project_id=metadata.project_id,
        )
        doc_id = (
            existing_identity.doc_id
            if existing_identity is not None
            else _derive_doc_id(clean_name, metadata.doc_type.value, metadata.project_id)
        )
        ingest_status = "updated" if existing_identity is not None else "ingested"

        extracted = extract_document(clean_name, data, self.settings, ocr_fn=self.ocr_fn)
        chunks = chunk_extracted_document(extracted, metadata, doc_id)

        native_pages = sum(
            1 for p in extracted.pages if p.extraction_method == ExtractionMethod.NATIVE
        )
        ocr_pages = sum(1 for p in extracted.pages if p.extraction_method == ExtractionMethod.OCR)
        tables_extracted = sum(1 for chk in chunks if chk.content_type == ContentType.TABLE)

        warnings = list(extracted.warnings)
        if metadata.effective_date is None and metadata.publication_date is None:
            warnings.append("No publication_date or effective_date provided in manifest.")

        record = DocumentRecord(
            doc_id=doc_id,
            doc_title=metadata.doc_title,
            doc_type=metadata.doc_type,
            jurisdiction=metadata.jurisdiction,
            project_id=metadata.project_id,
            standard_code=metadata.standard_code,
            version=metadata.version,
            publication_date=metadata.publication_date,
            effective_date=metadata.effective_date,
            supersedes_doc_id=metadata.supersedes_doc_id,
            status=DocumentStatus.ACTIVE,
            confidentiality_tier=metadata.confidentiality_tier,
            source_filename=clean_name,
            sha256_checksum=checksum,
            page_count=extracted.page_count,
            chunk_count=len(chunks),
            ingested_at=datetime.now(UTC),
        )
        self.store.upsert_document(
            record,
            chunks,
            tables_extracted=tables_extracted,
            native_pages=native_pages,
            ocr_pages=ocr_pages,
            warnings=warnings,
        )

        logger.info(
            "Document ingestion completed",
            extra={
                "doc_id": doc_id,
                "ingest_status": ingest_status,
                "source_filename": clean_name,
                "sha256_checksum": checksum,
                "page_count": extracted.page_count,
                "chunks_created": len(chunks),
                "tables_extracted": tables_extracted,
            },
        )
        return DocumentIngestResponse(
            doc_id=doc_id,
            status=ingest_status,
            unchanged=False,
            sha256_checksum=checksum,
            page_count=extracted.page_count,
            chunks_created=len(chunks),
            tables_extracted=tables_extracted,
            extraction_summary=ExtractionSummary(
                native_pages=native_pages,
                ocr_pages=ocr_pages,
            ),
            warnings=warnings,
        )

    def ingest_file(self, path: Path, metadata: DocumentIngestMetadata) -> DocumentIngestResponse:
        """Read a local file from disk and run the ingestion pipeline."""
        data = path.read_bytes()
        return self.ingest_bytes(path.name, data, metadata)
