"""Integration tests for embedding generation, vector persistence, and repeatable indexing."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.ingestion.service import IngestionService
from app.ingestion.store import IngestionStore
from app.main import create_app
from app.retrieval.embeddings import DeterministicMockEmbeddingAdapter
from app.retrieval.indexer import VectorIndexer
from app.retrieval.vector_store import QdrantVectorStore
from app.schemas.documents import (
    ConfidentialityTier,
    DocumentIngestMetadata,
    DocumentType,
)


def _sample_doc_metadata(
    doc_title: str = "Structural Steel Specification",
    version: str = "v1.0",
    project_id: str | None = "#104",
    doc_type: DocumentType = DocumentType.SPEC,
) -> DocumentIngestMetadata:
    return DocumentIngestMetadata(
        doc_title=doc_title,
        doc_type=doc_type,
        jurisdiction="IN-KA",
        project_id=project_id,
        standard_code="IS 800:2007",
        version=version,
        publication_date="2024-01-15",
        effective_date="2024-02-01",
        confidentiality_tier=ConfidentialityTier.INTERNAL,
    )


def test_end_to_end_ingestion_and_repeatable_indexing(tmp_path: Path) -> None:
    db_path = tmp_path / "test_ingest.db"
    store = IngestionStore(db_path)
    qdrant_store = QdrantVectorStore(location=":memory:")
    embedder = DeterministicMockEmbeddingAdapter(dimension=128)
    indexer = VectorIndexer(
        embedding_adapter=embedder,
        vector_store=qdrant_store,
        collection_name="test_chunks",
    )

    settings = Settings(_env_file=None)
    service = IngestionService(
        settings=settings,
        store=store,
        vector_indexer=indexer,
    )

    doc_bytes = (
        b"# 1.0 General Provisions\n\n"
        b"All structural steel shall conform to IS 2062 Grade E250.\n\n"
        b"## 1.1 Fasteners\n\n"
        b"High strength friction grip bolts must adhere to IS 3757.\n"
    )
    meta_v1 = _sample_doc_metadata(version="v1.0")

    # 1. Initial ingestion
    res_1 = service.ingest_bytes("steel_spec.md", doc_bytes, meta_v1)
    assert res_1.status == "ingested"
    assert not res_1.unchanged
    assert res_1.chunks_created > 0
    assert res_1.vectors_indexed == res_1.chunks_created

    # Verify Qdrant points count
    total_qdrant_points = qdrant_store.count("test_chunks")
    assert total_qdrant_points == res_1.chunks_created
    doc_points = qdrant_store.count("test_chunks", doc_id=res_1.doc_id)
    assert doc_points == res_1.chunks_created

    # 2. Repeat ingestion with identical content and manifest (unchanged detection)
    res_2 = service.ingest_bytes("steel_spec.md", doc_bytes, meta_v1)
    assert res_2.status == "unchanged"
    assert res_2.unchanged
    assert res_2.vectors_indexed == 0

    # Ensure no duplicates: point count remains unchanged
    assert qdrant_store.count("test_chunks") == total_qdrant_points

    # 3. Document revision / update: modified text and updated version
    updated_doc_bytes = (
        b"# 1.0 General Provisions\n\n"
        b"All structural steel shall conform to IS 2062 Grade E350 (Revised).\n\n"
        b"## 1.1 Fasteners\n\n"
        b"High strength friction grip bolts must adhere to IS 3757.\n\n"
        b"## 1.2 Welding\n\n"
        b"Submerged arc welding shall follow AWS D1.1 standards.\n"
    )
    meta_v2 = _sample_doc_metadata(version="v2.0")

    res_3 = service.ingest_bytes("steel_spec.md", updated_doc_bytes, meta_v2)
    assert res_3.status == "updated"
    assert not res_3.unchanged
    assert res_3.doc_id == res_1.doc_id
    assert res_3.vectors_indexed == res_3.chunks_created

    # Verify old points were replaced and no stale vectors remain
    new_doc_points = qdrant_store.count("test_chunks", doc_id=res_1.doc_id)
    assert new_doc_points == res_3.chunks_created
    assert qdrant_store.count("test_chunks") == res_3.chunks_created

    # 4. Search verification: query vector returns the updated content
    query_vec = embedder.embed_query("steel Grade E350")
    search_hits = qdrant_store.search("test_chunks", query_vec, limit=3)
    assert len(search_hits) > 0
    assert any("E350 (Revised)" in hit.text_verbatim for hit in search_hits)


def test_multi_document_coexistence_and_project_scoping(tmp_path: Path) -> None:
    db_path = tmp_path / "multi_doc.db"
    store = IngestionStore(db_path)
    qdrant_store = QdrantVectorStore(location=":memory:")
    embedder = DeterministicMockEmbeddingAdapter(dimension=64)
    indexer = VectorIndexer(
        embedding_adapter=embedder,
        vector_store=qdrant_store,
        collection_name="multi_scope",
    )

    settings = Settings(_env_file=None)
    service = IngestionService(
        settings=settings,
        store=store,
        vector_indexer=indexer,
    )

    # Document 1: Project-specific spec (#104)
    doc1_bytes = b"# Site Specification\n\nConcrete mix grade for Project 104 is M35.\n"
    meta1 = _sample_doc_metadata(
        doc_title="Site 104 Spec",
        project_id="#104",
        doc_type=DocumentType.SPEC,
    )
    res1 = service.ingest_bytes("spec_104.md", doc1_bytes, meta1)

    # Document 2: General regulatory building code (project_id=None)
    doc2_bytes = (
        b"# National Building Code\n\nMinimum curing period under normal weather is 7 days.\n"
    )
    meta2 = _sample_doc_metadata(
        doc_title="National Building Code",
        project_id=None,
        doc_type=DocumentType.CODE,
    )
    res2 = service.ingest_bytes("nbc_code.md", doc2_bytes, meta2)

    # Both documents indexed
    assert qdrant_store.count("multi_scope", doc_id=res1.doc_id) == res1.chunks_created
    assert qdrant_store.count("multi_scope", doc_id=res2.doc_id) == res2.chunks_created
    assert qdrant_store.count("multi_scope") == res1.chunks_created + res2.chunks_created

    # Query with project scoping: project_id == '#104' retrieves both project spec and general code
    query_vec = embedder.embed_query("concrete curing")
    scoped_hits = qdrant_store.search(
        "multi_scope",
        query_vec,
        limit=5,
        filters={"project_id": "#104"},
    )
    retrieved_doc_ids = {h.doc_id for h in scoped_hits}
    assert res1.doc_id in retrieved_doc_ids
    assert res2.doc_id in retrieved_doc_ids


def test_api_route_ingest_with_vector_indexing(tmp_path: Path) -> None:
    db_path = tmp_path / "api_test.db"
    store = IngestionStore(db_path)
    qdrant_store = QdrantVectorStore(location=":memory:")
    embedder = DeterministicMockEmbeddingAdapter(dimension=64)
    indexer = VectorIndexer(
        embedding_adapter=embedder,
        vector_store=qdrant_store,
        collection_name="api_chunks",
    )

    settings = Settings(_env_file=None)
    app = create_app(settings)
    app.state.ingestion_store = store
    app.state.vector_indexer = indexer

    client = TestClient(app)

    metadata = {
        "doc_title": "Excavation Protocol",
        "doc_type": "safety_manual",
        "jurisdiction": "IN-KA",
        "version": "1.0",
        "confidentiality_tier": "internal",
    }
    content = b"# Excavation Safety\nTrenches deeper than 1.5 meters require shoring.\n"

    response = client.post(
        "/documents/ingest",
        files={"file": ("excavation.md", content, "text/markdown")},
        data={"metadata": json.dumps(metadata)},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ingested"
    assert body["vectors_indexed"] > 0
    assert body["chunks_created"] == body["vectors_indexed"]

    # Verify points exist in Qdrant
    assert qdrant_store.count("api_chunks", doc_id=body["doc_id"]) == body["vectors_indexed"]
