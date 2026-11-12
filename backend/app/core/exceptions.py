"""Application exceptions and centralized FastAPI error handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application exception mapped to the standard API error envelope."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.details = details


class ConfigurationError(AppError):
    """Raised when required application configuration is invalid or missing."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "CONFIGURATION_ERROR"


class ValidationAppError(AppError):
    """Raised for domain-level input validation failures."""

    status_code = 422
    error_code = "VALIDATION_ERROR"


class ResourceNotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"


class ConflictAppError(AppError):
    """Raised on duplicate or conflicting resource state."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT_ERROR"


class PayloadTooLargeError(AppError):
    """Raised when an uploaded payload exceeds configured size bounds."""

    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    error_code = "PAYLOAD_TOO_LARGE"


class ServiceUnavailableError(AppError):
    """Raised when a required backend dependency is unreachable."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"


def _build_error_response(
    *,
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    """Serialize an error payload conforming to ErrorResponse."""
    request_id = request_id_ctx.get() or getattr(request.state, "request_id", None)
    payload = ErrorResponse(
        error=ErrorDetail(
            code=error_code,
            message=message,
            request_id=request_id,
            details=details,
        )
    )
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(exclude_none=True),
        headers=headers,
    )


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    log_fn = logger.error if exc.status_code >= 500 else logger.warning
    log_fn(
        "Application error handled",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "error_message": exc.message,
        },
    )
    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    sanitized_errors = [
        {
            "loc": list(err.get("loc", ())),
            "msg": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error"),
        }
        for err in exc.errors()
    ]
    logger.warning(
        "Request validation failed",
        extra={"path": request.url.path, "error_count": len(sanitized_errors)},
    )
    return _build_error_response(
        request=request,
        status_code=422,
        error_code="REQUEST_VALIDATION_ERROR",
        message="Request validation failed.",
        details=sanitized_errors,
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning(
        "HTTP exception handled",
        extra={"status_code": exc.status_code, "path": request.url.path},
    )
    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail) if exc.detail else "HTTP error occurred.",
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    token = None
    request_id = getattr(request.state, "request_id", None)
    if request_id and request_id_ctx.get() is None:
        token = request_id_ctx.set(request_id)
    try:
        logger.exception(
            "Unhandled exception during request processing",
            extra={"path": request.url.path, "exception_type": type(exc).__name__},
        )
        return _build_error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message="An internal server error occurred.",
        )
    finally:
        if token is not None:
            request_id_ctx.reset(token)


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers on the FastAPI application."""
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError,
        _handle_validation_error,  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        StarletteHTTPException,
        _handle_http_exception,  # type: ignore[arg-type]
    )
    app.add_exception_handler(Exception, _handle_unexpected_error)
