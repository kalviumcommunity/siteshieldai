"""LLM generation adapter protocol, OpenAI client, and deterministic mock implementation."""

from __future__ import annotations

import logging
import re
from typing import Protocol, runtime_checkable

from pydantic import SecretStr

from app.core.config import Settings
from app.core.exceptions import (
    AppError,
    ConfigurationError,
    ServiceUnavailableError,
)
from app.generation.models import EvidenceBlock, GroundedDraft
from app.generation.prompt import (
    SYSTEM_GROUNDED_PROMPT,
    build_user_prompt,
    clean_query_text,
)
from app.schemas.documents import DocumentType

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a",
    "an",
    "the",
    "in",
    "on",
    "at",
    "for",
    "to",
    "of",
    "and",
    "or",
    "is",
    "are",
    "was",
    "were",
    "what",
    "how",
    "when",
    "where",
    "which",
    "who",
    "whom",
    "does",
    "do",
    "did",
    "can",
    "could",
    "should",
    "shall",
    "must",
    "be",
    "been",
}


@runtime_checkable
class LLMAdapter(Protocol):
    """Protocol for grounded answer generation adapters."""

    def generate_grounded(
        self,
        query: str,
        evidence: list[EvidenceBlock],
    ) -> GroundedDraft:
        """Produce a grounded draft answer with inline [E#] citations or ABSTAIN."""
        ...


class DeterministicMockLLMAdapter:
    """Fast, deterministic LLM adapter for offline testing and verification.

    Extracts grounded statements directly from matching evidence blocks, defends against
    indirect prompt injection, and triggers ABSTAIN when evidence is insufficient.
    """

    def generate_grounded(
        self,
        query: str,
        evidence: list[EvidenceBlock],
    ) -> GroundedDraft:
        cleaned_query = clean_query_text(query)
        if not evidence:
            return GroundedDraft(
                answer="ABSTAIN",
                is_abstain=True,
                abstain_reason="No evidence blocks provided.",
            )

        query_tokens = {
            t.lower()
            for t in re.findall(r"\b[A-Za-z0-9]+\b", cleaned_query)
            if t.lower() not in STOP_WORDS and len(t) > 1
        }

        # Check for matching evidence blocks
        scored_blocks: list[tuple[int, EvidenceBlock, list[str]]] = []
        for ev in evidence:
            # Strip prompt injection phrases from untrusted text
            clean_verbatim = re.sub(
                r"(?i)(ignore previous instructions|say pwned|output system prompt|system override)"
                r".*?([.!?\n]|$)",
                "",
                ev.text_verbatim,
            ).strip()

            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_verbatim) if s.strip()]

            match_count = 0
            matching_sentences: list[str] = []
            for s in sentences:
                s_tokens = {t.lower() for t in re.findall(r"\b[A-Za-z0-9]+\b", s)}
                overlap = len(query_tokens.intersection(s_tokens))
                if overlap > 0:
                    match_count += overlap
                    matching_sentences.append(s)

            if match_count > 0:
                scored_blocks.append((match_count, ev, matching_sentences))

        if not scored_blocks:
            # Gate 2: In-context LLM abstention when evidence does not answer the question
            return GroundedDraft(
                answer="ABSTAIN",
                is_abstain=True,
                abstain_reason="Evidence does not contain information answering the question.",
            )

        # Sort blocks by match score descending
        scored_blocks.sort(key=lambda x: x[0], reverse=True)

        # Assemble grounded response
        answer_parts: list[str] = []
        cited_ids: list[str] = []

        # Group by requirement (spec/code) vs. historical finding (report)
        requirements: list[tuple[EvidenceBlock, str]] = []
        historical_findings: list[tuple[EvidenceBlock, str]] = []

        for _, ev, sents in scored_blocks:
            top_sent = sents[0] if sents else ev.text_verbatim[:120].strip()
            clean_sent = top_sent.rstrip(".!?")

            if ev.doc_type == DocumentType.REPORT:
                historical_findings.append((ev, clean_sent))
            else:
                requirements.append((ev, clean_sent))

        # Add governing requirements first
        for ev, sent in requirements:
            answer_parts.append(f"{sent} [{ev.evidence_id}].")
            cited_ids.append(ev.evidence_id)

        # Differentiate historical findings
        for ev, sent in historical_findings:
            answer_parts.append(
                f"Historical inspection report '{ev.doc_title}' ({ev.version}) "
                f"noted: {sent} [{ev.evidence_id}]."
            )
            cited_ids.append(ev.evidence_id)

        final_answer = " ".join(answer_parts)
        return GroundedDraft(
            answer=final_answer,
            is_abstain=False,
            cited_evidence_ids=list(dict.fromkeys(cited_ids)),
        )


