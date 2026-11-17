"""Grounded generation, citation validation, conflict detection, and query service."""

from __future__ import annotations

from app.generation.conflict_detector import ConflictDetector
from app.generation.llm_adapter import (
    DeterministicMockLLMAdapter,
    LLMAdapter,
    OpenAILLMAdapter,
    get_llm_adapter,
)
from app.generation.models import EvidenceBlock, GroundedDraft, ValidationResult
from app.generation.service import QueryService
from app.generation.validator import CitationValidator

__all__ = [
    "CitationValidator",
    "ConflictDetector",
    "DeterministicMockLLMAdapter",
    "EvidenceBlock",
    "GroundedDraft",
    "LLMAdapter",
    "OpenAILLMAdapter",
    "QueryService",
    "ValidationResult",
    "get_llm_adapter",
]
