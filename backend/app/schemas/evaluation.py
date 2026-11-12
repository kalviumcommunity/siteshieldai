"""Pydantic schemas for RAG evaluation benchmark summaries."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    """Measured retrieval, grounding, safety, and latency metrics."""

    recall_at_3: float = Field(..., ge=0.0, le=1.0)
    precision_at_3: float = Field(..., ge=0.0, le=1.0)
    citation_coverage_rate: float = Field(..., ge=0.0, le=1.0)
    abstention_accuracy: float = Field(..., ge=0.0, le=1.0)
    conflict_detection_f1: float = Field(..., ge=0.0, le=1.0)
    p50_latency_ms: int = Field(..., ge=0)
    p95_latency_ms: int = Field(..., ge=0)


class EvaluationSummaryResponse(BaseModel):
    """Response contract for GET /evaluation/summary."""

    run_id: str
    executed_at: datetime | None = None
    dataset_size: int = Field(..., ge=0)
    metrics: EvaluationMetrics
