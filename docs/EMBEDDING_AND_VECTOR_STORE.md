# Site Shield AI — Embedding & Vector Storage Architecture

## 1. Overview and Architectural Alignment

Site Shield AI requires a high-precision, low-latency retrieval layer designed specifically for construction regulatory compliance, technical specifications, and site inspection records. In accordance with the approved architecture ([`docs/RAG_ARCHITECTURE.md`](file:///home/abhinivesh/Downloads/siteshield_ai/docs/RAG_ARCHITECTURE.md)) and PRD requirements, this document details the implementation of the embedding and vector storage layer (Gate 5).

The implementation enforces three core invariants:
1. **Data Residency & Air-Gapped Operation (`OQ-06`):** The primary default embedding provider runs 100% locally in-process via FastEmbed ONNX Runtime (`BAAI/bge-base-en-v1.5` or `bge-small-en-v1.5`), ensuring confidential project drawings, specifications, and site inspection notes never leave the local environment without explicit administrative consent.
2. **Deterministic Provenance & Source Traceability:** Every vector stored in the vector database preserves the complete document- and chunk-level provenance payload (`doc_id`, `chunk_id`, `doc_title`, `version`, `section_id`, `section_path`, `page_start`, `page_end`, `content_type`, `extraction_method`, and `text_verbatim`) necessary for strict citation validation and side-by-side UI rendering.
3. **Repeatable Indexing & Idempotent Update Detection:** Re-ingesting identical content skips vector operations completely (zero duplicate vectors, zero wasted compute). Modifying an existing document triggers deterministic purging of old vectors before indexing the new revision, guaranteeing zero orphaned points.

---

## 2. Embedding Layer Architecture

### 2.1 Provider Abstraction (`EmbeddingAdapter`)

The embedding layer is isolated behind a strict Python `Protocol` defined in [`backend/app/retrieval/embeddings.py`](file:///home/abhinivesh/Downloads/siteshield_ai/backend/app/retrieval/embeddings.py):

```python
class EmbeddingAdapter(Protocol):
    @property
    def model_name(self) -> str: ...
    @property
    def dimension(self) -> int: ...
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
```

### 2.2 Supported Embedding Models and Dimensions

| Provider | Model Identifier | Dimensions | Primary Use Case | Data Residency (`OQ-06`) | Typical Latency (CPU) |
|---|---|---|---|---|---|
| **FastEmbed (Default Local)** | `BAAI/bge-base-en-v1.5` | **768** | Production default for air-gapped / local compliance | 100% Local (Zero egress) | ~20–50 ms / batch |
| **FastEmbed (Lightweight Local)** | `BAAI/bge-small-en-v1.5` | **384** | Resource-constrained containers / fast local dev | 100% Local (Zero egress) | ~8–20 ms / batch |
| **OpenAI (Cloud Adapter)** | `text-embedding-3-small` | **1536** | Cloud environments with authorized API egress | External Cloud API | ~80–180 ms (network) |
| **OpenAI (High-Capacity Cloud)** | `text-embedding-3-large` | **3072** | High-dimensional cloud indexing | External Cloud API | ~120–250 ms (network) |
| **Deterministic Mock** | `mock-deterministic` | **Configurable (default 768)** | Unit testing, integration testing, CI pipelines | 100% In-Memory (<0.1 ms) | < 0.1 ms |

### 2.3 Provider Selection Trade-Off Analysis

```
                              Embedding Trade-Off Matrix
┌──────────────────────────────────────┬──────────────────────────────────────┐
│ FastEmbed ONNX (BGE-base / small)   │ OpenAI (text-embedding-3-small)      │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ [+] Zero external egress (OQ-06 safe)│ [+] Zero local CPU/RAM utilization   │
│ [+] Zero per-query API costs         │ [+] Higher dimensional representation│
│ [+] No network failure modes         │ [-] Sends chunk text to external API │
│ [+] Deterministic CPU inference      │ [-] Requires billing & active key    │
│ [-] Local CPU consumption on ingest  │ [-] Subject to 429 rate limits       │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

**Architectural Rationale:**
- In construction risk management, proprietary contractor bids, project site blueprints, and safety incident reports frequently carry strict confidentiality obligations (`OQ-06`). Defaulting to **FastEmbed ONNX** satisfies all data privacy requirements out of the box while avoiding heavy PyTorch dependencies.
- The **OpenAI Adapter** is supported via `EMBEDDING_PROVIDER=openai` and reads `EMBEDDING_API_KEY` exclusively from environment variables. If credentials are missing when OpenAI is selected, the application raises a clear `ConfigurationError` (`MISSING_EMBEDDING_API_KEY`) before serving any requests.

### 2.4 Index Isolation Invariant

In accordance with `docs/RAG_ARCHITECTURE.md` §6, mixing embeddings of differing dimensions or disparate model spaces inside a single collection corrupts vector similarity calculations. The vector storage layer explicitly verifies that the active collection's vector dimensions match the current embedding adapter's dimensions. If a mismatch is detected (e.g., trying to query a 384-dimensional collection with a 768-dimensional model), the system raises a `VECTOR_DIMENSION_MISMATCH` error requiring a clean re-indexing cycle rather than returning corrupted nearest neighbors.

---

## 3. Vector Database Architecture (Qdrant)

### 3.1 Selection Rationale and Comparison

| Evaluation Metric | Qdrant (Selected) | ChromaDB | Pinecone |
|---|---|---|---|
| **Deployment Flexibility** | Local embedded (`path="data/qdrant"`), in-memory (`:memory:`), or server (`docker-compose.yml`) | Embedded local disk or server | Cloud SaaS only (violates `OQ-06`) |
| **Metadata Filtering** | Rich payload filtering (`MatchValue`, `MatchAny`, `IsNullCondition`, range queries) | Basic `where` filter; limited nested logical grouping | Good, but SaaS-dependent |
| **Point ID Stability** | Standard UUIDs and unsigned integers supported via deterministic UUIDv5 | Custom strings | Custom strings |
| **Concurrency & Safety** | High-throughput Rust engine; process-safe | SQLite locking constraints under multi-worker writes | Managed |
| **Test Ergonomics** | Zero-dependency `:memory:` mode for lightning-fast unit tests | SQLite in-memory | Requires remote mock or live account |

### 3.2 Collection Configuration Schema

- **Collection Name:** `siteshield_chunks` (configurable via `VECTOR_DB_COLLECTION`)
- **Distance Metric:** `Cosine` (`models.Distance.COSINE`)
- **Vector Dimension:** Matched to active model (768 for BGE-base, 384 for BGE-small, 1536 for OpenAI small)

### 3.3 Payload Schema and Inverted Indexes

To ensure fast metadata pre-filtering without full-table scans, the collection initializes dedicated payload schema indexes:

| Field | Index Type | Purpose / Query Scenarios |
|---|---|---|
| `doc_id` | `KEYWORD` | Scoping retrieval to a single document; targeted point deletion on update |
| `doc_type` | `KEYWORD` | Filtering by `code`, `spec`, `report`, or `safety_manual` |
| `project_id` | `KEYWORD` | Construction project isolation (e.g. `project_id == "#104"`) |
| `jurisdiction` | `KEYWORD` | Regulatory jurisdiction filtering (e.g. `IN-KA`, `US-IBC`, `GLOBAL`) |
| `status` | `KEYWORD` | Status filtering (`active`, `superseded`, `draft`) |
| `content_type` | `KEYWORD` | Filtering tabular vs narrative evidence (`table`, `prose`, `list`) |
| `effective_timestamp` | `INTEGER` | Numeric range queries for regulatory effective dates and revision precedence |

### 3.4 Chunk Point Provenance Payload

Every point stored in Qdrant contains the following verified metadata attributes:

```json
{
  "id": "e6f8841a-9694-55f6-a320-b467ef8497cb",
  "vector": [0.0341, -0.0125, "..."],
  "payload": {
    "chunk_id": "chk_doc_8a12f_0",
    "doc_id": "doc_8a12f",
    "doc_title": "Site Safety Manual - Excavation Protocols",
    "doc_type": "safety_manual",
    "jurisdiction": "IN-KA",
    "project_id": "#104",
    "standard_code": "IS 3764:1992",
    "version": "Rev 2.1",
    "publication_date": "2024-01-15",
    "effective_date": "2024-02-01",
    "effective_timestamp": 1706745600,
    "status": "active",
    "confidentiality_tier": "internal",
    "source_filename": "excavation_protocols.pdf",
    "sha256_checksum": "a79c3b84f...",
    "chunk_index": 0,
    "page_start": 3,
    "page_end": 4,
    "printed_page_label": "Sheet S-03",
    "section_id": "4.2.1",
    "section_path": ["4. Earthwork", "4.2 Shoring", "4.2.1 Trench Safety"],
    "content_type": "prose",
    "extraction_method": "native",
    "ocr_confidence": null,
    "char_start": 412,
    "char_end": 1056,
    "token_estimate": 142,
    "text_for_embedding": "[Doc: Site Safety Manual | Section: 4.2.1 Trench Safety] Trenches deeper than 1.5 m require shoring...",
    "text_verbatim": "Trenches deeper than 1.5 m require shoring conforming to IS 3764.",
    "indexed_at": "2026-11-17T16:05:00.000000Z"
  }
}
```

---

## 4. Repeatable Indexing and Synchronization Pipeline

### 4.1 Ingestion-to-Vector Lifecycle

The `VectorIndexer` ([`backend/app/retrieval/indexer.py`](file:///home/abhinivesh/Downloads/siteshield_ai/backend/app/retrieval/indexer.py)) coordinates the synchronization of document chunks with Qdrant based on document state:

```
                  Document Ingestion & Indexing Flow
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Validate & Compute SHA-256 Checksum                                  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
                   [ Check IngestionStore Checksum ]
                 /                                   \
      (Checksum Matches)                      (Checksum Differs)
               /                                       \
              ▼                                         ▼
   [ Match Manifest Metadata ]                 [ Extract & Chunk ]
     /                   \                              │
 (Identical)          (Changed)                         │
     │                    │                             ▼
     ▼                    ▼                [ Check Existing Identity ]
status: "unchanged"   status: "updated"          /                    \
  • Skip embedding     • Delete old points  (New Document)      (Existing Doc)
  • Skip Qdrant write  • Re-embed & upsert       │                     │
  • Return 200 OK      • Return 201 Created      ▼                     ▼
                                           status: "ingested"    status: "updated"
                                            • Embed & upsert      • Delete old points
                                            • Return 201          • Embed & upsert
```

### 4.2 Idempotency and Deduplication Guarantees

1. **Deterministic Point IDs:** Point IDs in Qdrant are generated as deterministic UUIDv5 strings derived from the stable `chunk_id` (`uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id)`). This guarantees that re-indexing identical chunks updates existing records in place rather than creating duplicate points.
2. **Atomic Replacement on Update:** When a document with an existing identity (`source_filename`, `doc_type`, `project_id`) is updated, `vector_store.delete_by_doc_id(doc_id)` purges all existing points from Qdrant before the new chunk set is indexed. This ensures zero orphaned vectors even when a revised document has fewer chunks than its predecessor.
3. **Repeat Ingestion Bypass:** When an identical file is uploaded without changes, `IngestionService` identifies the matching SHA-256 checksum, sets `vectors_indexed = 0`, and skips embedding inference and vector database writes entirely.

---

## 5. Metadata Scoping and Pre-Filtering Logic

Construction engineers need to retrieve project-specific requirements alongside general governing building codes. The Qdrant search implementation supports compound scoping filters:

```python
# Project Scoping Rule:
# Return chunks matching project_id == "#104"
# OR general building codes where project_id IS NULL and doc_type in ['code', 'safety_manual']
project_scope = models.Filter(
    should=[
        models.FieldCondition(key="project_id", match=models.MatchValue(value="#104")),
        models.Filter(
            must=[
                models.IsNullCondition(is_null=models.PayloadField(key="project_id")),
                models.FieldCondition(key="doc_type", match=models.MatchAny(any=["code", "safety_manual"])),
            ]
        ),
    ]
)
```

This guarantees that project queries never miss baseline building codes while strictly isolating proprietary specifications across different projects.

---

## 6. Error Handling Strategy

| Failure Scenario | Detected At | Raised Exception | HTTP Code | Error Code | Mitigation / Behavior |
|---|---|---|---|---|---|
| **Missing OpenAI API Key** | Adapter initialization | `ConfigurationError` | 500 | `MISSING_EMBEDDING_API_KEY` | Fails fast; never logs secret keys |
| **OpenAI Auth Failure (401/403)** | API call | `EmbeddingProviderError` | 401 | `EMBEDDING_AUTH_ERROR` | Surfaces authentication issue to operator |
| **OpenAI Rate Limit (429)** | API call | `EmbeddingProviderError` | 429 | `EMBEDDING_RATE_LIMITED` | Backoff and retry telemetry |
| **OpenAI Service / Network Down** | HTTP transport | `EmbeddingProviderError` | 503 | `EMBEDDING_NETWORK_ERROR` | Clean degradation without crashing ASGI server |
| **FastEmbed Model Corrupt / Missing** | Model loading | `EmbeddingProviderError` | 503 | `EMBEDDING_INIT_FAILED` | Descriptive download / cache repair error |
| **Dimension Mismatch** | Collection validation | `VectorStoreError` | 503 | `VECTOR_DIMENSION_MISMATCH` | Prohibits index corruption; requires re-index |
| **Qdrant Unreachable** | Connection attempt | `VectorStoreError` | 503 | `VECTOR_STORE_CONNECTION_FAILED` | Wraps connection refusal cleanly |
| **Empty Chunk / Query Text** | Input validation | `ValidationAppError` | 422 | `EMPTY_QUERY_TEXT` | Rejects blank query before vector search |

---

## 7. Empirical Test Verification

The embedding and vector storage layer is verified across 48 automated tests in `backend/tests/`:

- **Unit Tests (`tests/unit/test_embeddings.py` — 7 tests):**
  - Dimension consistency and vector normalization ($\|v\| \approx 1.0$)
  - Deterministic hashing and reproducibility across multiple calls
  - FastEmbed local inference on CPU
  - OpenAI adapter authentication, rate-limiting, and network error handling
  - Settings-driven provider factory resolution
- **Unit Tests (`tests/unit/test_vector_store.py` — 8 tests):**
  - Collection creation, distance metrics, and dimension mismatch protection
  - Provenance payload preservation across all metadata fields
  - Idempotent point upserting with UUIDv5 point IDs
  - Isolated point deletion by `doc_id`
  - Multi-attribute pre-filtering and project scoping rules
  - Empty collection searches and graceful edge cases
- **Integration Tests (`tests/integration/test_vector_indexing.py` — 3 tests):**
  - End-to-end document ingestion -> embedding -> Qdrant vector persistence
  - Repeat upload unchanged detection (`vectors_indexed == 0`)
  - Document revision update with complete stale vector purge
  - Multi-document coexistence and project scoping
  - FastAPI HTTP endpoint integration (`POST /documents/ingest` returning `vectors_indexed`)
