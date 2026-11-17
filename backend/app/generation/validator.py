"""Deterministic 3-stage citation and groundedness validator."""

from __future__ import annotations

import logging
import re
import unicodedata

from app.generation.models import EvidenceBlock, ValidationResult
from app.schemas.query import CitationItem

logger = logging.getLogger(__name__)

# Regular expressions for tags, numbers/units, and clause identifiers
CITATION_TAG_PATTERN = re.compile(r"\[E(\d+)\]")
NUMERIC_UNIT_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:days?|hours?|weeks?|months?|mm|cm|meters?|m|MPa|kN/m2|kN/m²|kN|%|°C|kg|tonnes?)\b",
    re.IGNORECASE,
)
CLAUSE_ID_PATTERN = re.compile(
    r"\b(?:[Cc]lause|[Ss]ection|[Aa]rticle)\s+[A-Za-z0-9.:-]+\b|\bIS\s+\d+(?::\d+)?\b"
)


def _normalize_text_for_comparison(text: str) -> str:
    """Normalize unicode and collapse whitespace for robust string containment."""
    normalized = unicodedata.normalize("NFKC", text)
    # Normalize superscript 2 and units
    normalized = normalized.replace("²", "2").replace("kN/m²", "kN/m2")
    return re.sub(r"\s+", " ", normalized).strip().lower()


class CitationValidator:
    """Validates that all statements in an answer are strictly grounded in retrieved evidence."""

    def __init__(self, strict_number_match: bool = True) -> None:
        self.strict_number_match = strict_number_match

    def validate(
        self,
        draft_answer: str,
        evidence_blocks: list[EvidenceBlock],
    ) -> ValidationResult:
        """Execute 3-stage deterministic citation validation.

        Stage 1: Tag Integrity Check (all [E#] map to actual retrieved evidence).
        Stage 2: Sentence-Level Coverage Check (factual statements carry citations).
        Stage 3: Literal Number, Unit & Clause Verification (numbers appear in cited source text).
        """
        cleaned_answer = draft_answer.strip()
        if not cleaned_answer:
            return ValidationResult(
                is_valid=False,
                verified_answer="",
                abstain_reason="Empty generation output.",
            )

        if cleaned_answer.upper().strip() in ("ABSTAIN", "ABSTAIN.", "I ABSTAIN"):
            return ValidationResult(
                is_valid=False,
                verified_answer=cleaned_answer,
                abstain_reason="Model signaled abstention due to insufficient evidence.",
            )

        evidence_map: dict[str, EvidenceBlock] = {ev.evidence_id: ev for ev in evidence_blocks}
        unverified_claims: list[str] = []

        # ---------------------------------------------------------
        # Stage 1: Tag Integrity Check
        # ---------------------------------------------------------
        found_tags = CITATION_TAG_PATTERN.findall(cleaned_answer)
        found_evidence_ids = [f"E{tag}" for tag in found_tags]

        invalid_tags = [eid for eid in found_evidence_ids if eid not in evidence_map]
        if invalid_tags:
            msg = f"Hallucinated citation tag(s) not in evidence: {', '.join(invalid_tags)}"
            logger.warning(msg)
            unverified_claims.append(msg)

        if not found_evidence_ids:
            unverified_claims.append("Answer contains zero citation tags ([E#]).")

        # ---------------------------------------------------------
        # Stage 2: Sentence-Level Coverage Check
        # ---------------------------------------------------------
        # Split text into sentences, attaching any trailing citation tags [E#]
        raw_tokens = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned_answer) if s.strip()]
        sentences: list[str] = []
        for token in raw_tokens:
            token_without_brackets = re.sub(r"\[E\d+(?:,\s*E\d+)*\]", "", token).strip()
            if not token_without_brackets and sentences:
                sentences[-1] = f"{sentences[-1]} {token}"
            else:
                sentences.append(token)

        for s in sentences:
            # Skip introductory greetings or transitional labels
            if len(s) < 15 and not any(ch.isdigit() for ch in s):
                continue
            sentence_tags = CITATION_TAG_PATTERN.findall(s)
            if not sentence_tags:
                unverified_claims.append(f"Sentence lacks citation: '{s[:60]}...'")

        # ---------------------------------------------------------
        # Stage 3: Literal Number, Unit & Clause Cross-Check
        # ---------------------------------------------------------
        if self.strict_number_match:
            for s in sentences:
                sentence_tags = [f"E{t}" for t in CITATION_TAG_PATTERN.findall(s)]
                valid_sentence_eids = [eid for eid in sentence_tags if eid in evidence_map]
                if not valid_sentence_eids:
                    continue

                # Combine text of attached cited blocks
                cited_source_corpus = " ".join(
                    _normalize_text_for_comparison(evidence_map[eid].text_verbatim)
                    for eid in valid_sentence_eids
                )

                # Check numbers and units
                nums_and_units = NUMERIC_UNIT_PATTERN.findall(s)
                for nu in nums_and_units:
                    norm_nu = _normalize_text_for_comparison(nu)
                    if norm_nu not in cited_source_corpus:
                        unverified_claims.append(
                            f"Numeric claim '{nu}' in sentence not found in cited evidence: "
                            f"{', '.join(valid_sentence_eids)}"
                        )

                # Check clause identifiers (e.g., Clause 4.2.1)
                clause_refs = CLAUSE_ID_PATTERN.findall(s)
                for cr in clause_refs:
                    norm_cr = _normalize_text_for_comparison(cr)
                    if norm_cr not in cited_source_corpus:
                        unverified_claims.append(
                            f"Clause reference '{cr}' not found in cited evidence: "
                            f"{', '.join(valid_sentence_eids)}"
                        )

        # ---------------------------------------------------------
        # Compile Validated Citations
        # ---------------------------------------------------------
        unique_cited_eids = sorted(
            {eid for eid in found_evidence_ids if eid in evidence_map},
            key=lambda x: int(x[1:]) if x[1:].isdigit() else 0,
        )
        citations: list[CitationItem] = [
            evidence_map[eid].to_citation_item() for eid in unique_cited_eids
        ]

        is_valid = len(unverified_claims) == 0 and len(citations) > 0

        return ValidationResult(
            is_valid=is_valid,
            verified_answer=cleaned_answer,
            citations=citations,
            unverified_claims=unverified_claims,
            abstain_reason=(
                None if is_valid else f"Citation validation failed: {'; '.join(unverified_claims)}"
            ),
        )
