"""Shared API error and common Pydantic schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured error payload returned by all exception handlers."""

    code: str = Field(..., min_length=1, description="Machine-readable error code.")
    message: str = Field(..., min_length=1, description="Human-readable error summary.")
    request_id: str | None = Field(
        default=None,
        description="Correlation identifier bound to the failing request.",
    )
    details: Any | None = Field(
        default=None,
        description="Optional structured validation or diagnostic details.",
    )


class ErrorResponse(BaseModel):
    """Top-level error envelope returned for 4xx/5xx responses."""

    error: ErrorDetail
