"""Unit tests for transparent cross-document conflict detection."""

from __future__ import annotations

from datetime import date

from app.generation.conflict_detector import ConflictDetector
from app.generation.models import EvidenceBlock
from app.schemas.documents import ContentType, DocumentType, ExtractionMethod
from app.schemas.query import ConflictType


def _make_block(
    evidence_id: str,
    doc_id: str,
    doc_title: str,
    doc_type: DocumentType,
    version: str,
    effective_date: date | None,
    text: str,
    standard_code: str | None = None,
) -> EvidenceBlock:
    return EvidenceBlock(
        evidence_id=evidence_id,
        chunk_id=f"chk_{evidence_id}",
        doc_id=doc_id,
        doc_title=doc_title,
        doc_type=doc_type,
        version=version,
        effective_date=effective_date,
        jurisdiction="IN-KA",
        project_id="#104" if doc_type != DocumentType.CODE else None,
        section_id="4.2",
        section_path=["4. Concrete", "4.2 Curing"],
        page_start=1,
        page_end=1,
        content_type=ContentType.PROSE,
        extraction_method=ExtractionMethod.NATIVE,
        retrieval_score=0.9,
        text_verbatim=text,
    )


def test_conflict_detector_version_supersession() -> None:
    detector = ConflictDetector()

    ev_old = _make_block(
        "E1",
        "doc_nbc_2016",
        "National Building Code",
        DocumentType.CODE,
        "2016",
        date(2016, 1, 1),
        "Curing duration is 7 days.",
        standard_code="NBC",
    )
    ev_new = _make_block(
        "E2",
        "doc_nbc_2024",
        "National Building Code",
        DocumentType.CODE,
        "2024",
        date(2024, 1, 1),
        "Curing duration is 10 days.",
        standard_code="NBC",
    )

    conflicts = detector.detect_conflicts([ev_old, ev_new])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.VERSION_SUPERSESSION
    assert "2016" in conflicts[0].summary
    assert "2024" in conflicts[0].summary
    assert "supersedes" in conflicts[0].precedence_note.lower()


def test_conflict_detector_report_vs_code_divergence() -> None:
    detector = ConflictDetector()

    ev_spec = _make_block(
        "E1",
        "doc_spec_concrete",
        "Project Concrete Specification",
        DocumentType.SPEC,
        "v2.0",
        date(2024, 1, 1),
        "Foundation slabs shall be cured for 14 days under all weather conditions.",
    )
    ev_report = _make_block(
        "E2",
        "doc_insp_001",
        "Foundation Inspection Report 001",
        DocumentType.REPORT,
        "v1.0",
        date(2023, 11, 10),
        "Contractor cured foundation slab for 7 days; forms stripped on Day 8.",
    )

    conflicts = detector.detect_conflicts([ev_spec, ev_report])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.REPORT_VS_CODE_DIVERGENCE
    assert "historical" in conflicts[0].summary.lower()
    assert "ECO" in conflicts[0].precedence_note or "Change Order" in conflicts[0].precedence_note


def test_conflict_detector_cross_document_numeric_mismatch() -> None:
    detector = ConflictDetector()

    ev_spec_a = _make_block(
        "E1",
        "doc_subcontractor_spec",
        "Subcontractor Masonry Spec",
        DocumentType.SPEC,
        "v1.0",
        date(2024, 1, 1),
        "Mortar joints shall be cured for 7 days.",
    )
    ev_spec_b = _make_block(
        "E2",
        "doc_client_architect_spec",
        "Architectural General Spec",
        DocumentType.SPEC,
        "v1.0",
        date(2024, 1, 1),
        "All exposed mortar joints shall be water-cured for 14 days.",
    )

    conflicts = detector.detect_conflicts([ev_spec_a, ev_spec_b])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.CROSS_DOCUMENT_VALUE_MISMATCH
    assert "7" in conflicts[0].summary
    assert "14" in conflicts[0].summary


def test_conflict_detector_no_conflicts_on_single_or_consistent_blocks() -> None:
    detector = ConflictDetector()

    ev1 = _make_block(
        "E1", "doc_1", "Safety Code", DocumentType.CODE, "2024", date(2024, 1, 1), "Wear helmets."
    )
    assert detector.detect_conflicts([ev1]) == []

    ev2 = _make_block(
        "E2", "doc_1", "Safety Code", DocumentType.CODE, "2024", date(2024, 1, 1), "Wear boots."
    )
    # Same document ID -> no cross-document conflict
    assert detector.detect_conflicts([ev1, ev2]) == []
