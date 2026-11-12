"""Environment-driven application configuration using Pydantic Settings."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_string_list(raw: Any) -> list[str]:
    """Parse a JSON array string, comma-separated string, or list into cleaned items."""
    if isinstance(raw, list):
        items = [str(item).strip() for item in raw]
    elif isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            if not isinstance(parsed, list):
                raise ValueError("Expected a JSON list of strings.")
            items = [str(item).strip() for item in parsed]
        else:
            items = [part.strip() for part in stripped.split(",")]
    else:
        raise ValueError("Expected a list or comma-separated string.")

    return [item for item in items if item]


class Settings(BaseSettings):
    """Typed application settings populated from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Site Shield AI"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # Provider placeholders (configuration only; clients implemented in subsequent gates)
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None

    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_api_key: SecretStr | None = None

    vector_db_provider: str | None = None
    vector_db_path: str | None = None
    vector_db_url: str | None = None
    vector_db_collection: str = "siteshield_chunks"

    # Ingestion guardrails (configuration only)
    max_upload_size_mb: int = Field(default=25, ge=1, le=500)
    allowed_document_extensions: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [".pdf", ".md", ".txt"]
    )

    # Frontend API reference
    api_base_url: str = "http://127.0.0.1:8000"

    @field_validator("*", mode="before")
    @classmethod
    def _blank_env_to_default(cls, value: Any, info: ValidationInfo) -> Any:
        """Convert empty-string environment variables to each field's default."""
        if isinstance(value, str) and not value.strip() and info.field_name:
            field = cls.model_fields[info.field_name]
            return field.get_default(call_default_factory=True)
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> Any:
        """Normalize log level casing."""
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("environment", "log_format", mode="before")
    @classmethod
    def _normalize_lowercase_literal(cls, value: Any) -> Any:
        """Normalize lowercase literal settings."""
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        """Parse comma-separated or JSON CORS origins."""
        origins = _parse_string_list(value)
        return origins or ["http://localhost:3000"]

    @field_validator("allowed_document_extensions", mode="before")
    @classmethod
    def _parse_allowed_extensions(cls, value: Any) -> list[str]:
        """Normalize allowed extensions to lowercase with a leading dot."""
        raw_exts = _parse_string_list(value)
        normalized = [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in raw_exts]
        return normalized or [".pdf", ".md", ".txt"]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
