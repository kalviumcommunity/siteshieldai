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
        query_text: str | None = None,
    ) -> list[ConflictItem]:
        """Inspect evidence blocks and surface transparent cross-document contradictions."""
        if len(evidence_blocks) < 2:
            return []

        conflicts: list[ConflictItem] = []
        seen_pairs: set[tuple[str, str]] = set()

        q_tokens = (
            {t.lower() for t in re.findall(r"\b[A-Za-z0-9]+\b", query_text) if len(t) > 2}
            if query_text
            else set()
        )

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
                # (Historical field inspection finding vs. binding code requirement
                # discussing the same technical subject)
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

                    sents_spec = [
                        s.strip()
                        for s in re.split(r"(?<=[.!?])\s+", spec_ev.text_verbatim)
                        if s.strip()
                    ]
                    sents_report = [
                        s.strip()
                        for s in re.split(r"(?<=[.!?])\s+", report_ev.text_verbatim)
                        if s.strip()
                    ]

                    GENERIC_WORDS = {
                        "foundation",
                        "foundations",
                        "concrete",
                        "project",
                        "specification",
                        "report",
                        "inspection",
                        "document",
                        "technical",
                        "standard",
                        "shall",
                        "under",
                        "grade",
                        "using",
                        "site",
                        "formwork",
                        "contractor",
                        "subcontractor",
                        "requirements",
                        "structural",
                        "elements",
                    }

                    divergence_found = False
                    for sa in sents_spec:
                        toks_sa = {
                            t.lower()
                            for t in re.findall(r"\b[A-Za-z0-9]+\b", sa)
                            if len(t) > 3 and t.lower() not in GENERIC_WORDS
                        }
                        nums_sa = NUMERIC_EXTRACT_PATTERN.findall(sa)
                        map_sa = {unit.lower(): val for val, unit in nums_sa}

                        for sb in sents_report:
                            toks_sb = {
                                t.lower()
                                for t in re.findall(r"\b[A-Za-z0-9]+\b", sb)
                                if len(t) > 3 and t.lower() not in GENERIC_WORDS
                            }
                            shared_topic = toks_sa.intersection(toks_sb)
                            if not shared_topic:
                                continue

                            # Query relevance: if query provided, shared topic must match query
                            if q_tokens and not any(
                                qt in shared_topic
                                or any(st.startswith(qt[:4]) for st in shared_topic)
                                for qt in q_tokens
                            ):
                                continue

                            ncr_pat = (
                                r"\b(ncr|non-conformance|non-compliant|failing to comply|"
                                r"failed|deviation|defect|violation|deficiency)\b"
                            )
                            is_ncr = bool(re.search(ncr_pat, sb, re.I))

                            nums_sb = NUMERIC_EXTRACT_PATTERN.findall(sb)
                            has_num_mismatch = False
                            for val_b, unit_b in nums_sb:
                                uk = unit_b.lower()
                                if uk in map_sa and map_sa[uk] != val_b:
                                    has_num_mismatch = True
                                    break

                            if is_ncr or has_num_mismatch:
                                seen_pairs.add(pair_key)
                                topic_str = ", ".join(sorted(list(shared_topic))[:3])
                                conflicts.append(
                                    ConflictItem(
                                        conflict_type=ConflictType.REPORT_VS_CODE_DIVERGENCE,
                                        source_a=_to_source_ref(spec_ev, sa),
                                        source_b=_to_source_ref(report_ev, sb),
                                        summary=(
                                            f"Historical field inspection report "
                                            f"'{report_ev.doc_title}' ({report_ev.version}) "
                                            f"differs from governing technical document "
                                            f"'{spec_ev.doc_title}' ({spec_ev.version}) "
                                            f"regarding {topic_str}."
                                        ),
                                        precedence_note=(
                                            "Past site inspection reports record as-built "
                                            "conditions at a specific date and do NOT alter "
                                            "governing building code requirements without an "
                                            "approved ECO."
                                        ),
                                    )
                                )
                                divergence_found = True
                                break
                        if divergence_found:
                            break

                    if divergence_found:
                        continue

                # -----------------------------------------------------
                # Check 3: Cross-Document Numeric Value Mismatch
                # (Same parameter/subject with conflicting numeric values)
                # -----------------------------------------------------
                sents_a = [
                    s.strip() for s in re.split(r"(?<=[.!?])\s+", ev_a.text_verbatim) if s.strip()
                ]
                sents_b = [
                    s.strip() for s in re.split(r"(?<=[.!?])\s+", ev_b.text_verbatim) if s.strip()
                ]

                mismatch_found = False
                for sa in sents_a:
                    nums_a = NUMERIC_EXTRACT_PATTERN.findall(sa)
                    if not nums_a:
                        continue
                    toks_sa = {t.lower() for t in re.findall(r"\b[A-Za-z0-9]+\b", sa) if len(t) > 3}

                    for sb in sents_b:
                        nums_b = NUMERIC_EXTRACT_PATTERN.findall(sb)
                        if not nums_b:
                            continue
                        toks_sb = {
                            t.lower() for t in re.findall(r"\b[A-Za-z0-9]+\b", sb) if len(t) > 3
                        }
                        shared_param = toks_sa.intersection(toks_sb)
                        # Must share at least 2 parameter context terms (e.g. "curing", "slabs")
                        # and that parameter must be relevant to the query (if provided)
                        if len(shared_param) < 2:
                            continue

                        NON_PARAM_WORDS = {
                            "foundation",
                            "foundations",
                            "concrete",
                            "structural",
                            "project",
                            "element",
                            "elements",
                            "standard",
                            "specification",
                        }
                        specific_param = {t for t in shared_param if t not in NON_PARAM_WORDS}
                        if q_tokens and not any(
                            qt in specific_param
                            or any(sp.startswith(qt[:4]) for sp in specific_param)
                            for qt in q_tokens
                        ):
                            continue

                        # Structural engineering sanity check:
                        # Do not compare two different structural components (e.g. beam vs footing)
                        structural_elements = {
                            "beam",
                            "beams",
                            "column",
                            "columns",
                            "slab",
                            "slabs",
                            "footing",
                            "footings",
                            "foundation",
                            "foundations",
                            "wall",
                            "walls",
                            "trench",
                            "trenches",
                            "girder",
                            "girders",
                            "ladder",
                            "ladders",
                        }
                        doc_elems_a = {
                            t.lower()
                            for t in re.findall(
                                r"\b[A-Za-z0-9]+\b",
                                f"{ev_a.doc_title} {' '.join(ev_a.section_path)}",
                            )
                        }.intersection(structural_elements)
                        doc_elems_b = {
                            t.lower()
                            for t in re.findall(
                                r"\b[A-Za-z0-9]+\b",
                                f"{ev_b.doc_title} {' '.join(ev_b.section_path)}",
                            )
                        }.intersection(structural_elements)
                        effective_elems_a = toks_sa.intersection(structural_elements) or doc_elems_a
                        effective_elems_b = toks_sb.intersection(structural_elements) or doc_elems_b
                        if (
                            effective_elems_a
                            and effective_elems_b
                            and not effective_elems_a.intersection(effective_elems_b)
                        ):
                            continue

                        # Check for matching unit with conflicting values
                        map_a = {unit.lower(): val for val, unit in nums_a}
                        for val_b, unit_b in nums_b:
                            uk = unit_b.lower()
                            if uk in map_a and map_a[uk] != val_b:
                                seen_pairs.add(pair_key)
                                param_str = ", ".join(sorted(list(shared_param))[:2])
                                conflicts.append(
                                    ConflictItem(
                                        conflict_type=ConflictType.CROSS_DOCUMENT_VALUE_MISMATCH,
                                        source_a=_to_source_ref(ev_a, sa),
                                        source_b=_to_source_ref(ev_b, sb),
                                        summary=(
                                            f"Conflicting thresholds for {unit_b}: "
                                            f"'{ev_a.doc_title}' ({map_a[uk]} {unit_b}) vs "
                                            f"'{ev_b.doc_title}' ({val_b} {unit_b}) "
                                            f"regarding {param_str}."
                                        ),
                                        precedence_note=(
                                            "Cross-document value contradiction detected. "
                                            "Governing project specification takes precedence."
                                        ),
                                    )
                                )
                                mismatch_found = True
                                break
                        if mismatch_found:
                            break
                    if mismatch_found:
                        break

        return conflicts
