"""Unit tests for environment-based configuration settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_defaults_without_env_file(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "APP_NAME",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "API_HOST",
        "API_PORT",
        "CORS_ORIGINS",
        "MAX_UPLOAD_SIZE_MB",
        "ALLOWED_DOCUMENT_EXTENSIONS",
    ):
        monkeypatch.delenv(var, raising=False)

    settings = Settings(_env_file=None)
    assert settings.app_name == "Site Shield AI"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.cors_origins == ["http://localhost:3000"]
    assert settings.max_upload_size_mb == 25
    assert settings.allowed_document_extensions == [".pdf", ".md", ".txt"]


def test_blank_env_vars_fallback_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_HOST", "")
    monkeypatch.setenv("API_PORT", "   ")
    monkeypatch.setenv("CORS_ORIGINS", "")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "")
    monkeypatch.setenv("ALLOWED_DOCUMENT_EXTENSIONS", "")
    monkeypatch.setenv("LLM_PROVIDER", "")

    settings = Settings(_env_file=None)
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.cors_origins == ["http://localhost:3000"]
    assert settings.max_upload_size_mb == 25
    assert settings.allowed_document_extensions == [".pdf", ".md", ".txt"]
    assert settings.llm_provider is None


def test_env_csv_and_json_list_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com, http://127.0.0.1:3000")
    monkeypatch.setenv("ALLOWED_DOCUMENT_EXTENSIONS", '["PDF", ".docx"]')
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-secret")

    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["https://app.example.com", "http://127.0.0.1:3000"]
    assert settings.allowed_document_extensions == [".pdf", ".docx"]
    assert settings.log_level == "DEBUG"
    assert settings.environment == "production"
    assert settings.llm_api_key is not None
    assert "sk-test-secret" not in repr(settings.llm_api_key)


def test_invalid_port_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", "70000")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
