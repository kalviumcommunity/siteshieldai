"""Retrieval, embedding, and vector database package."""

from __future__ import annotations

from app.retrieval.embeddings import (
    DeterministicMockEmbeddingAdapter,
    EmbeddingAdapter,
    FastEmbedAdapter,
    OpenAIEmbeddingAdapter,
    get_embedding_adapter,
)
from app.retrieval.indexer import VectorIndexer
from app.retrieval.vector_store import (
    QdrantVectorStore,
    ScoredChunk,
    VectorStorePort,
    get_vector_store,
)

__all__ = [
    "DeterministicMockEmbeddingAdapter",
    "EmbeddingAdapter",
    "FastEmbedAdapter",
    "OpenAIEmbeddingAdapter",
    "QdrantVectorStore",
    "ScoredChunk",
    "VectorIndexer",
    "VectorStorePort",
    "get_embedding_adapter",
    "get_vector_store",
]
