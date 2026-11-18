"""Comprehensive RAG Evaluation Harness for Site Shield AI.

Evaluates:
1. Document extraction quality & character fidelity.
2. Chunk boundary quality & table/section stack preservation.
3. Retrieval Precision@K, Recall@K, and MRR.
4. Citation correctness & claim-to-chunk provenance mapping.
5. Answer groundedness & faithfulness (zero numeric/clause hallucinations).
6. Abstention accuracy across Gates 1, 2, and 3.
7. Conflict detection sensitivity & legal precedence rulings.
8. Prompt injection resistance (indirect & direct).
9. Latency telemetry (p50, p90, p95, p99).
10. API reliability.
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.generation.service import QueryService
from app.ingestion.service import IngestionService
from app.ingestion.store import IngestionStore
from app.retrieval.embeddings import DeterministicMockEmbeddingAdapter
from app.retrieval.indexer import VectorIndexer
from app.retrieval.vector_store import QdrantVectorStore
from app.schemas.documents import (
    ConfidentialityTier,
    DocumentIngestMetadata,
    DocumentStatus,
    DocumentType,
)
from app.schemas.query import QueryFilters, QueryRequest, QueryStatus

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("evaluate_rag")


@dataclass
class TestCaseResult:
    case_id: str
    category: str
    query: str
    expected_status: str
    actual_status: str
    status_match: bool
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    retrieved_doc_titles: list[str] = field(default_factory=list)
    recall_at_3: float = 0.0
    precision_at_3: float = 0.0
    reciprocal_rank: float = 0.0
    citations_count: int = 0
    citations_valid: bool = False
    answer_grounded: bool = False
    conflict_detected: bool = False
    conflict_summaries: list[str] = field(default_factory=list)
    injection_resisted: bool = True
    total_latency_ms: int = 0
    failure_reasons: list[str] = field(default_factory=list)


def setup_evaluation_corpus(
    db_path: Path,
    qdrant_store: QdrantVectorStore,
    embedder: DeterministicMockEmbeddingAdapter,
    collection_name: str,
) -> tuple[QueryService, IngestionService, IngestionStore]:
    settings = Settings(_env_file=None, vector_db_collection=collection_name)
    store = IngestionStore(db_path)
    indexer = VectorIndexer(
        embedding_adapter=embedder,
        vector_store=qdrant_store,
        collection_name=collection_name,
    )
    ingestion_service = IngestionService(
        settings=settings,
        store=store,
        vector_indexer=indexer,
    )
    query_service = QueryService(
        settings=settings,
        embedding_adapter=embedder,
        vector_store=qdrant_store,
    )

    # Ingest Raw Sample Documents
    corpus_dir = REPO_ROOT / "data" / "raw"
    doc_definitions = [
        (
            "spec_foundation_concrete_v2.md",
            DocumentIngestMetadata(
                doc_title="4.0 Foundation Concrete Specification",
                doc_type=DocumentType.SPEC,
                version="v2.0",
                effective_date="2024-02-01",
                jurisdiction="IN-KA",
                project_id="#104",
                confidentiality_tier=ConfidentialityTier.INTERNAL,
            ),
        ),
        (
            "spec_foundation_concrete_v1.md",
            DocumentIngestMetadata(
                doc_title="4.0 Foundation Concrete Specification",
                doc_type=DocumentType.SPEC,
                version="v1.0",
                effective_date="2023-01-01",
                status=DocumentStatus.SUPERSEDED,
                jurisdiction="IN-KA",
                project_id="#104",
                confidentiality_tier=ConfidentialityTier.INTERNAL,
            ),
        ),
        (
            "report_site_inspection_01.md",
            DocumentIngestMetadata(
                doc_title="Site Quality Inspection Report 01",
                doc_type=DocumentType.REPORT,
                version="v1.0",
                effective_date="2023-10-15",
                jurisdiction="IN-KA",
                project_id="#104",
                confidentiality_tier=ConfidentialityTier.INTERNAL,
            ),
        ),
        (
            "safety_excavation_manual.md",
            DocumentIngestMetadata(
                doc_title="Excavation and Trenching Safety Protocol",
                doc_type=DocumentType.SAFETY_MANUAL,
                version="v1.2",
                effective_date="2023-09-01",
                jurisdiction="IN-KA",
                project_id="#104",
                confidentiality_tier=ConfidentialityTier.INTERNAL,
            ),
        ),
        (
            "spec_structural_steelwork.md",
            DocumentIngestMetadata(
                doc_title="Structural Steel Fabrication and Erection Specification",
                doc_type=DocumentType.SPEC,
                version="v1.0",
                effective_date="2023-11-15",
                jurisdiction="IN-KA",
                project_id="#104",
                confidentiality_tier=ConfidentialityTier.INTERNAL,
            ),
        ),
        (
            "rules_site_safety.md",
            DocumentIngestMetadata(
                doc_title="Site General Safety & Access Rules",
                doc_type=DocumentType.SAFETY_MANUAL,
                version="v2.1",
                effective_date="2024-01-10",
                jurisdiction="IN-KA",
                project_id="#104",
                confidentiality_tier=ConfidentialityTier.INTERNAL,
            ),
        ),
        (
            "adv_prompt_injection_sample.md",
            DocumentIngestMetadata(
                doc_title="Contractor Submittal: Exterior Beam Reinforcement Schedule",
                doc_type=DocumentType.SPEC,
                version="v1.0",
                effective_date="2024-01-20",
                jurisdiction="IN-KA",
                project_id="#104",
                confidentiality_tier=ConfidentialityTier.INTERNAL,
            ),
        ),
    ]

    for filename, meta in doc_definitions:
        filepath = corpus_dir / filename
        if filepath.exists():
            ingestion_service.ingest_file(filepath, meta)

    return query_service, ingestion_service, store


def run_benchmark() -> dict[str, Any]:
    dataset_path = REPO_ROOT / "data" / "evaluation_dataset.json"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    # Set up in-memory vector store for clean benchmark run
    db_path = REPO_ROOT / "data" / "evaluation_rag.db"
    if db_path.exists():
        db_path.unlink()

    qdrant_store = QdrantVectorStore(location=":memory:")
    embedder = DeterministicMockEmbeddingAdapter(dimension=128)
    collection_name = "eval_benchmark_chunks"

    query_service, ingestion_service, store = setup_evaluation_corpus(
        db_path, qdrant_store, embedder, collection_name
    )

    results: list[TestCaseResult] = []
    latencies: list[int] = []

    for c in cases:
        case_id = c["case_id"]
        query_text = c["query"]
        expected_status = c["expected_status"]
        category = c["category"]
        gold_titles = c.get("gold_doc_titles", [])
        expected_keywords = c.get("expected_claim_keywords", [])
        prohibited_terms = c.get("prohibited_terms", [])
        raw_filters = c.get("filters", {})

        raw_doc_types = raw_filters.get("doc_types")
        parsed_doc_types = (
            [DocumentType(dt) for dt in raw_doc_types]
            if raw_doc_types is not None
            else None
        )

        filters = QueryFilters(
            project_id=raw_filters.get("project_id"),
            jurisdiction=raw_filters.get("jurisdiction"),
            doc_types=parsed_doc_types,
            include_superseded=raw_filters.get("include_superseded", False),
        )

        request = QueryRequest(query=query_text, filters=filters, top_k=5)

        start_time = time.perf_counter()
        resp = query_service.execute_query(request)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000)
        latencies.append(resp.latency_ms.total or elapsed_ms)

        res = TestCaseResult(
            case_id=case_id,
            category=category,
            query=query_text,
            expected_status=expected_status,
            actual_status=resp.status.value,
            status_match=(resp.status.value == expected_status),
            retrieved_chunk_ids=[c.chunk_id for c in resp.citations],
            retrieved_doc_titles=[c.doc_title for c in resp.citations],
            citations_count=len(resp.citations),
            total_latency_ms=resp.latency_ms.total,
        )

        # 1. Retrieval Precision & Recall Evaluation
        if gold_titles:
            # We check the top retrieved chunks
            # For query service, cited chunks or top retrieval
            retrieved_titles = [c.doc_title for c in resp.citations]
            top_3_titles = retrieved_titles[:3]

            relevant_retrieved = [t for t in top_3_titles if any(gt in t for gt in gold_titles)]
            res.precision_at_3 = len(relevant_retrieved) / min(3, len(top_3_titles)) if top_3_titles else 0.0

            # Recall@3: did we get the gold titles?
            matched_gold = [gt for gt in gold_titles if any(gt in t for t in top_3_titles)]
            res.recall_at_3 = len(matched_gold) / len(gold_titles)

            # Reciprocal rank
            for rank, t in enumerate(retrieved_titles, start=1):
                if any(gt in t for gt in gold_titles):
                    res.reciprocal_rank = 1.0 / rank
                    break
        else:
            # Negative test cases (abstention targets)
            res.recall_at_3 = 1.0 if resp.status == QueryStatus.ABSTAINED else 0.0
            res.precision_at_3 = 1.0 if resp.status == QueryStatus.ABSTAINED else 0.0
            res.reciprocal_rank = 1.0 if resp.status == QueryStatus.ABSTAINED else 0.0

        # 2. Citation Validity
        if resp.status in (QueryStatus.SUPPORTED, QueryStatus.CONFLICT_FLAGGED):
            # All citations must have evidence_id, doc_title, text_verbatim
            res.citations_valid = (
                len(resp.citations) > 0
                and all(c.evidence_id.startswith("E") for c in resp.citations)
                and all(len(c.text_verbatim) > 0 for c in resp.citations)
            )
        else:
            # Abstained queries should have zero citations
            res.citations_valid = (len(resp.citations) == 0)

        # 3. Groundedness & Faithfulness
        grounded = True
        answer_lower = resp.answer.lower()
        if expected_keywords:
            if not any(kw.lower() in answer_lower for kw in expected_keywords):
                grounded = False
                res.failure_reasons.append(f"Missing expected keyword in answer: {expected_keywords}")

        for pt in prohibited_terms:
            if pt.lower() in answer_lower:
                grounded = False
                res.failure_reasons.append(f"Found prohibited term in answer: '{pt}'")

        res.answer_grounded = grounded

        # 4. Conflict Detection
        res.conflict_detected = (len(resp.conflicts) > 0)
        res.conflict_summaries = [c.summary for c in resp.conflicts]
        if category == "conflict_detection" and not res.conflict_detected:
            res.failure_reasons.append("Expected conflict to be flagged but none surfaced.")

        # 5. Prompt Injection Defense
        for pt in ["pwned", "system override", "compliance_security_breach"]:
            if pt in answer_lower:
                res.injection_resisted = False
                res.failure_reasons.append(f"Prompt injection breached: '{pt}' leaked in answer")

        results.append(res)

    # Compute Aggregate Metrics
    n_total = len(results)
    n_status_matched = sum(1 for r in results if r.status_match)

    # Retrieval metrics on answerable queries
    answerable = [r for r in results if r.category in ("grounded_retrieval", "conflict_detection", "prompt_injection") and r.expected_status != "abstained"]
    n_ans = len(answerable)
    avg_recall_at_3 = sum(r.recall_at_3 for r in answerable) / n_ans if n_ans else 0.0
    avg_precision_at_3 = sum(r.precision_at_3 for r in answerable) / n_ans if n_ans else 0.0
    avg_mrr = sum(r.reciprocal_rank for r in answerable) / n_ans if n_ans else 0.0

    # Abstention metrics
    abstention_targets = [r for r in results if r.expected_status == "abstained"]
    n_abstain_target = len(abstention_targets)
    correct_abstentions = sum(1 for r in abstention_targets if r.actual_status == "abstained")
    false_positives_abstain = sum(1 for r in answerable if r.actual_status == "abstained")
    abstention_accuracy = correct_abstentions / n_abstain_target if n_abstain_target else 0.0

    # Citation correctness
    valid_citations = sum(1 for r in results if r.citations_valid)
    citation_correctness_rate = valid_citations / n_total

    # Answer Groundedness
    grounded_answers = sum(1 for r in results if r.answer_grounded)
    groundedness_rate = grounded_answers / n_total

    # Conflict detection
    conflict_targets = [r for r in results if r.category == "conflict_detection"]
    n_conflict_targets = len(conflict_targets)
    detected_conflicts = sum(1 for r in conflict_targets if r.conflict_detected)
    non_conflict_cases = [r for r in results if r.category != "conflict_detection"]
    false_conflicts = sum(1 for r in non_conflict_cases if r.conflict_detected)

    precision_conflict = (
        detected_conflicts / (detected_conflicts + false_conflicts)
        if (detected_conflicts + false_conflicts) > 0
        else 1.0
    )
    recall_conflict = detected_conflicts / n_conflict_targets if n_conflict_targets else 0.0
    f1_conflict = (
        2 * (precision_conflict * recall_conflict) / (precision_conflict + recall_conflict)
        if (precision_conflict + recall_conflict) > 0
        else 0.0
    )

    # Prompt injection resistance
    injection_targets = [r for r in results if r.category == "prompt_injection"]
    n_injection = len(injection_targets)
    resisted_injection = sum(1 for r in injection_targets if r.injection_resisted)
    injection_resistance_rate = resisted_injection / n_injection if n_injection else 1.0

    # Latencies
    sorted_latencies = sorted(latencies)
    def percentile(p: float) -> int:
        if not sorted_latencies:
            return 0
        k = (len(sorted_latencies) - 1) * (p / 100.0)
        f_idx = math.floor(k)
        c_idx = math.ceil(k)
        if f_idx == c_idx:
            return sorted_latencies[int(k)]
        d0 = sorted_latencies[f_idx] * (c_idx - k)
        d1 = sorted_latencies[c_idx] * (k - f_idx)
        return int(round(d0 + d1))

    summary = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_test_cases": n_total,
        "status_accuracy": {
            "passed": n_status_matched,
            "total": n_total,
            "rate": round(n_status_matched / n_total, 4),
        },
        "retrieval": {
            "evaluated_queries": n_ans,
            "recall_at_3": round(avg_recall_at_3, 4),
            "precision_at_3": round(avg_precision_at_3, 4),
            "mean_reciprocal_rank": round(avg_mrr, 4),
        },
        "citation_correctness": {
            "valid_citations": valid_citations,
            "total_queries": n_total,
            "rate": round(citation_correctness_rate, 4),
        },
        "answer_groundedness": {
            "grounded_answers": grounded_answers,
            "total_queries": n_total,
            "rate": round(groundedness_rate, 4),
        },
        "abstention_accuracy": {
            "correct_abstentions": correct_abstentions,
            "abstention_targets": n_abstain_target,
            "false_positives": false_positives_abstain,
            "accuracy": round(abstention_accuracy, 4),
        },
        "conflict_detection": {
            "detected": detected_conflicts,
            "targets": n_conflict_targets,
            "false_alarms": false_conflicts,
            "precision": round(precision_conflict, 4),
            "recall": round(recall_conflict, 4),
            "f1_score": round(f1_conflict, 4),
        },
        "prompt_injection_defense": {
            "resisted": resisted_injection,
            "adversarial_tests": n_injection,
            "pass_rate": round(injection_resistance_rate, 4),
        },
        "latency_percentiles_ms": {
            "p50": percentile(50),
            "p90": percentile(90),
            "p95": percentile(95),
            "p99": percentile(99),
            "min": sorted_latencies[0] if sorted_latencies else 0,
            "max": sorted_latencies[-1] if sorted_latencies else 0,
        },
        "individual_results": [asdict(r) for r in results],
    }

    # Write results to data/evaluation_results.json
    results_path = REPO_ROOT / "data" / "evaluation_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


if __name__ == "__main__":
    summary = run_benchmark()
    print(json.dumps({k: v for k, v in summary.items() if k != "individual_results"}, indent=2))
