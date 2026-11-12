"""Unit tests for document upload validation and magic-byte guardrails."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import PayloadTooLargeError, ValidationAppError
from app.ingestion.validator import validate_document_input


def test_validate_supported_formats() -> None:
    settings = Settings(_env_file=None)
    assert validate_document_input("code.pdf", b"%PDF-1.4\n...", settings) == ("code.pdf", ".pdf")
    assert validate_document_input("notes.MD", b"# Title\nContent", settings) == ("notes.MD", ".md")
    assert validate_document_input("spec.txt", b"Clause 1.1", settings) == ("spec.txt", ".txt")


def test_validate_rejects_unsupported_extension() -> None:
    settings = Settings(_env_file=None)
    with pytest.raises(ValidationAppError) as exc_info:
        validate_document_input("payload.exe", b"MZ...", settings)
    assert exc_info.value.error_code == "UNSUPPORTED_DOCUMENT_FORMAT"


def test_validate_rejects_empty_and_whitespace_files() -> None:
    settings = Settings(_env_file=None)
    with pytest.raises(ValidationAppError) as empty_exc:
        validate_document_input("empty.pdf", b"", settings)
    assert empty_exc.value.error_code == "EMPTY_DOCUMENT"

    with pytest.raises(ValidationAppError) as blank_exc:
        validate_document_input("blank.txt", b"   \n\t  ", settings)
    assert blank_exc.value.error_code == "EMPTY_DOCUMENT"


def test_validate_rejects_oversized_upload() -> None:
    settings = Settings(_env_file=None, max_upload_size_mb=1)
    oversized = b"a" * (1024 * 1024 + 1)
    with pytest.raises(PayloadTooLargeError):
        validate_document_input("big.txt", oversized, settings)


def test_validate_rejects_malformed_magic_bytes_and_encoding() -> None:
    settings = Settings(_env_file=None)
    with pytest.raises(ValidationAppError) as pdf_exc:
        validate_document_input("fake.pdf", b"not actually a pdf", settings)
    assert pdf_exc.value.error_code == "MALFORMED_DOCUMENT"

    with pytest.raises(ValidationAppError) as bin_exc:
        validate_document_input("binary.txt", b"hello\x00world", settings)
    assert bin_exc.value.error_code == "MALFORMED_DOCUMENT"

    with pytest.raises(ValidationAppError) as utf_exc:
        validate_document_input("bad_utf8.md", b"\xff\xfe\xfd", settings)
    assert utf_exc.value.error_code == "MALFORMED_DOCUMENT"

