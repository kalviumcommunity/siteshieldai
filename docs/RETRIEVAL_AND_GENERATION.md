# Site Shield AI — Retrieval & Grounded Answer Pipeline Architecture

## 1. Overview and Architectural Alignment

Site Shield AI delivers a high-precision, safety-critical regulatory compliance assistant for construction engineering. In accordance with the approved architecture ([`docs/RAG_ARCHITECTURE.md`](file:///home/abhinivesh/Downloads/siteshield_ai/docs/RAG_ARCHITECTURE.md)) and PRD requirements, this document details the implementation of the retrieval and grounded answer generation pipeline (Gate 6).

### Core Invariants Enforced

1. **Anti-Hallucination & Strict Grounding:** The model is strictly prohibited from citing regulatory standards or asserting safety numbers not present verbatim in the retrieved corpus. A similarity score is **never** presented as proof of regulatory correctness.
2. **Three-Gate Deterministic Abstention:** If evidence is absent, insufficient, or fails citation verification, the system refuses to answer (`status="abstained"`) with an explicit reason, rather than speculating or offering dangerous guesswork.
3. **Traceable Source Provenance:** Every claim is tied to an inline citation tag (`[E#]`) referencing an exact chunk payload (`chunk_id`, `doc_title`, `version`, `page_start`, `page_end`, `section_id`, `retrieval_score`, `text_verbatim`).
4. **Transparent Conflict & Precedence Flagging:** Divergences between governing codes/specifications and historical site inspection reports, or superseded revisions, are surfaced in structured `conflicts` payloads with legal precedence guidance.
5. **Indirect Prompt Injection Neutralization:** Retrieved chunks are treated as untrusted text, safely enclosed in `<evidence>` tags with CDATA and escaped XML brackets, and sanitized of adversarial control commands (`"Ignore previous instructions"`).

---

## 2. Retrieval Pipeline Architecture

```
User Query ──► Query Normalization & Input Validation
                     │
                     ▼
          Metadata Filter Compilation (project_id, jurisdiction, doc_types, superseded)
                     │
                     ▼
          Embedding Generation (FastEmbed local ONNX / OpenAI)
                     │
                     ▼
          Qdrant Vector Retrieval (Top-K, Cosine Metric)
                     │
                     ▼
          [Gate 1 Abstention Check] ──(Low score & zero lexical overlap)──► ABSTAIN
                     │
                     ▼
          Evidence Context Assembly (<evidence id="E#" ...> CDATA </evidence>)
                     │
                     ▼
          Conflict Detection (Version supersession, report vs spec divergence)
                     │
                     ▼
          LLM Generation (Deterministic Mock / OpenAI Adapter)
                     │
                     ▼
          [Gate 2 Abstention Check] ──(LLM outputs "ABSTAIN")─────────────► ABSTAIN
                     │
                     ▼
          3-Stage Citation Validation (Tag integrity, sentence coverage, literal check)
                     │
                     ├──(Validation Failure)──────────────────────────────► ABSTAIN (Gate 3)
                     │
                     ▼
          Structured QueryResponse (Status, Verified Answer, Citations, Conflicts, Latency)
```

### 2.1 Metadata Filtering & Isolation

Pre-filtering in Qdrant ensures that queries are strictly bounded to the appropriate project, jurisdiction, and governing lifecycle stage:
- **`project_id` scoping:** Prevents cross-project leakage of proprietary contractor bids or site-specific drawings.
- **`jurisdiction` scoping:** Filters out inapplicable building codes (e.g., California CBC vs Indian NBC / IS).
- **`doc_types` filtering:** Allows users or automated agents to query only governing standards (`spec`, `code`) or audit logs (`report`).
- **`include_superseded` toggle:** Defaults to `False`, excluding superseded document versions unless historical audit analysis is requested.

### 2.2 Source Provenance Retention

When vector search returns nearest neighbors, each chunk preserves the complete ingestion provenance in its payload:
- `doc_id`, `chunk_id`, `doc_title`, `doc_type`
- `version`, `publication_date`, `effective_date`
- `jurisdiction`, `project_id`, `standard_code`
- `section_id`, `section_path`
- `page_start`, `page_end`
- `content_type`, `extraction_method`
- `retrieval_score` (cosine similarity score)
- `text_verbatim` (exact extracted source text)

---

## 3. The Three-Gate Abstention Framework

To guarantee zero false confidence in life-safety construction questions, the system implements a sequential, 3-gate abstention pipeline:

| Gate | Stage | Trigger Condition | Emitted Status | User Message / Reason |
|---|---|---|---|---|
| **Gate 1** | **Retrieval Pre-Check** | Empty search results OR (Top score < threshold AND zero lexical overlap with query tokens) | `QueryStatus.ABSTAINED` | `"No relevant documents found in the corpus."` |
| **Gate 2** | **In-Context Refusal** | Model emits `ABSTAIN` (evidence context does not contain answer) | `QueryStatus.ABSTAINED` | `"The retrieved documents do not contain sufficient regulatory evidence..."` |
| **Gate 3** | **Validation Post-Check** | Citation validation fails (hallucinated `[E#]`, uncited claim, or numeric value mismatch) | `QueryStatus.ABSTAINED` | `"Grounded generation failed citation verification: <reason>"` |

### Gate 1: Retrieval Abstention
Before invoking the LLM, the `QueryService` evaluates the similarity score and lexical overlap. If Qdrant returns no hits, or if the top hit has a low score and shares fewer than two meaningful keywords with the question (e.g. asking for *"speed of sound in seawater"* against an excavation safety corpus), the pipeline terminates immediately without consuming LLM inference tokens.

### Gate 2: In-Context LLM Abstention
The system prompt strictly commands the LLM:
> *"If the retrieved evidence does not contain sufficient facts to answer the question completely and factually, output ONLY 'ABSTAIN'. Do NOT extrapolate, speculate, or draw on external knowledge."*

If the model outputs `ABSTAIN`, the service records `QueryStatus.ABSTAINED` and supplies the reason to the caller.

### Gate 3: Deterministic Post-Generation Verification
Even if the model generates text, the answer is unverified until it passes the deterministic `CitationValidator`. If the model fabricated a claim, missed a citation, or cited an invalid evidence ID, Gate 3 catches it and demotes the response to `ABSTAINED`.

---

## 4. Deterministic Citation Validation Pipeline

The `CitationValidator` in [`backend/app/generation/validator.py`](file:///home/abhinivesh/Downloads/siteshield_ai/backend/app/generation/validator.py) executes a deterministic, 3-stage audit on every generated answer:

```
                  ┌────────────────────────────────────────┐
                  │          Generated Draft Answer        │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
               [Stage 1: Citation Tag Integrity Verification]
               - All [E#] tags must exist in retrieved evidence
               - Fails if [E99] appears but only [E1, E2] retrieved
                                      │
                                      ▼
               [Stage 2: Sentence-Level Coverage Verification]
               - Every factual sentence (>15 chars or digits)
                 must carry at least one [E#] citation tag
               - Trailing and inline tags preserved with sentence
                                      │
                                      ▼
               [Stage 3: Literal Number, Unit & Clause Cross-Check]
               - Any number (e.g., "14 days", "50 mm", "75 degrees")
                 must appear verbatim in cited chunk's text_verbatim
               - Any clause reference (e.g., "Clause 4.2.1", "IS 456")
                 must appear verbatim in cited chunk's text_verbatim
                                      │
                                      ▼
                      Validated Grounded Output / Citations
```

### 4.1 Stage 1: Tag Integrity Check
Extracts all `\[E(\d+)\]` patterns from the generated answer and verifies that every referenced ID exists in the retrieved `evidence_blocks`. Any hallucinated tag causes immediate failure.

### 4.2 Stage 2: Sentence-Level Coverage Check
Splits the text into logical sentences. Any non-trivial sentence (length > 15 characters or containing digits) must contain at least one valid citation tag. This guarantees that ungrounded introductory or bridging statements cannot smuggle in unverified regulatory claims.

### 4.3 Stage 3: Literal Number, Unit, and Clause Cross-Check
Regulatory compliance relies on precise numeric thresholds (curing periods, cover depths, rebar diameters, slopes, fire ratings).
The validator extracts:
- Quantities and units (`NUMERIC_UNIT_PATTERN`: e.g., `14 days`, `50 mm`, `75 degrees`, `1.5 m`, `20 MPa`).
- Clause references (`CLAUSE_ID_PATTERN`: e.g., `Clause 4.2.1`, `Section 5.3`, `IS 456:2000`).

It verifies that every extracted numeric quantity in a sentence exists in the verbatim text of the specific `EvidenceBlock` cited by that sentence. If a model says *"Foundation slabs shall be cured for 21 days [E1]"* while E1 specifies *14 days*, Stage 3 flags `Numeric claim '21 days' in sentence not found in cited evidence: E1` and refuses the response.

---

## 5. Conflict Detection & Precedence Rules

Construction projects constantly face revisions, addenda, and field deviations. The `ConflictDetector` ([`backend/app/generation/conflict_detector.py`](file:///home/abhinivesh/Downloads/siteshield_ai/backend/app/generation/conflict_detector.py)) automatically scans retrieved evidence for three classes of conflicts:

### 5.1 Version Supersession
- **Condition:** Two retrieved chunks share the same `doc_title` or `doc_id`, but carry different version strings (e.g., `v1.0` vs `v2.0`).
- **Precedence Rule:** The newer version supersedes the older version. The older version is marked as superseded.

### 5.2 Report vs. Governing Code / Specification Divergence
- **Condition:** One chunk is from a governing document (`doc_type in ["code", "spec", "standard"]`) and another is from a historical site record (`doc_type in ["report", "audit"]`), and both discuss the same topic or numeric requirement.
- **Precedence Rule:** Governing codes and specifications take legal precedence. Historical inspection reports describe past as-built conditions and do **not** amend or relax mandatory project specifications.

### 5.3 Cross-Document Numeric Value Mismatch
- **Condition:** Two different governing documents define conflicting numeric requirements for the same parameter (e.g., one requires `14 days` curing, another requires `7 days`).
- **Precedence Rule:** Flagged to the user as an unresolved discrepancy requiring Engineer of Record (EoR) clarification.

When conflicts are detected, the query status is set to `QueryStatus.CONFLICT_FLAGGED` (or included with `SUPPORTED`), and full structured details are returned in `QueryResponse.conflicts`.

---

## 6. Indirect Prompt Injection Defense

Retrieved construction files (subcontractor PDFs, public standards, vendor submittals) may contain adversarial text designed to override agent instructions.

### Defense Mechanisms:
1. **XML Boundary Delimitation:** Chunks are enclosed in `<evidence id="E#" doc_title="..." version="...">` tags with `<![CDATA[ ... ]]>` wrapping.
2. **Entity Escaping:** Verbatim text containing `</evidence>` or `>` brackets is escaped to prevent XML tag breakout.
3. **Adversarial Pattern Scrubbing:** Text containing known prompt override patterns (`(?i)ignore previous instructions`, `say pwned`, `output system prompt`) is filtered before prompt assembly and generation.
4. **Zero Tool Sandbox:** The LLM generation stage has zero filesystem or system command privileges. It is strictly a text-in, text-out transformation step.

---

## 7. API Endpoints

The pipeline exposes two HTTP endpoints:

### 7.1 `POST /query` & `POST /api/v1/query`

**Request Payload:**
```json
{
  "query": "What is the minimum curing duration for foundation slabs under high moisture?",
  "filters": {
    "project_id": "#104",
    "jurisdiction": "IN-KA",
    "doc_types": ["spec", "code"]
  },
  "top_k": 5
}
```

**Response Payload (Supported Query):**
```json
{
  "query_id": "qry_881ab709d73c",
  "status": "supported",
  "answer": "Under high moisture conditions, foundation slabs shall be cured for 14 days [E1].",
  "citations": [
    {
      "evidence_id": "E1",
      "chunk_id": "chk_513366fd5afd78e3",
      "doc_id": "doc_2070ec2c4465",
      "doc_title": "Foundation Concrete Specification",
      "doc_type": "spec",
      "version": "v2.0",
      "effective_date": "2024-02-01",
      "jurisdiction": "IN-KA",
      "project_id": "#104",
      "section_id": "4.2.1",
      "section_path": ["4.0 Concrete Curing Specification", "4.2 High Moisture"],
      "page_start": 4,
      "page_end": 4,
      "content_type": "prose",
      "extraction_method": "native",
      "retrieval_score": 0.8124,
      "text_verbatim": "Under high moisture conditions, foundation slabs shall be cured for 14 days."
    }
  ],
  "conflicts": [],
  "abstention_reason": null,
  "latency_ms": {
    "embedding": 12,
    "retrieval": 15,
    "generation": 34,
    "validation": 2,
    "total": 63
  },
  "disclaimer": "Site Shield AI is an assistive decision-support system for construction compliance. All citations, clauses, and conflict flags must be independently verified by the Engineer of Record (EoR) or certified safety inspector before construction execution."
}
```

**Response Payload (Conflicted Query):**
```json
{
  "query_id": "qry_791df8820c41",
  "status": "conflict_flagged",
  "answer": "Foundation slabs shall be cured for 14 days [E1]. Historical inspection report 'Site Inspection Report 01' (v1.0) noted: Foundation slabs were cured for 7 days before formwork removal [E2].",
  "citations": [ ... ],
  "conflicts": [
    {
      "conflict_type": "report_vs_code_divergence",
      "source_a": {
        "doc_id": "doc_0c34a088a16e",
        "doc_title": "Governing Concrete Specification",
        "version": "v2.0",
        "page_start": 1,
        "excerpt": "Foundation slabs shall be cured for 14 days."
      },
      "source_b": {
        "doc_id": "doc_836a4a99cf10",
        "doc_title": "Site Inspection Report 01",
        "version": "v1.0",
        "page_start": 1,
        "excerpt": "Foundation slabs were cured for 7 days before formwork removal."
      },
      "summary": "Governing specification 'Governing Concrete Specification' requires 14 days, whereas historical site inspection report 'Site Inspection Report 01' records 7 days.",
      "precedence_note": "Governing codes and specifications take precedence over historical site inspection reports. Past inspection notes record as-built conditions and do not modify project requirements."
    }
  ],
  "latency_ms": { ... },
  "disclaimer": "..."
}
```

---

## 8. Test & Verification Evidence

All tests pass 100% across unit and integration suites without mock regressions:

```bash
backend/.venv/bin/pytest backend/ -v
======================== 73 passed, 1 warning in 10.88s ========================
```

### Covered Test Dimensions:
- **`test_supported_compliance_question_with_citations`:** Verifies accurate retrieval, inline `[E1]` citation attachment, metadata preservation, and latency telemetry.
- **`test_unsupported_question_triggers_abstention`:** Verifies Gate 1 and Gate 2 abstention on questions outside the corpus domain.
- **`test_conflicting_documents_flags_conflict_and_precedence`:** Verifies detection of report-versus-spec discrepancies and version supersession.
- **`test_indirect_document_prompt_injection_defense`:** Verifies neutralization of malicious command injections embedded in untrusted PDFs.
- **`test_api_route_query_and_v1_alias`:** Verifies HTTP 200 contract across both `/query` and `/api/v1/query`, and HTTP 422 on blank query text.
- **`test_citation_validator`:** Verifies detection of hallucinated citation tags, missing citations on factual claims, and numeric mismatches.
- **`test_conflict_detector`:** Verifies isolation and summary construction across all three conflict types.
- **Ruff Lint & Format:** `ruff check backend/` and `ruff format --check backend/` pass cleanly with 0 errors.
