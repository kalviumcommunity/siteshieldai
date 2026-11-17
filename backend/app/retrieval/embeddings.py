"""Embedding provider abstraction, implementations, and factory."""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Any, Protocol, runtime_checkable

from pydantic import SecretStr

from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    EmbeddingProviderError,
    ValidationAppError,
)

logger = logging.getLogger(__name__)

KNOWN_DIMENSIONS: dict[str, int] = {
    "baai/bge-base-en-v1.5": 768,
    "baai/bge-base-en": 768,
    "baai/bge-small-en-v1.5": 384,
    "baai/bge-small-en": 384,
    "baai/bge-large-en-v1.5": 1024,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


@runtime_checkable
class EmbeddingAdapter(Protocol):
    """Unified protocol for embedding generation adapters."""

    @property
    def model_name(self) -> str:
        """Return the canonical model identifier."""
        ...

    @property
    def dimension(self) -> int:
        """Return the vector dimensionality produced by this model."""
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Compute normalized vector embeddings for a list of document chunk texts."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Compute a normalized vector embedding for a single user query."""
        ...


class FastEmbedAdapter:
    """Local, in-process embedding adapter powered by FastEmbed and ONNX Runtime.

    Zero external network transmission; safe for air-gapped and confidential construction data.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        batch_size: int = 32,
    ) -> None:
        self._model_name = model_name
        self._batch_size = batch_size
        self._model: Any | None = None
        self._dimension: int | None = KNOWN_DIMENSIONS.get(model_name.lower())

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._load_model()
            probe = self.embed_query("dimension probe")
            self._dimension = len(probe)
        return self._dimension

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from fastembed import TextEmbedding

                logger.info(
                    "Initializing FastEmbed model",
                    extra={"model_name": self._model_name},
                )
                self._model = TextEmbedding(model_name=self._model_name)
            except Exception as exc:
                logger.error(
                    "Failed to initialize FastEmbed model",
                    extra={"model_name": self._model_name, "error": str(exc)},
                )
                raise EmbeddingProviderError(
                    f"FastEmbed initialization failed for '{self._model_name}': {exc}",
                    error_code="EMBEDDING_INIT_FAILED",
                ) from exc
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings for a sequence of texts."""
        if not texts:
            return []

        model = self._load_model()
        try:
            embeddings_gen = model.embed(texts, batch_size=self._batch_size)
            vectors: list[list[float]] = []
            for vec in embeddings_gen:
                vectors.append([float(x) for x in vec])
            if self._dimension is None and vectors:
                self._dimension = len(vectors[0])
            return vectors
        except Exception as exc:
            logger.error(
                "FastEmbed inference failure",
                extra={"model_name": self._model_name, "count": len(texts), "error": str(exc)},
            )
            raise EmbeddingProviderError(
                f"FastEmbed inference failed: {exc}",
                error_code="EMBEDDING_INFERENCE_FAILED",
            ) from exc

    def embed_query(self, text: str) -> list[float]:
        """Compute an embedding for a single query text."""
        cleaned = text.strip() if text else ""
        if not cleaned:
            raise ValidationAppError(
                "Query text cannot be empty or whitespace-only.",
                error_code="EMPTY_QUERY_TEXT",
            )
        vectors = self.embed_documents([cleaned])
        return vectors[0]


class OpenAIEmbeddingAdapter:
    """Cloud embedding adapter for OpenAI's embeddings API (e.g., text-embedding-3-small).

    Requires explicit EMBEDDING_API_KEY environment variable.
    """

    def __init__(
        self,
        api_key: str | SecretStr | None,
        model_name: str = "text-embedding-3-small",
        api_base: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self._model_name = model_name
        self._api_base = api_base.rstrip("/")
        self._timeout = timeout

        if isinstance(api_key, SecretStr):
            raw_key = api_key.get_secret_value()
        else:
            raw_key = str(api_key or "")

        if not raw_key.strip():
            raise ConfigurationError(
                "EMBEDDING_API_KEY environment variable is required when using the "
                "OpenAI embedding provider.",
                error_code="MISSING_EMBEDDING_API_KEY",
            )
        self._api_key = raw_key.strip()
        self._dimension = KNOWN_DIMENSIONS.get(model_name.lower(), 1536)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI /v1/embeddings endpoint for a batch of documents."""
        if not texts:
            return []

        import httpx

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model_name,
            "input": texts,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._api_base}/embeddings",
                    json=payload,
                    headers=headers,
                )
        except Exception as exc:
            logger.error(
                "OpenAI embedding request network failure",
                extra={"model": self._model_name, "error": str(exc)},
            )
            raise EmbeddingProviderError(
                f"Failed to connect to OpenAI embedding service: {exc}",
                error_code="EMBEDDING_NETWORK_ERROR",
            ) from exc

        if resp.status_code == 401 or resp.status_code == 403:
            raise EmbeddingProviderError(
                "OpenAI authentication failed: invalid or unauthorized API key.",
                status_code=401,
                error_code="EMBEDDING_AUTH_ERROR",
            )
        if resp.status_code == 429:
            raise EmbeddingProviderError(
                "OpenAI rate limit or quota exceeded.",
                status_code=429,
                error_code="EMBEDDING_RATE_LIMITED",
            )
        if resp.status_code >= 400:
            raise EmbeddingProviderError(
                f"OpenAI embedding API returned HTTP {resp.status_code}: {resp.text}",
                status_code=503,
                error_code="EMBEDDING_API_ERROR",
            )

        data = resp.json()
        items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        results = [item["embedding"] for item in items]
        if results and self._dimension != len(results[0]):
            self._dimension = len(results[0])
        return results

    def embed_query(self, text: str) -> list[float]:
        """Compute an embedding for a query text."""
        cleaned = text.strip() if text else ""
        if not cleaned:
            raise ValidationAppError(
                "Query text cannot be empty or whitespace-only.",
                error_code="EMPTY_QUERY_TEXT",
            )
        vectors = self.embed_documents([cleaned])
        return vectors[0]


class DeterministicMockEmbeddingAdapter:
    """Fast, reproducible mock embedding adapter for testing and CI.

    Generates deterministic, unit-length normalized vectors from text hashes without
    network requests or heavy model downloads.
    """

    def __init__(
        self,
        model_name: str = "mock-deterministic",
        dimension: int = 768,
    ) -> None:
        self._model_name = model_name
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _hash_to_vector(self, text: str) -> list[float]:
        import re

        cleaned = text.strip() if text else ""
        if not cleaned:
            return [0.0] * self._dimension

        tokens = re.findall(r"\b[A-Za-z0-9]+\b", cleaned.lower())
        values = [0.0] * self._dimension

        # Whole-string base hash
        digest = hashlib.sha256(cleaned.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big")
        state = seed
        for i in range(self._dimension):
            state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            val = ((state / 0xFFFFFFFFFFFFFFFF) * 2.0) - 1.0
            values[i] += val * 0.1

        # Token-level hash so documents with overlapping keywords correlate positively
        for tok in tokens:
            t_digest = hashlib.sha256(tok.encode("utf-8")).digest()
            t_seed = int.from_bytes(t_digest[:8], "big")
            t_state = t_seed
            for i in range(self._dimension):
                t_state = (t_state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
                val = ((t_state / 0xFFFFFFFFFFFFFFFF) * 2.0) - 1.0
                values[i] += val

        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [self._hash_to_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        cleaned = text.strip() if text else ""
        if not cleaned:
            raise ValidationAppError(
                "Query text cannot be empty or whitespace-only.",
                error_code="EMPTY_QUERY_TEXT",
            )
        return self._hash_to_vector(cleaned)


def get_embedding_adapter(settings: Settings) -> EmbeddingAdapter:
    """Factory creating the appropriate EmbeddingAdapter according to application settings."""
    provider = settings.effective_embedding_provider
    model = settings.effective_embedding_model

    if provider == "fastembed":
        return FastEmbedAdapter(model_name=model)
    if provider == "openai":
        return OpenAIEmbeddingAdapter(
            api_key=settings.embedding_api_key,
            model_name=model,
        )
    if provider in ("mock", "deterministic"):
        dim = KNOWN_DIMENSIONS.get(model.lower(), 768)
        return DeterministicMockEmbeddingAdapter(model_name=model, dimension=dim)

    raise ConfigurationError(
        f"Unsupported embedding provider: '{provider}'. "
        "Supported providers are: 'fastembed', 'openai', 'mock'.",
        error_code="UNSUPPORTED_EMBEDDING_PROVIDER",
    )
