"""End-to-end grounded query execution, retrieval, validation, and abstention service."""

from __future__ import annotations

import logging
import re
import time
import uuid
from datetime import date
from typing import Any

from app.core.config import Settings
from app.generation.conflict_detector import ConflictDetector
from app.generation.llm_adapter import LLMAdapter, get_llm_adapter
from app.generation.models import EvidenceBlock
from app.generation.prompt import clean_query_text
from app.generation.validator import CitationValidator
from app.retrieval.embeddings import EmbeddingAdapter, get_embedding_adapter
from app.retrieval.vector_store import VectorStorePort, get_vector_store
from app.schemas.documents import ContentType, DocumentType, ExtractionMethod
from app.schemas.query import (
    LatencyBreakdown,
    QueryFilters,
    QueryRequest,
    QueryResponse,
    QueryStatus,
)

logger = logging.getLogger(__name__)

STANDARD_DISCLAIMER = (
    "AI-generated decision support. Verify cited source clauses and governing "
    "revisions before site execution."
)

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
    "under",
    "above",
    "with",
    "from",
    "by",
    "about",
    "into",
    "through",
    "during",
    "before",
    "after",
    "between",
    "against",
    "out",
    "over",
    "all",
    "any",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "than",
    "too",
    "very",
    "have",
    "has",
    "had",
    "having",
}


def _parse_optional_date(raw: Any) -> date | None:
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return date.fromisoformat(raw.strip())
        except ValueError:
            return None
    return None