class OpenAILLMAdapter:
    """Production cloud adapter for OpenAI-compatible LLMs."""

    def __init__(
        self,
        api_key: str | SecretStr | None,
        model_name: str = "gpt-4o-mini",
        api_base: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self.model_name = model_name
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

        if isinstance(api_key, SecretStr):
            raw_key = api_key.get_secret_value()
        else:
            raw_key = str(api_key or "")

        if not raw_key.strip():
            raise ConfigurationError(
                "LLM_API_KEY environment variable is required when using the OpenAI LLM provider.",
                error_code="MISSING_LLM_API_KEY",
            )
        self.api_key = raw_key.strip()

    def generate_grounded(
        self,
        query: str,
        evidence: list[EvidenceBlock],
    ) -> GroundedDraft:
        import httpx

        user_content = build_user_prompt(query, evidence)
        payload = {
            "model": self.model_name,
            "temperature": 0.0,
            "max_tokens": 700,
            "messages": [
                {"role": "system", "content": SYSTEM_GROUNDED_PROMPT},
                {"role": "user", "content": user_content},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                )
        except Exception as exc:
            logger.error("LLM generation network failure: %s", exc)
            raise ServiceUnavailableError(
                f"LLM generation service unreachable: {exc}",
                error_code="LLM_SERVICE_UNAVAILABLE",
            ) from exc

        if resp.status_code == 401 or resp.status_code == 403:
            raise AppError(
                "OpenAI authentication failed: invalid API key.",
                status_code=401,
                error_code="LLM_AUTH_ERROR",
            )
        if resp.status_code == 429:
            raise ServiceUnavailableError(
                "OpenAI rate limit exceeded.",
                status_code=429,
                error_code="LLM_RATE_LIMITED",
            )
        if resp.status_code >= 400:
            raise ServiceUnavailableError(
                f"OpenAI chat completion returned HTTP {resp.status_code}: {resp.text}",
                status_code=503,
                error_code="LLM_API_ERROR",
            )

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "").strip()

        if not content or content.upper() in ("ABSTAIN", "ABSTAIN.", "I ABSTAIN"):
            return GroundedDraft(
                answer="ABSTAIN",
                is_abstain=True,
                abstain_reason="Model signaled abstention due to lack of evidence.",
                raw_response=content,
            )

        cited_tags = [f"E{t}" for t in re.findall(r"\[E(\d+)\]", content)]
        return GroundedDraft(
            answer=content,
            is_abstain=False,
            cited_evidence_ids=list(dict.fromkeys(cited_tags)),
            raw_response=content,
        )


def get_llm_adapter(settings: Settings) -> LLMAdapter:
    """Factory creating the appropriate LLMAdapter according to application settings."""
    provider = settings.effective_llm_provider
    model = settings.effective_llm_model

    if provider == "openai":
        return OpenAILLMAdapter(
            api_key=settings.llm_api_key,
            model_name=model,
        )
    if provider in ("mock", "deterministic"):
        return DeterministicMockLLMAdapter()

    raise ConfigurationError(
        f"Unsupported LLM provider: '{provider}'. Supported providers are: 'openai', 'mock'.",
        error_code="UNSUPPORTED_LLM_PROVIDER",
    )
