"""Health-check response schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    """Overall service health state."""

    OK = "ok"
    DEGRADED = "degraded"


class DependencyState(StrEnum):
    """Readiness state for an optional or deferred backend dependency."""

    OK = "ok"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"


class DependencyHealth(BaseModel):
    """Status summary for a configured infrastructure or model provider."""

    status: DependencyState
    provider: str | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    """Response contract for GET /health."""

    status: HealthStatus
    service: str
    version: str
    environment: str
    timestamp: datetime
    dependencies: dict[str, DependencyHealth] = Field(default_factory=dict)