class QueryService:
    """Orchestrates hybrid retrieval, conflict detection, grounded generation, and citations."""

    def __init__(
        self,
        settings: Settings,
        embedding_adapter: EmbeddingAdapter | None = None,
        vector_store: VectorStorePort | None = None,
        llm_adapter: LLMAdapter | None = None,
        citation_validator: CitationValidator | None = None,
        conflict_detector: ConflictDetector | None = None,
    ) -> None:
        self.settings = settings
        self.embedding_adapter = embedding_adapter or get_embedding_adapter(settings)
        self.vector_store = vector_store or get_vector_store(settings)
        self.llm_adapter = llm_adapter or get_llm_adapter(settings)
        self.citation_validator = citation_validator or CitationValidator()
        self.conflict_detector = conflict_detector or ConflictDetector()
        self.collection_name = settings.vector_db_collection

    def execute_query(self, request: QueryRequest) -> QueryResponse:
        """Execute a full grounded compliance query pipeline."""
        start_total = time.perf_counter()
        query_id = f"qry_{uuid.uuid4().hex[:12]}"
        cleaned_query = clean_query_text(request.query)

        latency = LatencyBreakdown()

        # -------------------------------------------------------------
        # Step 1: Compute query embedding
        # -------------------------------------------------------------
        start_embed = time.perf_counter()
        query_vector = self.embedding_adapter.embed_query(cleaned_query)
        latency.embedding = round((time.perf_counter() - start_embed) * 1000)

        # -------------------------------------------------------------
        # Step 2: Retrieve candidate chunks with metadata pre-filtering
        # -------------------------------------------------------------
        start_ret = time.perf_counter()
        filter_dict = self._build_filter_dict(request.filters)
        limit = min(max(request.top_k * 2, 5), 20)

        hits = self.vector_store.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            filters=filter_dict,
        )
        latency.retrieval = round((time.perf_counter() - start_ret) * 1000)

        # -------------------------------------------------------------
        # Step 3: Gate 1 Abstention Check (Pre-Generation)
        # -------------------------------------------------------------
        if not hits:
            logger.info(
                "Gate 1 Abstention: 0 candidate chunks retrieved", extra={"query_id": query_id}
            )
            latency.total = round((time.perf_counter() - start_total) * 1000)
            return QueryResponse(
                query_id=query_id,
                status=QueryStatus.ABSTAINED,
                answer="I cannot find relevant information in the provided codes or reports.",
                citations=[],
                conflicts=[],
                abstention_reason=(
                    "No relevant document chunks found matching query and metadata filters."
                ),
                latency_ms=latency,
                disclaimer=STANDARD_DISCLAIMER,
            )

        # Check semantic relevance & lexical overlap
        query_tokens = {
            t.lower()
            for t in re.findall(r"\b[A-Za-z0-9]+\b", cleaned_query)
            if t.lower() not in STOP_WORDS and len(t) > 2
        }
        has_lexical_match = False
        for hit in hits:
            hit_tokens = {t.lower() for t in re.findall(r"\b[A-Za-z0-9]+\b", hit.text_verbatim)}
            if len(query_tokens.intersection(hit_tokens)) >= 2:
                has_lexical_match = True
                break

        # If top retrieval score is very low AND there is zero non-stopword keyword match
        if hits[0].score < 0.25 and not has_lexical_match:
            logger.info(
                "Gate 1 Abstention: low retrieval confidence and zero keyword overlap",
                extra={"query_id": query_id, "top_score": hits[0].score},
            )
            latency.total = round((time.perf_counter() - start_total) * 1000)
            return QueryResponse(
                query_id=query_id,
                status=QueryStatus.ABSTAINED,
                answer="I cannot find relevant information in the provided codes or reports.",
                citations=[],
                conflicts=[],
                abstention_reason=(
                    "Insufficient semantic retrieval confidence and no keyword overlap."
                ),
                latency_ms=latency,
                disclaimer=STANDARD_DISCLAIMER,
            )

        # -------------------------------------------------------------
        # Step 4: Assemble bounded evidence context [E1]..[Ek]
        # -------------------------------------------------------------
        bounded_hits = hits[: request.top_k]
        evidence_blocks: list[EvidenceBlock] = []
        for idx, hit in enumerate(bounded_hits, 1):
            p = hit.payload or {}
            evidence_blocks.append(
                EvidenceBlock(
                    evidence_id=f"E{idx}",
                    chunk_id=str(p.get("chunk_id", hit.chunk_id)),
                    doc_id=str(p.get("doc_id", hit.doc_id)),
                    doc_title=str(p.get("doc_title", "Untitled Document")),
                    doc_type=DocumentType(p.get("doc_type", "spec")),
                    version=str(p.get("version", "v1.0")),
                    effective_date=_parse_optional_date(p.get("effective_date")),
                    jurisdiction=str(p.get("jurisdiction", "UNSPECIFIED")),
                    project_id=p.get("project_id"),
                    standard_code=p.get("standard_code"),
                    section_id=p.get("section_id"),
                    section_path=list(p.get("section_path", [])),
                    page_start=int(p.get("page_start", 1)),
                    page_end=int(p.get("page_end", 1)),
                    content_type=ContentType(p.get("content_type", "prose")),
                    extraction_method=ExtractionMethod(p.get("extraction_method", "native")),
                    retrieval_score=hit.score,
                    text_verbatim=hit.text_verbatim,
                )
            )

        # -------------------------------------------------------------
        # Step 5: Detect cross-document and revision conflicts
        # -------------------------------------------------------------
        conflicts = self.conflict_detector.detect_conflicts(evidence_blocks, cleaned_query)

        # -------------------------------------------------------------
        # Step 6: Grounded LLM Generation
        # -------------------------------------------------------------
        start_gen = time.perf_counter()
        draft = self.llm_adapter.generate_grounded(cleaned_query, evidence_blocks)
        latency.generation = round((time.perf_counter() - start_gen) * 1000)

        # -------------------------------------------------------------
        # Step 7: Gate 2 Abstention Check (In-Context Refusal)
        # -------------------------------------------------------------
        if draft.is_abstain or draft.answer.strip().upper() in ("ABSTAIN", "ABSTAIN.", "I ABSTAIN"):
            logger.info("Gate 2 Abstention: LLM signaled ABSTAIN", extra={"query_id": query_id})
            latency.total = round((time.perf_counter() - start_total) * 1000)
            return QueryResponse(
                query_id=query_id,
                status=QueryStatus.ABSTAINED,
                answer=(
                    "The retrieved documents do not contain sufficient regulatory "
                    "evidence to answer this requirement."
                ),
                citations=[],
                conflicts=[],
                abstention_reason=(
                    draft.abstain_reason or "Insufficient regulatory evidence in corpus."
                ),
                latency_ms=latency,
                disclaimer=STANDARD_DISCLAIMER,
            )

        # -------------------------------------------------------------
        # Step 8: Citation and Groundedness Validation
        # -------------------------------------------------------------
        start_val = time.perf_counter()
        validation = self.citation_validator.validate(draft.answer, evidence_blocks)
        latency.validation = round((time.perf_counter() - start_val) * 1000)

        # -------------------------------------------------------------
        # Step 9: Gate 3 Abstention Check (Validation Failure)
        # -------------------------------------------------------------
        if not validation.is_valid:
            logger.warning(
                "Gate 3 Abstention: Citation validation failed",
                extra={"query_id": query_id, "unverified_claims": validation.unverified_claims},
            )
            latency.total = round((time.perf_counter() - start_total) * 1000)
            return QueryResponse(
                query_id=query_id,
                status=QueryStatus.ABSTAINED,
                answer="I cannot verify the generated answer against the retrieved source clauses.",
                citations=[],
                conflicts=[],
                abstention_reason=validation.abstain_reason,
                latency_ms=latency,
                disclaimer=STANDARD_DISCLAIMER,
            )

        # -------------------------------------------------------------
        # Step 10: Compile Final Verified Response
        # Filter surfaced conflicts to those directly relevant to cited documents
        # -------------------------------------------------------------
        cited_doc_ids = {c.doc_id for c in validation.citations}
        relevant_conflicts = [
            c
            for c in conflicts
            if c.source_a.doc_id in cited_doc_ids or c.source_b.doc_id in cited_doc_ids
        ]

        status = QueryStatus.CONFLICT_FLAGGED if relevant_conflicts else QueryStatus.SUPPORTED
        latency.total = round((time.perf_counter() - start_total) * 1000)

        logger.info(
            "Query answered successfully",
            extra={
                "query_id": query_id,
                "status": status.value,
                "citations_count": len(validation.citations),
                "conflicts_count": len(relevant_conflicts),
                "total_latency_ms": latency.total,
            },
        )

        return QueryResponse(
            query_id=query_id,
            status=status,
            answer=validation.verified_answer,
            citations=validation.citations,
            conflicts=relevant_conflicts,
            abstention_reason=None,
            latency_ms=latency,
            disclaimer=STANDARD_DISCLAIMER,
        )

    @staticmethod
    def _build_filter_dict(filters: QueryFilters | None) -> dict[str, Any]:
        """Convert QueryFilters Pydantic schema to Qdrant filter dictionary."""
        if filters is None:
            return {"status": "active"}

        filter_dict: dict[str, Any] = {}
        if filters.project_id:
            filter_dict["project_id"] = filters.project_id
        if filters.jurisdiction:
            filter_dict["jurisdiction"] = filters.jurisdiction
        if filters.doc_types:
            filter_dict["doc_types"] = [dt.value for dt in filters.doc_types]

        if not filters.include_superseded:
            filter_dict["status"] = "active"

        return filter_dict
