"""Structured logging configuration with request correlation and secret redaction."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

_STANDARD_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)

_SENSITIVE_FRAGMENTS = ("api_key", "apikey", "password", "secret", "token", "authorization")


def _redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask sensitive keys in structured log payloads."""
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        lowered = key.lower()
        if any(fragment in lowered for fragment in _SENSITIVE_FRAGMENTS):
            cleaned[key] = "***REDACTED***"
        elif isinstance(value, dict):
            cleaned[key] = _redact_mapping(value)
        else:
            cleaned[key] = value
    return cleaned


class JsonLogFormatter(logging.Formatter):
    """Format log records as single-line JSON with UTC timestamp and request_id."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = request_id_ctx.get()
        if request_id is not None:
            payload["request_id"] = request_id

        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _STANDARD_RECORD_ATTRS and not k.startswith("_")
        }
        if extra_fields:
            payload.update(_redact_mapping(extra_fields))

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleLogFormatter(logging.Formatter):
    """Human-readable structured formatter for local console development."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        request_id = request_id_ctx.get() or "-"
        base = (
            f"{ts} | {record.levelname:<8} | {record.name} "
            f"| req={request_id} | {record.getMessage()}"
        )
        if record.exc_info:
            return f"{base}\n{self.formatException(record.exc_info)}"
        return base


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure root and Uvicorn loggers without duplicating handlers."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    formatter: logging.Formatter = (
        ConsoleLogFormatter() if log_format == "console" else JsonLogFormatter()
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
        uv_logger.setLevel(level)
