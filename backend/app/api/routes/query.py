"""Compliance query and grounded retrieval API route."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings, get_settings
from app.generation.service import QueryService
from app.schemas.query import QueryRequest, QueryResponse

router = APIRouter(tags=["query"])


def _get_settings(request: Request) -> Settings:
    app_settings: Settings | None = getattr(request.app.state, "settings", None)
    return app_settings if app_settings is not None else get_settings()


def _get_query_service(
    request: Request,
    settings: Annotated[Settings, Depends(_get_settings)],
) -> QueryService:
    service: QueryService | None = getattr(request.app.state, "query_service", None)
    if service is None:
        service = QueryService(settings=settings)
        request.app.state.query_service = service
    return service


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a construction compliance or regulatory question",
)
async def query_compliance(
    request_data: QueryRequest,
    service: Annotated[QueryService, Depends(_get_query_service)],
) -> QueryResponse:
    """Execute grounded retrieval, conflict detection, and verified citation answering."""
    return service.execute_query(request_data)
