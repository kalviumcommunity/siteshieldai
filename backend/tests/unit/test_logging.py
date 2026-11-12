"""Unit tests for structured JSON logging and correlation context."""

from __future__ import annotations

import json
import logging

from app.core.logging import JsonLogFormatter, configure_logging, request_id_ctx


def test_json_formatter_includes_request_id_and_redacts_secrets() -> None:
    formatter = JsonLogFormatter()
    token = request_id_ctx.set("req-abc-123")
    try:
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Processing test event",
            args=(),
            exc_info=None,
        )
        record.api_key = "super-secret-key"
        record.nested = {"auth_token": "bearer-xyz", "safe_field": 42}

        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "app.test"
        assert parsed["message"] == "Processing test event"
        assert parsed["request_id"] == "req-abc-123"
        assert parsed["api_key"] == "***REDACTED***"
        assert parsed["nested"] == {"auth_token": "***REDACTED***", "safe_field": 42}
        assert "timestamp" in parsed
    finally:
        request_id_ctx.reset(token)


def test_configure_logging_does_not_duplicate_handlers() -> None:
    configure_logging(log_level="DEBUG", log_format="json")
    configure_logging(log_level="INFO", log_format="json")
    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert root.level == logging.INFO
