"""Shared pytest fixtures for backend unit and integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated test settings independent of any local `.env` file."""
    return Settings(
        _env_file=None,
        environment="test",
        log_level="INFO",
        log_format="json",
        cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    """Create a FastAPI TestClient wired with isolated test settings."""
    app = create_app(settings=test_settings)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
