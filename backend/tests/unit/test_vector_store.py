"""Unit tests for Qdrant vector database store, payload indexes, and operations."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    ResourceNotFoundError,
    ValidationAppError,
    VectorStoreError,
)
from app.ingestion.models import DocumentChunk
from app.retrieval.vector_store import (
    QdrantVectorStore,
    get_vector_store,
)
from app.schemas.documents import (
    ChunkRecord,
    ConfidentialityTier,
    ContentType,
    DocumentRecord,
    DocumentStatus,
    DocumentType,
    ExtractionMethod,
)


@pytest.fixture
def memory_vector_store() -> QdrantVectorStore:
    """Fixture providing an isolated in-memory Qdrant client."""
    return QdrantVectorStore(location=":memory:")


def _make_dummy_chunk(
    doc_id: str,
    chunk_index: int,
    text: str = "Test text",
    section_id: str = "1.0",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"chk_{doc_id}_{chunk_index}",
        doc_id=doc_id,
        chunk_index=chunk_index,
        page_start=1,
        page_end=1,
        printed_page_label="1",
        section_id=section_id,
        section_path=["1. Introduction", f"{section_id} Details"],
        content_type=ContentType.PROSE,
        extraction_method=ExtractionMethod.NATIVE,
        ocr_confidence=None,
        char_start=0,
        char_end=len(text),
        token_estimate=15,
        text_for_embedding=f"[Doc: {doc_id}] {text}",
        text_verbatim=text,
    )


def _make_dummy_doc_record(
    doc_id: str,
    project_id: str | None = None,
    doc_type: DocumentType = DocumentType.SPEC,
    jurisdiction: str = "IN-KA",
) -> DocumentRecord:
    from datetime import UTC, datetime

    return DocumentRecord(
        doc_id=doc_id,
        doc_title=f"Document {doc_id}",
        doc_type=doc_type,
        jurisdiction=jurisdiction,
        project_id=project_id,
        standard_code="IS 456" if doc_type == DocumentType.CODE else None,
        version="v1.0",
        publication_date=date(2024, 1, 15),
        effective_date=date(2024, 2, 1),
        supersedes_doc_id=None,
        status=DocumentStatus.ACTIVE,
        confidentiality_tier=ConfidentialityTier.INTERNAL,
        source_filename=f"{doc_id}.pdf",
        sha256_checksum=f"hash_{doc_id}",
        page_count=5,
        chunk_count=2,
        ingested_at=datetime.now(UTC),
    )


def test_ensure_collection_and_dimension_validation(
    memory_vector_store: QdrantVectorStore,
) -> None:
    coll = "test_dimension_coll"
    assert not memory_vector_store.collection_exists(coll)

    memory_vector_store.ensure_collection(coll, dimension=384, distance="Cosine")
    assert memory_vector_store.collection_exists(coll)

    info = memory_vector_store.get_collection_info(coll)
    assert info["dimension"] == 384
    assert "Cosine" in info["distance"]
    assert info["points_count"] == 0

    # Calling ensure_collection again with identical dimension succeeds idempotently
    memory_vector_store.ensure_collection(coll, dimension=384)

    # Calling with a different dimension raises VectorStoreError (index isolation invariant)
    with pytest.raises(VectorStoreError) as exc_info:
        memory_vector_store.ensure_collection(coll, dimension=768)
    assert exc_info.value.error_code == "VECTOR_DIMENSION_MISMATCH"


def test_get_collection_info_not_found(memory_vector_store: QdrantVectorStore) -> None:
    with pytest.raises(ResourceNotFoundError):
        memory_vector_store.get_collection_info("non_existent_coll")


def test_upsert_empty_and_mismatched_inputs(
    memory_vector_store: QdrantVectorStore,
) -> None:
    coll = "test_empty_coll"
    memory_vector_store.ensure_collection(coll, dimension=4)

    assert memory_vector_store.upsert_chunks(coll, [], []) == 0

    chunk = _make_dummy_chunk("doc_1", 0)
    with pytest.raises(ValidationAppError) as exc_info:
        memory_vector_store.upsert_chunks(
            coll,
            [chunk],
            [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]],
        )
    assert exc_info.value.error_code == "CHUNKS_EMBEDDINGS_MISMATCH"


def test_upsert_provenance_payload_and_idempotency(
    memory_vector_store: QdrantVectorStore,
) -> None:
    coll = "test_provenance_coll"
    memory_vector_store.ensure_collection(coll, dimension=4)

    doc_record = _make_dummy_doc_record("doc_alpha", project_id="#104")
    chunk_0 = _make_dummy_chunk("doc_alpha", 0, text="First clause text", section_id="2.1")
    chunk_1 = _make_dummy_chunk("doc_alpha", 1, text="Second clause text", section_id="2.2")

    vectors = [
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
    ]
    upserted = memory_vector_store.upsert_chunks(
        coll,
        [chunk_0, chunk_1],
        vectors,
        doc_record=doc_record,
    )
    assert upserted == 2
    assert memory_vector_store.count(coll) == 2
    assert memory_vector_store.count(coll, doc_id="doc_alpha") == 2

    # Verify search retrieves complete provenance payload
    results = memory_vector_store.search(coll, query_vector=[0.1, 0.2, 0.3, 0.4], limit=2)
    assert len(results) == 2
    top = results[0]
    assert top.chunk_id == "chk_doc_alpha_0"
    assert top.doc_id == "doc_alpha"
    assert top.text_verbatim == "First clause text"

    payload: dict[str, Any] = top.payload
    assert payload["doc_title"] == "Document doc_alpha"
    assert payload["doc_type"] == "spec"
    assert payload["jurisdiction"] == "IN-KA"
    assert payload["project_id"] == "#104"
    assert payload["version"] == "v1.0"
    assert payload["publication_date"] == "2024-01-15"
    assert payload["effective_date"] == "2024-02-01"
    assert payload["effective_timestamp"] is not None
    assert payload["status"] == "active"
    assert payload["section_id"] == "2.1"
    assert payload["section_path"] == ["1. Introduction", "2.1 Details"]
    assert payload["content_type"] == "prose"
    assert payload["extraction_method"] == "native"

    # Idempotent re-upsert: upserting the exact same points does not create duplicates
    re_upserted = memory_vector_store.upsert_chunks(
        coll,
        [chunk_0, chunk_1],
        vectors,
        doc_record=doc_record,
    )
    assert re_upserted == 2
    assert memory_vector_store.count(coll) == 2  # Still 2 points!


def test_upsert_with_chunk_record(memory_vector_store: QdrantVectorStore) -> None:
    coll = "test_chunk_record_coll"
    memory_vector_store.ensure_collection(coll, dimension=3)

    record = ChunkRecord(
        chunk_id="chk_from_record_1",
        doc_id="doc_beta",
        doc_title="Code Spec 2024",
        doc_type=DocumentType.CODE,
        jurisdiction="GLOBAL",
        project_id=None,
        standard_code="IBC-2024",
        version="v2.0",
        publication_date=date(2024, 3, 1),
        effective_date=date(2024, 4, 1),
        status=DocumentStatus.ACTIVE,
        confidentiality_tier=ConfidentialityTier.PUBLIC,
        source_filename="ibc_2024.pdf",
        sha256_checksum="hash_beta",
        chunk_index=0,
        page_start=10,
        page_end=10,
        printed_page_label="X",
        section_id="5.4",
        section_path=["5. Fire", "5.4 Egress"],
        content_type=ContentType.LIST,
        extraction_method=ExtractionMethod.NATIVE,
        ocr_confidence=None,
        char_start=100,
        char_end=250,
        token_estimate=35,
        text_for_embedding="[Doc: Code Spec 2024] Egress width must be at least 1200 mm",
        text_verbatim="Egress width must be at least 1200 mm",
    )

    upserted = memory_vector_store.upsert_chunks(coll, [record], [[0.3, 0.4, 0.5]])
    assert upserted == 1
    assert memory_vector_store.count(coll, doc_id="doc_beta") == 1


def test_delete_by_doc_id_isolation(memory_vector_store: QdrantVectorStore) -> None:
    coll = "test_delete_isolation_coll"
    memory_vector_store.ensure_collection(coll, dimension=2)

    doc_a = _make_dummy_doc_record("doc_A")
    doc_b = _make_dummy_doc_record("doc_B")

    chunks_a = [_make_dummy_chunk("doc_A", 0), _make_dummy_chunk("doc_A", 1)]
    chunks_b = [_make_dummy_chunk("doc_B", 0)]

    memory_vector_store.upsert_chunks(coll, chunks_a, [[0.1, 0.1], [0.2, 0.2]], doc_record=doc_a)
    memory_vector_store.upsert_chunks(coll, chunks_b, [[0.9, 0.9]], doc_record=doc_b)

    assert memory_vector_store.count(coll) == 3
    assert memory_vector_store.count(coll, doc_id="doc_A") == 2
    assert memory_vector_store.count(coll, doc_id="doc_B") == 1

    # Delete Doc A points
    deleted = memory_vector_store.delete_by_doc_id(coll, "doc_A")
    assert deleted == 2
    assert memory_vector_store.count(coll, doc_id="doc_A") == 0
    assert memory_vector_store.count(coll, doc_id="doc_B") == 1
    assert memory_vector_store.count(coll) == 1

    # Delete non-existent doc gracefully returns 0
    assert memory_vector_store.delete_by_doc_id(coll, "doc_nonexistent") == 0


def test_search_and_metadata_filtering(memory_vector_store: QdrantVectorStore) -> None:
    coll = "test_search_filters_coll"
    memory_vector_store.ensure_collection(coll, dimension=2)

    doc_spec = _make_dummy_doc_record("spec_104", project_id="#104", doc_type=DocumentType.SPEC)
    doc_code = _make_dummy_doc_record(
        "code_is456", project_id=None, doc_type=DocumentType.CODE, jurisdiction="IN-KA"
    )

    chk_spec = _make_dummy_chunk("spec_104", 0, text="Site concrete mix design")
    chk_code = _make_dummy_chunk("code_is456", 0, text="IS 456 general curing table")

    memory_vector_store.upsert_chunks(coll, [chk_spec], [[0.8, 0.2]], doc_record=doc_spec)
    memory_vector_store.upsert_chunks(coll, [chk_code], [[0.1, 0.9]], doc_record=doc_code)

    # 1. Search empty collection or non-matching filter
    res_empty = memory_vector_store.search(
        coll, [0.8, 0.2], filters={"jurisdiction": "NON_EXISTENT"}
    )
    assert len(res_empty) == 0

    # 2. Filter by doc_id
    res_doc = memory_vector_store.search(coll, [0.8, 0.2], filters={"doc_id": "spec_104"})
    assert len(res_doc) == 1
    assert res_doc[0].doc_id == "spec_104"

    # 3. Project scoping filter: project_id == '#104' OR
    # (project_id IS NULL AND doc_type IN ['code', 'safety_manual'])
    res_scoped = memory_vector_store.search(
        coll, [0.5, 0.5], limit=5, filters={"project_id": "#104"}
    )
    assert len(res_scoped) == 2
    matched_docs = {r.doc_id for r in res_scoped}
    assert matched_docs == {"spec_104", "code_is456"}


def test_get_vector_store_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None)
    store = get_vector_store(settings, location=":memory:")
    assert isinstance(store, QdrantVectorStore)

    monkeypatch.setenv("VECTOR_DB_PROVIDER", "unsupported-db")
    settings_invalid = Settings(_env_file=None)
    with pytest.raises(ConfigurationError):
        get_vector_store(settings_invalid)
