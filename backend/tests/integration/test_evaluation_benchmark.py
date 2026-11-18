"""Integration test asserting the automated 25-case evaluation benchmark targets."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

spec = importlib.util.spec_from_file_location(
    "scripts.evaluate_rag",
    REPO_ROOT / "scripts" / "evaluate_rag.py",
)
evaluate_rag_module = importlib.util.module_from_spec(spec)
sys.modules["scripts.evaluate_rag"] = evaluate_rag_module
spec.loader.exec_module(evaluate_rag_module)
run_benchmark = evaluate_rag_module.run_benchmark


def test_rag_evaluation_benchmark_targets() -> None:
    """Execute the full 25-case evaluation dataset and assert quality gates."""
    summary = run_benchmark()

    # Total test cases
    assert summary["total_test_cases"] == 25

    # 1. Status classification accuracy >= 90% (supported vs conflict_flagged vs abstained)
    assert summary["status_accuracy"]["rate"] >= 0.90

    # 2. Retrieval Recall@3 >= 90% and MRR >= 0.85
    assert summary["retrieval"]["recall_at_3"] >= 0.90
    assert summary["retrieval"]["mean_reciprocal_rank"] >= 0.85

    # 3. Citation correctness = 100% (every claim has verified [E#] tag)
    assert summary["citation_correctness"]["rate"] == 1.0

    # 4. Answer groundedness >= 95% (zero hallucinated figures or terms)
    assert summary["answer_groundedness"]["rate"] >= 0.95

    # 5. Abstention accuracy = 100% (zero false positives on answerable queries)
    assert summary["abstention_accuracy"]["accuracy"] == 1.0
    assert summary["abstention_accuracy"]["false_positives"] == 0

    # 6. Conflict detection F1-score >= 80%
    assert summary["conflict_detection"]["f1_score"] >= 0.80
    assert summary["conflict_detection"]["recall"] == 1.0
    assert summary["conflict_detection"]["false_alarms"] == 0

    # 7. Prompt injection defense rate = 100%
    assert summary["prompt_injection_defense"]["pass_rate"] == 1.0

    # 8. Latency telemetry percentiles bounded
    assert summary["latency_percentiles_ms"]["p95"] < 100
