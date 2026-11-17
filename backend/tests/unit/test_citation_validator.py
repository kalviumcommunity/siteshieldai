"""Unit tests for deterministic 3-stage citation and groundedness validator."""

from __future__ import annotations

from datetime import date

from app.generation.models import EvidenceBlock
from app.generation.validator import CitationValidator
from app.schemas.documents import ContentType, DocumentType, ExtractionMethod


def _make_evidence(
    evidence_id: str,
    text: str,
    doc_id: str = "doc_1",
    doc_title: str = "IS 456 Concrete Code",
) -> EvidenceBlock:
    return EvidenceBlock(
        evidence_id=evidence_id,
        chunk_id=f"chk_{evidence_id}",
        doc_id=doc_id,
        doc_title=doc_title,
        doc_type=DocumentType.CODE,
        version="2000",
        effective_date=date(2000, 1, 1),
        jurisdiction="IN-KA",
        project_id=None,
        section_id="4.2.1",
        section_path=["4. Concrete", "4.2 Curing"],
        page_start=12,
        page_end=12,
        content_type=ContentType.PROSE,
        extraction_method=ExtractionMethod.NATIVE,
        retrieval_score=0.92,
        text_verbatim=text,
    )


def test_validator_passes_valid_grounded_answer() -> None:
    ev1 = _make_evidence(
        "E1", "Concrete curing duration shall be a minimum of 7 days under normal weather."
    )
    validator = CitationValidator(strict_number_match=True)

    answer = "The minimum curing duration is 7 days under normal weather [E1]."
    result = validator.validate(answer, [ev1])

    assert result.is_valid
    assert len(result.citations) == 1
    assert result.citations[0].evidence_id == "E1"
    assert result.citations[0].chunk_id == "chk_E1"
    assert len(result.unverified_claims) == 0


def test_validator_fails_hallucinated_citation_tag() -> None:
    ev1 = _make_evidence("E1", "Scaffolding guard rails must be at least 1.0 m high.")
    validator = CitationValidator()

    # Model hallucinates tag [E9] which was never retrieved
    answer = "Guard rails must be 1.0 m high [E1]. Top rail strength is 100 kg [E9]."
    result = validator.validate(answer, [ev1])

    assert not result.is_valid
    assert any("E9" in claim for claim in result.unverified_claims)
    assert result.abstain_reason is not None


def test_validator_fails_sentence_missing_citation() -> None:
    ev1 = _make_evidence("E1", "Trenches deeper than 1.5 m require shoring.")
    validator = CitationValidator()

    # Second sentence is an uncited factual statement
    answer = "Trenches deeper than 1.5 m require shoring [E1]. Excavation must be inspected daily."
    result = validator.validate(answer, [ev1])

    assert not result.is_valid
    assert any("Sentence lacks citation" in claim for claim in result.unverified_claims)


def test_validator_detects_numeric_value_mismatch() -> None:
    ev1 = _make_evidence("E1", "Moist curing shall continue for not less than 7 days.")
    validator = CitationValidator(strict_number_match=True)

    # Cited evidence says 7 days, but answer hallucinates 14 days!
    answer = "Moist curing shall continue for not less than 14 days [E1]."
    result = validator.validate(answer, [ev1])

    assert not result.is_valid
    assert any("Numeric claim '14 days'" in claim for claim in result.unverified_claims)


def test_validator_handles_abstain_signal() -> None:
    ev1 = _make_evidence("E1", "General building guidelines.")
    validator = CitationValidator()

    result = validator.validate("ABSTAIN", [ev1])
    assert not result.is_valid
    assert "abstention" in (result.abstain_reason or "").lower()


def test_validator_handles_empty_output() -> None:
    validator = CitationValidator()
    result = validator.validate("", [])
    assert not result.is_valid
    assert result.abstain_reason == "Empty generation output."
