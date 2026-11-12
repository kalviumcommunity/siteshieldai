# Document Ingestion Pipeline — Verification & Extraction Evidence

**Stage:** Gate 4 — Document Ingestion, Cleaning, Table Preservation & Hierarchical Chunking  
**Embeddings Generated:** None (strictly excluded per current stage scope)  
**Permitted Sample Documents Tested:**
1. [`SiteShield_AI_PRD.pdf`](file:///home/abhinivesh/Downloads/siteshield_ai/SiteShield_AI_PRD.pdf) (5-page digital PDF)
2. [`README.md`](file:///home/abhinivesh/Downloads/siteshield_ai/README.md) (506-line Markdown with 8 tables)
3. [`docs/DOCUMENT_CORPUS_ANALYSIS.md`](file:///home/abhinivesh/Downloads/siteshield_ai/docs/DOCUMENT_CORPUS_ANALYSIS.md) (253-line Markdown with 8 tables)

---

## 1. Repeatability & Ingestion Summary (Observed CLI Runs)

Executed via [`scripts/ingest_documents.py`](file:///home/abhinivesh/Downloads/siteshield_ai/scripts/ingest_documents.py) storing manifests and chunks in local SQLite (`data/processed/siteshield_ingestion.db`):

| Run | Source File | `doc_id` | Status | `unchanged` | Pages (`Native / OCR`) | Chunks | Tables | `\u200b` Remaining |
|---|---|---|---|---|---|---|---|---|
| 1 | `SiteShield_AI_PRD.pdf` | `doc_a74ca05485d8` | `ingested` | `false` | `5` (`5 / 0`) | `18` | `5` | `0` |
| 2 (Repeat) | `SiteShield_AI_PRD.pdf` | `doc_a74ca05485d8` | `unchanged` | `true` | `5` (`5 / 0`) | `18` | `5` | `0` |
| 3 | `README.md` | `doc_63d9519cce5e` | `ingested` | `false` | `1` (`1 / 0`) | `39` | `8` | `0` |
| 4 | `DOCUMENT_CORPUS_ANALYSIS.md` | `doc_ac9cd5a3b277` | `ingested` | `false` | `1` (`1 / 0`) | `32` | `8` | `0` |

- **SHA-256 Checksum (`SiteShield_AI_PRD.pdf`):** `4c2d2cf295f9757af7058acf91db64e366cdf57a204812669a9b27c50b49f768`
- **Repeat-Run Behavior:** Re-running ingestion with identical bytes and manifest short-circuited (`status: "unchanged"`, `unchanged: true`) with warning `"Document unchanged (matching SHA-256 checksum); skipped re-ingestion."` and created zero duplicate rows.

---

## 2. Verified Extraction, Cleaning & Chunking Evidence (`SiteShield_AI_PRD.pdf`)

### 2.1 Zero-Width Space Removal & Regulatory Symbol Preservation
- Prior corpus analysis found `27` `U+200B` (`\u200b`) characters in the raw PDF text stream.
- Verified across all `18` persisted chunks of `SiteShield_AI_PRD.pdf` (and all chunks of `README.md` and `DOCUMENT_CORPUS_ANALYSIS.md`): **`zwsp_count = 0`**.
- Regulatory/metric symbols such as `≥ 85% top-3 recall` (Chunk `5`) and `→` (Chunk `11`) were preserved intact.

### 2.2 Cross-Page Section & List Preservation (Page 1 → Page 2)
Chunk `4` (`chk_1a56fdf34299b812`) preserved Section `2.1 Primary Objectives` across the Page 1 → Page 2 boundary without severing the 3rd bullet from its parent heading:

```json
{
  "chunk_id": "chk_1a56fdf34299b812",
  "doc_id": "doc_a74ca05485d8",
  "chunk_index": 4,
  "page_start": 1,
  "page_end": 2,
  "section_id": "2.1",
  "section_path": [
    "2. Objectives & Success Metrics",
    "2.1 Primary Objectives"
  ],
  "content_type": "list",
  "extraction_method": "native",
  "token_estimate": 98
}
```

### 2.3 Cross-Page Table Stitching & Blank-Key Continuation (Page 4 → Page 5)
The `6. Milestones & Sprint Execution Plan` table physically splits across Page 4 and Page 5 (`Week 5` row ends with `"Accuracy benchmarking against test queries,"` on Page 4, followed by a repeated header row and blank leading key cells on Page 5). The ingestion stitcher merged both fragments into **one** intact Markdown table chunk (`chk_2446f3ea2f3395b4`):

```json
{
  "chunk_id": "chk_2446f3ea2f3395b4",
  "doc_id": "doc_a74ca05485d8",
  "chunk_index": 16,
  "page_start": 4,
  "page_end": 5,
  "section_id": "6",
  "section_path": [
    "6. Milestones & Sprint Execution Plan"
  ],
  "content_type": "table",
  "extraction_method": "native",
  "token_estimate": 209
}
```

Verified `text_verbatim` for `Week 5` inside `chk_2446f3ea2f3395b4`:
```markdown
| Week 5 | Evaluation, Hardening & Final Presentation | Accuracy benchmarking against test queries, performance optimization, final viva & product submission. |
```

---

## 3. Malformed, Empty, Encrypted & Scanned Edge Cases Verified (`pytest`)

- **Unsupported extension (`.exe`):** Rejected with `422` (`UNSUPPORTED_DOCUMENT_FORMAT`).
- **Empty (`0`-byte) & whitespace-only files / blank `0`-text PDFs:** Rejected with `422` (`EMPTY_DOCUMENT`).
- **Oversized uploads (`> MAX_UPLOAD_SIZE_MB`):** Rejected with `413` (`PAYLOAD_TOO_LARGE`).
- **Corrupted PDF / bad magic header / null bytes / invalid UTF-8:** Rejected with `422` (`MALFORMED_DOCUMENT`).
- **Password-protected PDF:** Rejected with `422` (`ENCRYPTED_DOCUMENT`).
- **Duplicate content under a different filename:** Rejected with `409` (`DUPLICATE_DOCUMENT_CONTENT`).
- **Image-only PDF page triage:** Routed to `ExtractionMethod.OCR` (`ocr_pages = 1`) via the pluggable `ocr_fn` hook in integration testing (preserving `ocr_confidence`), or emits an explicit unconfigured-OCR page warning when no OCR engine is attached.

