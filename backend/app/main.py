"""FastAPI application factory and ASGI entrypoint for Site Shield AI."""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, request_id_ctx

logger = logging.getLogger(__name__)

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _resolve_request_id(header_value: str | None) -> str:
    """Validate an incoming X-Request-ID header or generate a safe UUID."""
    if header_value and _REQUEST_ID_PATTERN.match(header_value.strip()):
        return header_value.strip()
    return uuid.uuid4().hex


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    resolved_settings = settings if settings is not None else get_settings()
    configure_logging(
        log_level=resolved_settings.log_level,
        log_format=resolved_settings.log_format,
    )

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="AI-Powered Construction Compliance Assistant API",
    )
    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _resolve_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "Unhandled exception in middleware",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "HTTP request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        finally:
            request_id_ctx.reset(token)

    register_exception_handlers(app)
    app.include_router(api_router)

    logger.info(
        "Application initialized",
        extra={
            "service": resolved_settings.app_name,
            "version": resolved_settings.app_version,
            "environment": resolved_settings.environment,
        },
    )
    return app


app = create_app()

