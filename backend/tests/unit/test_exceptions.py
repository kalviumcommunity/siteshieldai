"""Unit tests for custom application exception classes."""

from __future__ import annotations

from app.core.exceptions import (
    AppError,
    ConfigurationError,
    ConflictAppError,
    PayloadTooLargeError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationAppError,
)


def test_exception_status_and_codes() -> None:
    cases = [
        (ConfigurationError("bad cfg"), 500, "CONFIGURATION_ERROR"),
        (ValidationAppError("bad input"), 422, "VALIDATION_ERROR"),
        (ResourceNotFoundError("missing"), 404, "RESOURCE_NOT_FOUND"),
        (ConflictAppError("duplicate"), 409, "CONFLICT_ERROR"),
        (PayloadTooLargeError("too big"), 413, "PAYLOAD_TOO_LARGE"),
        (ServiceUnavailableError("down"), 503, "SERVICE_UNAVAILABLE"),
    ]
    for exc, expected_status, expected_code in cases:
        assert isinstance(exc, AppError)
        assert exc.status_code == expected_status
        assert exc.error_code == expected_code
        assert str(exc) == exc.message
