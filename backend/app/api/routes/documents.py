"""Document ingestion and inspection API routes."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import ResourceNotFoundError, ValidationAppError
from app.ingestion.service import IngestionService
from app.ingestion.store import IngestionStore
from app.schemas.documents import (
    DocumentChunksResponse,
    DocumentIngestMetadata,
    DocumentIngestResponse,
    DocumentListResponse,
    DocumentRecord,
    DocumentStatus,
    DocumentType,
)

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_settings(request: Request) -> Settings:
    app_settings: Settings | None = getattr(request.app.state, "settings", None)
    return app_settings if app_settings is not None else get_settings()


def _get_ingestion_store(
    request: Request,
    settings: Annotated[Settings, Depends(_get_settings)],
) -> IngestionStore:
    store: IngestionStore | None = getattr(request.app.state, "ingestion_store", None)
    if store is None:
        store = IngestionStore(settings.ingestion_db_path)
        request.app.state.ingestion_store = store
    return store


def _get_ingestion_service(
    settings: Annotated[Settings, Depends(_get_settings)],
    store: Annotated[IngestionStore, Depends(_get_ingestion_store)],
) -> IngestionService:
    return IngestionService(settings=settings, store=store)


@router.post(
    "/ingest",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and chunk a construction or reference document",
)
async def ingest_document(
    response: Response,
    file: Annotated[UploadFile, File(...)],
    metadata: Annotated[str, Form(...)],
    service: Annotated[IngestionService, Depends(_get_ingestion_service)],
) -> DocumentIngestResponse:
    """Validate, extract, clean, chunk, and store a document without embeddings."""
    try:
        raw_meta = json.loads(metadata)
    except json.JSONDecodeError as exc:
        raise ValidationAppError(
            "Invalid JSON in metadata form field.",
            error_code="INVALID_METADATA_JSON",
        ) from exc

    try:
        parsed_meta = DocumentIngestMetadata.model_validate(raw_meta)
    except ValidationError as exc:
        raise ValidationAppError(
            "Document metadata validation failed.",
            error_code="INVALID_METADATA_SCHEMA",
            details=[
                {
                    "loc": list(err.get("loc", ())),
                    "msg": err.get("msg", "Invalid value"),
                    "type": err.get("type", "value_error"),
                }
                for err in exc.errors()
            ],
        ) from exc

    file_bytes = await file.read()
    result = service.ingest_bytes(file.filename or "", file_bytes, parsed_meta)
    if result.unchanged:
        response.status_code = status.HTTP_200_OK
    return result


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List ingested documents",
)
async def list_documents(
    store: Annotated[IngestionStore, Depends(_get_ingestion_store)],
    doc_type: Annotated[DocumentType | None, Query()] = None,
    jurisdiction: Annotated[str | None, Query()] = None,
    project_id: Annotated[str | None, Query()] = None,
    doc_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    """Retrieve ingested documents with optional metadata filters."""
    items, total = store.list_documents(
        doc_type=doc_type,
        jurisdiction=jurisdiction,
        project_id=project_id,
        status=doc_status,
        limit=limit,
        offset=offset,
    )
    return DocumentListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{doc_id}",
    response_model=DocumentRecord,
    summary="Retrieve ingested document details",
)
async def get_document(
    doc_id: str,
    store: Annotated[IngestionStore, Depends(_get_ingestion_store)],
) -> DocumentRecord:
    """Return manifest metadata and counts for a single document."""
    record = store.get_document(doc_id)
    if record is None:
        raise ResourceNotFoundError(f"Document '{doc_id}' was not found.")
    return record


@router.get(
    "/{doc_id}/chunks",
    response_model=DocumentChunksResponse,
    summary="Retrieve verified chunks and provenance metadata for a document",
)
async def get_document_chunks(
    doc_id: str,
    store: Annotated[IngestionStore, Depends(_get_ingestion_store)],
) -> DocumentChunksResponse:
    """Return stored chunks with section, page, and manifest provenance."""
    record = store.get_document(doc_id)
    if record is None:
        raise ResourceNotFoundError(f"Document '{doc_id}' was not found.")
    chunks = store.get_chunks(doc_id)
    return DocumentChunksResponse(doc_id=doc_id, total_chunks=len(chunks), chunks=chunks)

