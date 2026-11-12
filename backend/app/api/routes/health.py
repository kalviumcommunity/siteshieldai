"""Health-check endpoint for service readiness and configuration visibility."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings, get_settings
from app.schemas.health import (
    DependencyHealth,
    DependencyState,
    HealthResponse,
    HealthStatus,
)

router = APIRouter(tags=["health"])


def _get_app_settings(request: Request) -> Settings:
    """Resolve settings from app state when available, else cached defaults."""
    app_settings: Settings | None = getattr(request.app.state, "settings", None)
    return app_settings if app_settings is not None else get_settings()


def _provider_status(provider: str | None) -> DependencyHealth:
    """Report configuration status without initializing deferred RAG clients."""
    if provider:
        return DependencyHealth(
            status=DependencyState.OK,
            provider=provider,
            detail="Configured; runtime integration deferred to RAG gates.",
        )
    return DependencyHealth(
        status=DependencyState.NOT_CONFIGURED,
        provider=None,
        detail="Not configured in backend foundation stage.",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check application health",
)
async def health_check(
    settings: Annotated[Settings, Depends(_get_app_settings)],
) -> HealthResponse:
    """Return service liveness, environment metadata, and dependency status."""
    return HealthResponse(
        status=HealthStatus.OK,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
        dependencies={
            "vector_db": _provider_status(settings.vector_db_provider),
            "embedding": _provider_status(settings.embedding_provider),
            "llm": _provider_status(settings.llm_provider),
        },
    )
