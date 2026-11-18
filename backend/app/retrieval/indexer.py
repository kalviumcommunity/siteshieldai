"""Vector indexing coordinator connecting ingestion, embedding, and vector storage."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ingestion.models import DocumentChunk
from app.retrieval.embeddings import EmbeddingAdapter
from app.retrieval.vector_store import VectorStorePort
from app.schemas.documents import ChunkRecord, DocumentRecord

logger = logging.getLogger(__name__)


class VectorIndexer:
    """Coordinates embedding generation and vector database synchronization.

    Guarantees:
    - Repeatable indexing: unchanged documents bypass embedding and vector writes.
    - Idempotent updates: existing vectors for an updated document are deleted prior to upsert.
    - Provenance preservation: full document and chunk metadata is attached to vector points.
    """

    def __init__(
        self,
        embedding_adapter: EmbeddingAdapter,
        vector_store: VectorStorePort,
        collection_name: str = "siteshield_chunks",
    ) -> None:
        self.embedding_adapter = embedding_adapter
        self.vector_store = vector_store
        self.collection_name = collection_name
        self._initialized = False

    def initialize(self) -> None:
        """Ensure the target collection exists with the active embedding dimension."""
        self.vector_store.ensure_collection(
            collection_name=self.collection_name,
            dimension=self.embedding_adapter.dimension,
            distance="Cosine",
        )
        self._initialized = True

    def sync_document(
        self,
        doc_record: DocumentRecord,
        chunks: list[DocumentChunk | ChunkRecord],
        ingest_status: str,
    ) -> int:
        """Synchronize document chunks with vector storage based on ingestion triage.

        Parameters
        ----------
        doc_record : DocumentRecord
            Document manifest and source provenance.
        chunks : list[DocumentChunk | ChunkRecord]
            Verified extracted chunks ready for indexing.
        ingest_status : str
            One of "ingested", "updated", or "unchanged".

        Returns
        -------
        int
            Number of vector points upserted.
        """
        if ingest_status == "unchanged":
            logger.info(
                "Document content and manifest unchanged; skipping vector indexing",
                extra={"doc_id": doc_record.doc_id, "checksum": doc_record.sha256_checksum},
            )
            return 0

        if not self._initialized:
            self.initialize()

        if ingest_status == "updated":
            deleted_count = self.vector_store.delete_by_doc_id(
                collection_name=self.collection_name,
                doc_id=doc_record.doc_id,
            )
            logger.info(
                "Removed stale document vector points before update indexing",
                extra={"doc_id": doc_record.doc_id, "deleted_count": deleted_count},
            )

        if not chunks:
            return 0

        # Generate embeddings using prefixed text_for_embedding for higher precision
        texts_to_embed = [chk.text_for_embedding for chk in chunks]
        embeddings = self.embedding_adapter.embed_documents(texts_to_embed)

        upserted_count = self.vector_store.upsert_chunks(
            collection_name=self.collection_name,
            chunks=chunks,
            embeddings=embeddings,
            doc_record=doc_record,
        )

        logger.info(
            "Vector indexing synchronization completed",
            extra={
                "doc_id": doc_record.doc_id,
                "ingest_status": ingest_status,
                "chunks_count": len(chunks),
                "vectors_upserted": upserted_count,
            },
        )
        return upserted_count
