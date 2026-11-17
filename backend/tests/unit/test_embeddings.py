"""Unit tests for embedding adapters (FastEmbed, OpenAI, and DeterministicMock)."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    EmbeddingProviderError,
    ValidationAppError,
)
from app.retrieval.embeddings import (
    DeterministicMockEmbeddingAdapter,
    FastEmbedAdapter,
    OpenAIEmbeddingAdapter,
    get_embedding_adapter,
)


def test_deterministic_mock_adapter_properties_and_normalization() -> None:
    adapter = DeterministicMockEmbeddingAdapter(dimension=384)
    assert adapter.model_name == "mock-deterministic"
    assert adapter.dimension == 384

    texts = [
        "Concrete minimum curing duration shall be 7 days.",
        "Scaffolding inspection must be completed daily.",
    ]
    vectors = adapter.embed_documents(texts)
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384

    # Verify unit-length normalization: ||v|| ≈ 1.0
    for vec in vectors:
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-5

    # Determinism: same input text yields identical vector
    repeat_vectors = adapter.embed_documents([texts[0]])
    assert repeat_vectors[0] == vectors[0]

    # Distinct inputs yield distinct vectors
    assert vectors[0] != vectors[1]


def test_deterministic_mock_empty_and_invalid_inputs() -> None:
    adapter = DeterministicMockEmbeddingAdapter(dimension=128)
    assert adapter.embed_documents([]) == []

    with pytest.raises(ValidationAppError):
        adapter.embed_query("")

    with pytest.raises(ValidationAppError):
        adapter.embed_query("    ")


def test_fastembed_adapter_local_inference() -> None:
    adapter = FastEmbedAdapter(model_name="BAAI/bge-small-en-v1.5")
    assert adapter.model_name == "BAAI/bge-small-en-v1.5"
    assert adapter.dimension == 384

    texts = ["Structural steel fireproofing specification", "Excavation safety perimeter"]
    embeddings = adapter.embed_documents(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384

    # Test single query embedding
    q_vec = adapter.embed_query("steel fireproofing")
    assert len(q_vec) == 384

    # Empty inputs
    assert adapter.embed_documents([]) == []
    with pytest.raises(ValidationAppError):
        adapter.embed_query("")


def test_openai_adapter_missing_key_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        OpenAIEmbeddingAdapter(api_key=None)
    assert "EMBEDDING_API_KEY" in str(exc_info.value)

    with pytest.raises(ConfigurationError):
        OpenAIEmbeddingAdapter(api_key=SecretStr("   "))


def test_openai_adapter_successful_inference_mocked() -> None:
    adapter = OpenAIEmbeddingAdapter(
        api_key=SecretStr("sk-test-key-valid"),
        model_name="text-embedding-3-small",
    )
    assert adapter.model_name == "text-embedding-3-small"
    assert adapter.dimension == 1536

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"index": 0, "embedding": [0.1] * 1536},
            {"index": 1, "embedding": [0.2] * 1536},
        ]
    }

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        vectors = adapter.embed_documents(["Text A", "Text B"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 1536
        assert vectors[0][0] == 0.1
        assert vectors[1][0] == 0.2


def test_openai_adapter_error_handling_mocked() -> None:
    adapter = OpenAIEmbeddingAdapter(api_key=SecretStr("sk-test-key"))

    # Test 401 Unauthorized
    resp_401 = MagicMock(status_code=401, text="Unauthorized")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = resp_401
        mock_client_cls.return_value = mock_client

        with pytest.raises(EmbeddingProviderError) as exc:
            adapter.embed_documents(["Hello"])
        assert exc.value.status_code == 401

    # Test 429 Rate Limit
    resp_429 = MagicMock(status_code=429, text="Rate limit exceeded")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = resp_429
        mock_client_cls.return_value = mock_client

        with pytest.raises(EmbeddingProviderError) as exc:
            adapter.embed_documents(["Hello"])
        assert exc.value.status_code == 429


def test_get_embedding_adapter_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Default to FastEmbed
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    settings = Settings(_env_file=None)
    adapter = get_embedding_adapter(settings)
    assert isinstance(adapter, FastEmbedAdapter)

    # 2. Mock provider
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_MODEL", "mock-model")
    settings_mock = Settings(_env_file=None)
    adapter_mock = get_embedding_adapter(settings_mock)
    assert isinstance(adapter_mock, DeterministicMockEmbeddingAdapter)
    assert adapter_mock.model_name == "mock-model"

    # 3. OpenAI provider
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_API_KEY", "sk-live-test-12345")
    settings_openai = Settings(_env_file=None)
    adapter_openai = get_embedding_adapter(settings_openai)
    assert isinstance(adapter_openai, OpenAIEmbeddingAdapter)

    # 4. Unsupported provider raises ConfigurationError
    monkeypatch.setenv("EMBEDDING_PROVIDER", "unknown-vendor")
    settings_invalid = Settings(_env_file=None)
    with pytest.raises(ConfigurationError):
        get_embedding_adapter(settings_invalid)
