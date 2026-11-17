"""Transparent cross-document conflict detection and historical divergence flagging."""

from __future__ import annotations

import logging
import re

from app.generation.models import EvidenceBlock
from app.schemas.documents import DocumentType
from app.schemas.query import ConflictItem, ConflictSourceRef, ConflictType

logger = logging.getLogger(__name__)

NUMERIC_EXTRACT_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(days?|hours?|weeks?|months?|mm|cm|meters?|m|MPa|kN/m2|kN/m²|kN)\b",
    re.IGNORECASE,
)


def _to_source_ref(ev: EvidenceBlock, excerpt: str | None = None) -> ConflictSourceRef:
    return ConflictSourceRef(
        doc_id=ev.doc_id,
        doc_title=ev.doc_title,
        version=ev.version,
        effective_date=ev.effective_date,
        section_id=ev.section_id,
        page_start=ev.page_start,
        excerpt=(excerpt or ev.text_verbatim)[:200],
    )


class ConflictDetector:
    """Detects version supersession, report-vs-code divergence, and numeric value conflicts."""

    def detect_conflicts(
        self,
        evidence_blocks: list[EvidenceBlock],
    ) -> list[ConflictItem]:
        """Inspect evidence blocks and surface transparent cross-document contradictions."""
        if len(evidence_blocks) < 2:
            return []

        conflicts: list[ConflictItem] = []
        seen_pairs: set[tuple[str, str]] = set()

        for i in range(len(evidence_blocks)):
            for j in range(i + 1, len(evidence_blocks)):
                ev_a = evidence_blocks[i]
                ev_b = evidence_blocks[j]

                if ev_a.doc_id == ev_b.doc_id:
                    continue

                pair_key = tuple(sorted([ev_a.doc_id, ev_b.doc_id]))
                if pair_key in seen_pairs:
                    continue

                # -----------------------------------------------------
                # Check 1: Version Supersession (Same standard / code, different versions)
                # -----------------------------------------------------
                if (
                    ev_a.standard_code
                    and ev_b.standard_code
                    and ev_a.standard_code.strip().lower() == ev_b.standard_code.strip().lower()
                    and ev_a.version != ev_b.version
                ) or (
                    ev_a.doc_title.strip().lower() == ev_b.doc_title.strip().lower()
                    and ev_a.version != ev_b.version
                ):
                    doc_name = ev_a.standard_code or ev_a.doc_title
                    date_a = str(ev_a.effective_date or "unknown")
                    date_b = str(ev_b.effective_date or "unknown")
                    newer_ver = (
                        ev_b.version
                        if (
                            ev_b.effective_date
                            and ev_a.effective_date
                            and ev_b.effective_date > ev_a.effective_date
                        )
                        else ev_a.version
                    )
                    seen_pairs.add(pair_key)
                    conflicts.append(
                        ConflictItem(
                            conflict_type=ConflictType.VERSION_SUPERSESSION,
                            source_a=_to_source_ref(ev_a),
                            source_b=_to_source_ref(ev_b),
                            summary=(
                                f"Multiple revisions found for '{doc_name}': "
                                f"{ev_a.version} (effective {date_a}) vs "
                                f"{ev_b.version} (effective {date_b})."
                            ),
                            precedence_note=(
                                f"Newer revision ({newer_ver}) typically supersedes earlier "
                                "revisions — verify applicable contract standard."
                            ),
                        )
                    )
                    continue

                # -----------------------------------------------------
                # Check 2: Report vs. Code Divergence
                # (Historical field inspection finding vs. binding code requirement)
                # -----------------------------------------------------
                has_report = (
                    ev_a.doc_type == DocumentType.REPORT or ev_b.doc_type == DocumentType.REPORT
                )
                has_code_or_spec = ev_a.doc_type in (
                    DocumentType.CODE,
                    DocumentType.SPEC,
                ) or ev_b.doc_type in (DocumentType.CODE, DocumentType.SPEC)

                if has_report and has_code_or_spec:
                    report_ev = ev_a if ev_a.doc_type == DocumentType.REPORT else ev_b
                    spec_ev = ev_b if ev_a.doc_type == DocumentType.REPORT else ev_a

                    seen_pairs.add(pair_key)
                    conflicts.append(
                        ConflictItem(
                            conflict_type=ConflictType.REPORT_VS_CODE_DIVERGENCE,
                            source_a=_to_source_ref(spec_ev),
                            source_b=_to_source_ref(report_ev),
                            summary=(
                                f"Historical field inspection report '{report_ev.doc_title}' "
                                f"({report_ev.version}) differs from governing technical "
                                f"document '{spec_ev.doc_title}' ({spec_ev.version})."
                            ),
                            precedence_note=(
                                "Past site inspection reports record as-built conditions at a "
                                "specific date and do NOT alter governing building code or "
                                "specification requirements without an approved ECO."
                            ),
                        )
                    )
                    continue

                # -----------------------------------------------------
                # Check 3: Cross-Document Numeric Value Mismatch
                # -----------------------------------------------------
                nums_a = NUMERIC_EXTRACT_PATTERN.findall(ev_a.text_verbatim)
                nums_b = NUMERIC_EXTRACT_PATTERN.findall(ev_b.text_verbatim)

                # Look for matching units with differing numbers
                units_map_a: dict[str, set[str]] = {}
                for val, unit in nums_a:
                    units_map_a.setdefault(unit.lower(), set()).add(val)

                mismatch_found = False
                for val_b, unit_b in nums_b:
                    unit_key = unit_b.lower()
                    if unit_key in units_map_a:
                        vals_a = units_map_a[unit_key]
                        if val_b not in vals_a:
                            seen_pairs.add(pair_key)
                            conflicts.append(
                                ConflictItem(
                                    conflict_type=ConflictType.CROSS_DOCUMENT_VALUE_MISMATCH,
                                    source_a=_to_source_ref(ev_a),
                                    source_b=_to_source_ref(ev_b),
                                    summary=(
                                        f"Conflicting thresholds for {unit_b}: "
                                        f"'{ev_a.doc_title}' ({', '.join(vals_a)} {unit_b}) vs "
                                        f"'{ev_b.doc_title}' ({val_b} {unit_b})."
                                    ),
                                    precedence_note=(
                                        "Cross-document value contradiction detected. Governing "
                                        "project specification takes precedence."
                                    ),
                                )
                            )
                            mismatch_found = True
                            break
                if mismatch_found:
                    continue

        return conflicts
