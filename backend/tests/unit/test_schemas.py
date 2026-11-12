"""Unit tests for Pydantic request and response schemas."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.schemas import (
    CitationItem,
    ConfidentialityTier,
    ContentType,
    DocumentIngestMetadata,
    DocumentType,
    ErrorDetail,
    ErrorResponse,
    EvaluationMetrics,
    EvaluationSummaryResponse,
    ExtractionMethod,
    QueryRequest,
    QueryResponse,
    QueryStatus,
)


def test_document_ingest_metadata_validates_dates_and_trims() -> None:
    meta = DocumentIngestMetadata(
        doc_title="  National Building Code  ",
        doc_type=DocumentType.CODE,
        jurisdiction="  IN-KA  ",
        project_id="   ",
        version=" v1.0 ",
        publication_date=date(2025, 1, 1),
        effective_date=date(2025, 2, 1),
        confidentiality_tier=ConfidentialityTier.INTERNAL,
    )
    assert meta.doc_title == "National Building Code"
    assert meta.jurisdiction == "IN-KA"
    assert meta.project_id is None
    assert meta.version == "v1.0"


def test_document_ingest_metadata_rejects_effective_before_publication() -> None:
    with pytest.raises(ValidationError):
        DocumentIngestMetadata(
            doc_title="Concrete Spec",
            doc_type=DocumentType.SPEC,
            version="v1.0",
            publication_date=date(2026, 5, 10),
            effective_date=date(2026, 5, 1),
        )


def test_query_request_validation() -> None:
    req = QueryRequest(query="  What is minimum curing time?  ", top_k=3)
    assert req.query == "What is minimum curing time?"
    assert req.top_k == 3
    assert req.filters.include_superseded is False

    with pytest.raises(ValidationError):
        QueryRequest(query="   ")

    with pytest.raises(ValidationError):
        QueryRequest(query="valid", top_k=25)


def test_query_response_and_evaluation_schemas() -> None:
    citation = CitationItem(
        evidence_id="E1",
        chunk_id="chk_123",
        doc_id="doc_1",
        doc_title="Concrete Spec",
        doc_type=DocumentType.SPEC,
        version="Rev 1",
        jurisdiction="IN-KA",
        section_id="4.2.1",
        section_path=["4. Concrete", "4.2 Curing"],
        page_start=5,
        page_end=5,
        content_type=ContentType.PROSE,
        extraction_method=ExtractionMethod.NATIVE,
        retrieval_score=0.91,
        text_verbatim="Minimum curing time is 7 days.",
    )
    response = QueryResponse(
        query_id="qry_1",
        status=QueryStatus.SUPPORTED,
        answer="Minimum curing time is 7 days [E1].",
        citations=[citation],
    )
    assert response.citations[0].evidence_id == "E1"

    summary = EvaluationSummaryResponse(
        run_id="eval_1",
        executed_at=datetime.now(UTC),
        dataset_size=20,
        metrics=EvaluationMetrics(
            recall_at_3=0.9,
            precision_at_3=0.8,
            citation_coverage_rate=1.0,
            abstention_accuracy=1.0,
            conflict_detection_f1=0.95,
            p50_latency_ms=1200,
            p95_latency_ms=2500,
        ),
    )
    assert summary.metrics.recall_at_3 == 0.9

    err = ErrorResponse(error=ErrorDetail(code="TEST_ERR", message="failed"))
    assert err.error.code == "TEST_ERR"
