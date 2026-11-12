"""Input validation and magic-byte guardrails for uploaded documents."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import PayloadTooLargeError, ValidationAppError


def validate_document_input(
    filename: str,
    data: bytes,
    settings: Settings,
) -> tuple[str, str]:
    """Validate filename, extension, size, non-emptiness, and file signature."""
    clean_name = Path(filename).name.strip()
    if not clean_name:
        raise ValidationAppError(
            "Uploaded filename is missing.",
            error_code="INVALID_FILENAME",
        )

    ext = Path(clean_name).suffix.lower()
    if ext not in settings.allowed_document_extensions:
        raise ValidationAppError(
            f"Unsupported document format '{ext or 'none'}'.",
            error_code="UNSUPPORTED_DOCUMENT_FORMAT",
            details={"allowed_extensions": settings.allowed_document_extensions},
        )

    if not data:
        raise ValidationAppError(
            f"Document '{clean_name}' is empty (0 bytes).",
            error_code="EMPTY_DOCUMENT",
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise PayloadTooLargeError(
            f"Document exceeds maximum upload size of {settings.max_upload_size_mb} MB.",
            details={"size_bytes": len(data), "max_bytes": max_bytes},
        )

    if ext == ".pdf":
        if b"%PDF-" not in data[:1024]:
            raise ValidationAppError(
                f"File '{clean_name}' does not have a valid PDF header.",
                error_code="MALFORMED_DOCUMENT",
            )
    else:
        if b"\x00" in data:
            raise ValidationAppError(
                f"Text document '{clean_name}' contains binary null bytes.",
                error_code="MALFORMED_DOCUMENT",
            )
        try:
            decoded = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationAppError(
                f"Text document '{clean_name}' is not valid UTF-8.",
                error_code="MALFORMED_DOCUMENT",
            ) from exc
        if not decoded.strip():
            raise ValidationAppError(
                f"Document '{clean_name}' contains only whitespace.",
                error_code="EMPTY_DOCUMENT",
            )

    return clean_name, ext

