"""Vector storage abstraction, Qdrant implementation, and factory."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import SecretStr

from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    ResourceNotFoundError,
    ValidationAppError,
    VectorStoreError,
)
from app.ingestion.models import DocumentChunk
from app.schemas.documents import ChunkRecord, DocumentRecord

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ScoredChunk:
    """Scored retrieval candidate returned by vector similarity search."""

    chunk_id: str
    doc_id: str
    score: float
    text_verbatim: str
    payload: dict[str, Any]


@runtime_checkable
class VectorStorePort(Protocol):
    """Protocol for vector database operations."""

    def collection_exists(self, collection_name: str) -> bool:
        """Return True if the specified collection exists."""
        ...

    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """Return collection configuration and runtime statistics."""
        ...

    def ensure_collection(
        self,
        collection_name: str,
        dimension: int,
        distance: str = "Cosine",
    ) -> None:
        """Create or validate the target collection with required schema and indexes."""
        ...

    def upsert_chunks(
        self,
        collection_name: str,
        chunks: list[DocumentChunk | ChunkRecord],
        embeddings: list[list[float]],
        doc_record: DocumentRecord | None = None,
    ) -> int:
        """Persist chunk vectors and complete provenance metadata payloads."""
        ...

    def delete_by_doc_id(self, collection_name: str, doc_id: str) -> int:
        """Delete all points associated with a specific document identifier."""
        ...

    def count(self, collection_name: str, doc_id: str | None = None) -> int:
        """Count total vectors or vectors scoped to a document."""
        ...

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        """Execute vector similarity search with optional metadata pre-filtering."""
        ...

    def delete_collection(self, collection_name: str) -> None:
        """Drop an entire collection (used in tests or re-indexing)."""
        ...


def _date_to_timestamp(d: date | None) -> int | None:
    if d is None:
        return None
    return int(datetime.combine(d, time.min, tzinfo=UTC).timestamp())


class QdrantVectorStore:
    """Qdrant vector store adapter supporting local embedded, in-memory, or remote client-server."""

    def __init__(
        self,
        path: str | Path | None = None,
        url: str | None = None,
        api_key: str | SecretStr | None = None,
        location: str | None = None,
        client: Any | None = None,
    ) -> None:
        if client is not None:
            self._client = client
            return

        from qdrant_client import QdrantClient

        raw_api_key = (
            api_key.get_secret_value() if isinstance(api_key, SecretStr) else (api_key or None)
        )

        try:
            if location == ":memory:":
                logger.info("Initializing in-memory Qdrant client")
                self._client = QdrantClient(":memory:")
            elif url and url.strip():
                logger.info("Connecting to remote Qdrant server", extra={"url": url.strip()})
                self._client = QdrantClient(url=url.strip(), api_key=raw_api_key)
            else:
                db_path = Path(path or "data/qdrant")
                db_path.mkdir(parents=True, exist_ok=True)
                logger.info(
                    "Initializing embedded disk Qdrant client", extra={"path": str(db_path)}
                )
                self._client = QdrantClient(path=str(db_path))
        except Exception as exc:
            logger.error("Failed to initialize Qdrant client", extra={"error": str(exc)})
            raise VectorStoreError(
                f"Failed to connect to Qdrant vector database: {exc}",
                error_code="VECTOR_STORE_CONNECTION_FAILED",
            ) from exc

    @property
    def client(self) -> Any:
        """Expose underlying QdrantClient instance."""
        return self._client

    def collection_exists(self, collection_name: str) -> bool:
        """Check whether a collection is registered in Qdrant."""
        try:
            collections_res = self._client.get_collections()
            return any(c.name == collection_name for c in collections_res.collections)
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to check collection existence for '{collection_name}': {exc}",
                error_code="VECTOR_STORE_ERROR",
            ) from exc

    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """Fetch metadata, vector parameters, and counts for a collection."""
        try:
            info = self._client.get_collection(collection_name=collection_name)
            vectors_cfg = info.config.params.vectors
            dim = getattr(vectors_cfg, "size", None)
            distance = getattr(vectors_cfg, "distance", None)
            return {
                "collection_name": collection_name,
                "dimension": dim,
                "distance": str(distance),
                "points_count": info.points_count,
                "indexed_vectors_count": getattr(info, "indexed_vectors_count", None),
                "status": str(info.status),
            }
        except Exception as exc:
            if "not found" in str(exc).lower():
                raise ResourceNotFoundError(
                    f"Collection '{collection_name}' not found.",
                    error_code="COLLECTION_NOT_FOUND",
                ) from exc
            raise VectorStoreError(
                f"Failed to retrieve collection info for '{collection_name}': {exc}",
                error_code="VECTOR_STORE_ERROR",
            ) from exc

    def ensure_collection(
        self,
        collection_name: str,
        dimension: int,
        distance: str = "Cosine",
    ) -> None:
        """Ensure collection exists with matching vector dimensions and payload indexes."""
        from qdrant_client import models

        distance_map = {
            "cosine": models.Distance.COSINE,
            "dot": models.Distance.DOT,
            "euclid": models.Distance.EUCLID,
        }
        chosen_distance = distance_map.get(distance.lower(), models.Distance.COSINE)

        try:
            if self.collection_exists(collection_name):
                info = self._client.get_collection(collection_name=collection_name)
                existing_size = info.config.params.vectors.size
                if existing_size != dimension:
                    raise VectorStoreError(
                        f"Collection '{collection_name}' vector dimension mismatch: "
                        f"existing collection has dimension {existing_size}, but active model "
                        f"requires {dimension}. Per architectural policy (RAG_ARCHITECTURE.md §6), "
                        "mixing incompatible vectors is prohibited; re-indexing is required.",
                        error_code="VECTOR_DIMENSION_MISMATCH",
                        details={
                            "collection_name": collection_name,
                            "existing_dimension": existing_size,
                            "required_dimension": dimension,
                        },
                    )
                return

            logger.info(
                "Creating Qdrant collection",
                extra={
                    "collection_name": collection_name,
                    "dimension": dimension,
                    "distance": distance,
                },
            )
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=chosen_distance,
                ),
            )

            # Create payload indices for fast pre-filtering
            payload_indexes = [
                ("doc_id", models.PayloadSchemaType.KEYWORD),
                ("doc_type", models.PayloadSchemaType.KEYWORD),
                ("project_id", models.PayloadSchemaType.KEYWORD),
                ("jurisdiction", models.PayloadSchemaType.KEYWORD),
                ("status", models.PayloadSchemaType.KEYWORD),
                ("content_type", models.PayloadSchemaType.KEYWORD),
                ("effective_timestamp", models.PayloadSchemaType.INTEGER),
            ]
            for field_name, schema_type in payload_indexes:
                try:
                    import warnings

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        self._client.create_payload_index(
                            collection_name=collection_name,
                            field_name=field_name,
                            field_schema=schema_type,
                        )
                except Exception as index_err:
                    # In local in-memory Qdrant, payload indices are no-ops
                    logger.debug(
                        "Payload index creation note",
                        extra={"field": field_name, "error": str(index_err)},
                    )
        except VectorStoreError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to ensure Qdrant collection",
                extra={"collection_name": collection_name, "error": str(exc)},
            )
            raise VectorStoreError(
                f"Failed to ensure Qdrant collection '{collection_name}': {exc}",
                error_code="COLLECTION_INITIALIZATION_FAILED",
            ) from exc

    def upsert_chunks(
        self,
        collection_name: str,
        chunks: list[DocumentChunk | ChunkRecord],
        embeddings: list[list[float]],
        doc_record: DocumentRecord | None = None,
    ) -> int:
        """Upsert document chunks and verified provenance metadata into Qdrant."""
        if len(chunks) != len(embeddings):
            raise ValidationAppError(
                f"Chunks count ({len(chunks)}) does not match embeddings "
                f"count ({len(embeddings)}).",
                error_code="CHUNKS_EMBEDDINGS_MISMATCH",
            )
        if not chunks:
            return 0

        from qdrant_client import models

        points: list[models.PointStruct] = []
        indexed_at_iso = datetime.now(UTC).isoformat()

        for chunk, vector in zip(chunks, embeddings, strict=True):
            # Deterministic UUID v5 derived from unique chunk_id
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))

            # Resolve document-level provenance
            if isinstance(chunk, ChunkRecord):
                doc_id = chunk.doc_id
                doc_title = chunk.doc_title
                doc_type_val = chunk.doc_type.value
                jurisdiction = chunk.jurisdiction
                project_id = chunk.project_id
                standard_code = chunk.standard_code
                version = chunk.version
                pub_date = chunk.publication_date.isoformat() if chunk.publication_date else None
                eff_date = chunk.effective_date.isoformat() if chunk.effective_date else None
                eff_ts = _date_to_timestamp(chunk.effective_date)
                status_val = chunk.status.value
                conf_val = chunk.confidentiality_tier.value
                source_filename = chunk.source_filename
                sha256_checksum = chunk.sha256_checksum
            elif doc_record is not None:
                doc_id = doc_record.doc_id
                doc_title = doc_record.doc_title
                doc_type_val = doc_record.doc_type.value
                jurisdiction = doc_record.jurisdiction
                project_id = doc_record.project_id
                standard_code = doc_record.standard_code
                version = doc_record.version
                pub_date = (
                    doc_record.publication_date.isoformat() if doc_record.publication_date else None
                )
                eff_date = (
                    doc_record.effective_date.isoformat() if doc_record.effective_date else None
                )
                eff_ts = _date_to_timestamp(doc_record.effective_date)
                status_val = doc_record.status.value
                conf_val = doc_record.confidentiality_tier.value
                source_filename = doc_record.source_filename
                sha256_checksum = doc_record.sha256_checksum
            else:
                doc_id = chunk.doc_id
                doc_title = ""
                doc_type_val = "spec"
                jurisdiction = "UNSPECIFIED"
                project_id = None
                standard_code = None
                version = "v1.0"
                pub_date = None
                eff_date = None
                eff_ts = None
                status_val = "active"
                conf_val = "internal"
                source_filename = ""
                sha256_checksum = ""

            content_type_val = (
                chunk.content_type.value
                if hasattr(chunk.content_type, "value")
                else str(chunk.content_type)
            )
            extraction_val = (
                chunk.extraction_method.value
                if hasattr(chunk.extraction_method, "value")
                else str(chunk.extraction_method)
            )

            payload: dict[str, Any] = {
                "chunk_id": chunk.chunk_id,
                "doc_id": doc_id,
                "doc_title": doc_title,
                "doc_type": doc_type_val,
                "jurisdiction": jurisdiction,
                "project_id": project_id,
                "standard_code": standard_code,
                "version": version,
                "publication_date": pub_date,
                "effective_date": eff_date,
                "effective_timestamp": eff_ts,
                "status": status_val,
                "confidentiality_tier": conf_val,
                "source_filename": source_filename,
                "sha256_checksum": sha256_checksum,
                "chunk_index": chunk.chunk_index,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "printed_page_label": chunk.printed_page_label,
                "section_id": chunk.section_id,
                "section_path": list(chunk.section_path),
                "content_type": content_type_val,
                "extraction_method": extraction_val,
                "ocr_confidence": chunk.ocr_confidence,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "token_estimate": chunk.token_estimate,
                "text_for_embedding": chunk.text_for_embedding,
                "text_verbatim": chunk.text_verbatim,
                "indexed_at": indexed_at_iso,
            }

            points.append(
                models.PointStruct(
                    id=point_uuid,
                    vector=vector,
                    payload=payload,
                )
            )

        # Batch upsert into Qdrant
        batch_size = 64
        total_upserted = 0
        try:
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                self._client.upsert(
                    collection_name=collection_name,
                    points=batch,
                )
                total_upserted += len(batch)
            logger.info(
                "Upserted vector points into Qdrant",
                extra={
                    "collection_name": collection_name,
                    "points_upserted": total_upserted,
                },
            )
            return total_upserted
        except Exception as exc:
            logger.error(
                "Qdrant point upsert failed",
                extra={"collection_name": collection_name, "error": str(exc)},
            )
            raise VectorStoreError(
                f"Failed to upsert points into collection '{collection_name}': {exc}",
                error_code="VECTOR_UPSERT_FAILED",
            ) from exc

    def count(self, collection_name: str, doc_id: str | None = None) -> int:
        """Count total points in a collection or points belonging to a specific doc_id."""
        from qdrant_client import models

        try:
            if not self.collection_exists(collection_name):
                return 0

            if doc_id is None:
                res = self._client.count(collection_name=collection_name)
                return int(res.count)

            res = self._client.count(
                collection_name=collection_name,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id),
                        )
                    ]
                ),
            )
            return int(res.count)
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to count points in collection '{collection_name}': {exc}",
                error_code="VECTOR_STORE_ERROR",
            ) from exc

    def delete_by_doc_id(self, collection_name: str, doc_id: str) -> int:
        """Delete all vector points belonging to a document identifier."""
        from qdrant_client import models

        try:
            if not self.collection_exists(collection_name):
                return 0

            existing_count = self.count(collection_name, doc_id=doc_id)
            if existing_count == 0:
                return 0

            self._client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="doc_id",
                                match=models.MatchValue(value=doc_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(
                "Deleted vector points by doc_id",
                extra={
                    "collection_name": collection_name,
                    "doc_id": doc_id,
                    "points_deleted": existing_count,
                },
            )
            return existing_count
        except Exception as exc:
            logger.error(
                "Failed to delete points by doc_id",
                extra={"collection_name": collection_name, "doc_id": doc_id, "error": str(exc)},
            )
            raise VectorStoreError(
                f"Failed to delete points for doc_id '{doc_id}' in '{collection_name}': {exc}",
                error_code="VECTOR_DELETE_FAILED",
            ) from exc

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        """Execute vector similarity search with optional metadata pre-filtering."""
        from qdrant_client import models

        try:
            if not self.collection_exists(collection_name):
                return []

            conditions: list[Any] = []
            if filters:
                if filters.get("doc_id"):
                    conditions.append(
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=filters["doc_id"]),
                        )
                    )
                if filters.get("jurisdiction"):
                    conditions.append(
                        models.FieldCondition(
                            key="jurisdiction",
                            match=models.MatchValue(value=filters["jurisdiction"]),
                        )
                    )
                if filters.get("status"):
                    conditions.append(
                        models.FieldCondition(
                            key="status",
                            match=models.MatchValue(value=filters["status"]),
                        )
                    )
                if filters.get("doc_types"):
                    conditions.append(
                        models.FieldCondition(
                            key="doc_type",
                            match=models.MatchAny(any=list(filters["doc_types"])),
                        )
                    )
                if filters.get("project_id"):
                    # Scoping rule: project_id == target OR
                    # (project_id IS NULL AND doc_type IN ['code', 'safety_manual'])
                    req_proj = filters["project_id"]
                    project_scope = models.Filter(
                        should=[
                            models.FieldCondition(
                                key="project_id",
                                match=models.MatchValue(value=req_proj),
                            ),
                            models.Filter(
                                must=[
                                    models.IsNullCondition(
                                        is_null=models.PayloadField(key="project_id")
                                    ),
                                    models.FieldCondition(
                                        key="doc_type",
                                        match=models.MatchAny(any=["code", "safety_manual"]),
                                    ),
                                ]
                            ),
                        ]
                    )
                    conditions.append(project_scope)

            query_filter = models.Filter(must=conditions) if conditions else None

            response = self._client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                query_filter=query_filter,
                with_payload=True,
            )

            scored_chunks: list[ScoredChunk] = []
            for pt in response.points:
                payload = pt.payload or {}
                scored_chunks.append(
                    ScoredChunk(
                        chunk_id=str(payload.get("chunk_id", pt.id)),
                        doc_id=str(payload.get("doc_id", "")),
                        score=float(pt.score),
                        text_verbatim=str(payload.get("text_verbatim", "")),
                        payload=payload,
                    )
                )
            return scored_chunks
        except Exception as exc:
            logger.error(
                "Qdrant query execution failed",
                extra={"collection_name": collection_name, "error": str(exc)},
            )
            raise VectorStoreError(
                f"Vector search failed in collection '{collection_name}': {exc}",
                error_code="VECTOR_SEARCH_FAILED",
            ) from exc

    def delete_collection(self, collection_name: str) -> None:
        """Drop a collection if it exists."""
        try:
            if self.collection_exists(collection_name):
                self._client.delete_collection(collection_name=collection_name)
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to delete collection '{collection_name}': {exc}",
                error_code="VECTOR_STORE_ERROR",
            ) from exc


def get_vector_store(
    settings: Settings,
    location: str | None = None,
) -> VectorStorePort:
    """Factory creating the appropriate VectorStorePort according to settings."""
    provider = settings.effective_vector_db_provider
    if provider != "qdrant":
        raise ConfigurationError(
            f"Unsupported vector database provider: '{provider}'. Supported provider is 'qdrant'.",
            error_code="UNSUPPORTED_VECTOR_DB_PROVIDER",
        )

    return QdrantVectorStore(
        path=settings.effective_vector_db_path,
        url=settings.vector_db_url,
        api_key=settings.vector_db_api_key,
        location=location,
    )
