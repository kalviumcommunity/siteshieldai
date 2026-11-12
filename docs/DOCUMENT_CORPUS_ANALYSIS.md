# Document Corpus Analysis — Site Shield AI

**Status:** Initial Corpus Inspection Complete (Pending Real Construction Corpus & Strategy Review)  
**Scope:** Read-only inspection of all files currently present in `/home/abhinivesh/Downloads/siteshield_ai`  
**Original Files Modified or Deleted:** None

---

## Executive Summary

**Critical Finding:** The repository currently contains **zero (`0`) actual construction compliance documents** (no building codes, no project specifications, no safety manuals, and no site inspection reports). No `data/` directory exists on disk (`data/raw/` is listed in `.gitignore` and not yet populated).

The only PDF present in the repository is [`SiteShield AI (PRD) Team Fire.pdf`](file:///home/abhinivesh/Downloads/siteshield_ai/SiteShield%20AI%20%28PRD%29%20Team%20Fire.pdf), which is a **5-page software Product Requirements Document (PRD)** for building Site Shield AI — not a construction regulation, engineering specification, or inspection report. All 5 other files in the repository are software planning, governance, and configuration files.

Consequently, while we can empirically verify extraction behavior and formatting challenges on the 5-page digital PRD PDF (including stream-order table scrambling, cross-page split tables, minimal cell padding, and `U+200B` zero-width space pollution), **ingestion parsers, OCR thresholds, and chunking parameters cannot be finalized until representative construction documents are supplied.**

---

## 1. File Formats and Document Counts

### 1.1 Repository File Inventory (Excluding `.git/`)

Total files on disk: **6 files** across **4 file types** (`168,093` bytes / ~`164.2 KiB` total).

| # | Relative Path | Format | Size (Bytes) | Extent | Git Status (`initialsetup`) | Domain Role |
|---|---|---|---|---|---|---|
| 1 | [`SiteShield AI (PRD) Team Fire.pdf`](file:///home/abhinivesh/Downloads/siteshield_ai/SiteShield%20AI%20%28PRD%29%20Team%20Fire.pdf) | PDF (`.pdf`, v1.4) | `141,598` | 5 pages, 1,136 words | Untracked | Software Product Requirements Document (PRD) |
| 2 | [`README.md`](file:///home/abhinivesh/Downloads/siteshield_ai/README.md) | Markdown (`.md`) | `17,186` | 506 lines, 8 tables | Tracked (`a7e9c75`) | Project overview, proposed architecture, roadmap, Git workflow |
| 3 | [`docs/OPEN_QUESTIONS.md`](file:///home/abhinivesh/Downloads/siteshield_ai/docs/OPEN_QUESTIONS.md) | Markdown (`.md`) | `6,937` | 61 lines, 5 tables | Untracked | Unresolved requirements & Gate 1–10 decision tracker (`OQ-01`–`OQ-20`) |
| 4 | [`.gitignore`](file:///home/abhinivesh/Downloads/siteshield_ai/.gitignore) | Git config | `981` | 88 lines | Untracked | Ignore rules for secrets, Python, Node/Next.js, `data/raw/`, vector DBs |
| 5 | [`.env.example`](file:///home/abhinivesh/Downloads/siteshield_ai/.env.example) | Dotenv template | `759` | 35 lines | Untracked | Environment configuration placeholders |
| 6 | [`.github/PULL_REQUEST_TEMPLATE.md`](file:///home/abhinivesh/Downloads/siteshield_ai/.github/PULL_REQUEST_TEMPLATE.md) | Markdown (`.md`) | `632` | 31 lines | Untracked | Pull Request checklist and verification template |

*(Note: `docs/DOCUMENT_CORPUS_ANALYSIS.md` is added as the output of this analysis.)*

### 1.2 Construction Compliance Corpus Count

| Expected Source Category | PDF | DOCX | XLSX / CSV | TXT / MD | Drawings / Images | Total |
|---|---|---|---|---|---|---|
| Building Codes | 0 | 0 | 0 | 0 | 0 | **0** |
| Project Specifications | 0 | 0 | 0 | 0 | 0 | **0** |
| Inspection Reports | 0 | 0 | 0 | 0 | 0 | **0** |
| Safety Manuals / Guidelines | 0 | 0 | 0 | 0 | 0 | **0** |
| **Total Construction Corpus** | **0** | **0** | **0** | **0** | **0** | **0** |

---

## 2. Document Categories

### 2.1 Categories Actually Present in the Repository

1. **Software Product Requirements Document (`.pdf`):** `SiteShield AI (PRD) Team Fire.pdf` — defines problem statement, target persona, KPIs, feature breakdown, user stories, high-level RAG architecture, edge cases, sprint plan, and team roles.
2. **Engineering & Governance Documentation (`.md`):** `README.md`, `docs/OPEN_QUESTIONS.md`, `.github/PULL_REQUEST_TEMPLATE.md`.
3. **Repository Configuration (`.gitignore`, `.env.example`):** ignore rules and environment variable templates.

### 2.2 Planned Construction Categories (Referenced, Not Present)

Cross-referencing the PRD, `README.md`, and `docs/OPEN_QUESTIONS.md` reveals slight variation in category terminology:

- **PRD §3.1 (Feature 1):** `Code vs. Spec vs. Report` (`national/regional building codes`, `project specifications`, `past inspection reports`).
- **`README.md` §1:** `building codes, project specifications, safety guidelines, and inspection reports`.
- **`docs/OPEN_QUESTIONS.md` (`OQ-01`):** `building codes, project specs, inspection reports, safety manuals`.

---

## 3. Available Project Identifiers and Jurisdictions

### 3.1 Verified Software-Project Identifiers (Metadata of This Codebase)

- **Product / Repo Name:** `Site Shield AI` (`README.md`, `.env.example`) / `SiteShield AI` (PDF title/filename) / `kalviumcommunity/siteshieldai` (`origin` Git remote; `OQ-20`).
- **Team / Cohort:** `Team Fire` (`Team 02` in `README.md` §13), `Kalvium Squad 76` (`README.md` §13; `Squad 76` in PRD §7).
- **Sprint / Academic Context:** `Sem 5 — Sprint 2 (AI Application Development with RAG)` (PRD p. 1); `Sprint 2` (`README.md` §13).
- **Team Members Listed:** `Aakash J`, `Jandy Y`, `Abhinivesh` (PRD p. 1, `README.md` §13; Git commit `a7e9c75` author `Abhinivesh S <abhisa8888@gmail.com>`).

### 3.2 Construction Project Identifiers & Regulatory Jurisdictions

- **Actual Construction Project IDs:** **None.** Zero real construction projects exist in the corpus.
  - *Illustrative Example Only:* `Project #104` appears once in PRD §3.2 (*User Stories*, p. 3) inside a sample Safety Inspector query (*"Check past inspection reports for Project #104 regarding scaffolding violations"*). This is a synthetic user-story example, not an active project document identifier.
- **Actual Jurisdictions & Standard-Setting Bodies:** **None specified.** Neither `SiteShield AI (PRD) Team Fire.pdf`, `README.md`, nor `docs/OPEN_QUESTIONS.md` names a country, state/province, municipality, or regulatory standard (e.g., IBC, OSHA, NBC India, IS codes, Eurocodes, BS). PRD §3.1 mentions only generic `"national/regional building codes"` and `"Region/Jurisdiction"`.

---

## 4. Publication and Revision Dates

| Artifact | Internal Document / PDF Date Metadata | Dates in Body Text | Git Commit Timestamp | Filesystem Timestamps (Non-Authoritative) |
|---|---|---|---|---|
| `SiteShield AI (PRD) Team Fire.pdf` | **None** (`/CreationDate` absent, `/ModDate` absent, XMP `/Metadata` stream absent) | **None** (only relative sprint duration `"Sem 5 — Sprint 2"` and `"5 weeks (approx. 25 working days)"` in §6) | Untracked | `mtime`: `2026-11-02 14:30:40 +0530`<br>`ctime`: `2026-11-12 10:17:34 +0530` |
| `README.md` | N/A | **None** (notes `"Sprint 2"` and 5-week roadmap) | `2026-11-11 22:28:11 +0530` (`a7e9c75`) | `mtime`: `2026-11-12 10:16:32 +0530` |
| `docs/OPEN_QUESTIONS.md` | N/A | **None** (notes `"Sprint 2"`) | Untracked | `mtime`: `2026-11-12 10:04:44 +0530` |
| `.gitignore`, `.env.example`, `.github/PULL_REQUEST_TEMPLATE.md` | N/A | **None** | Untracked | `mtime`: `2026-11-12 10:04:44 +0530` |

**Key Observation:** Zero regulatory publication dates, effective dates, or revision numbers exist anywhere in the repository. Moreover, reliance on filesystem `mtime`/`ctime` for `SiteShield AI (PRD) Team Fire.pdf` demonstrates why filesystem timestamps cannot serve as document `revision_date` or `effective_date` metadata (the file copy/touch timestamp differs by 10 days from its download `mtime`).

---

## 5. PDF Text-Based vs. Scanned Inspection

Inspected `SiteShield AI (PRD) Team Fire.pdf` locally using `pdfinfo`, `pdffonts`, `pdfimages`, `pdftotext`, `pdftohtml -xml`, `pdftoppm`, and raw PDF stream inspection:

- **Classification:** **100% digital, text-based, Tagged PDF** (NOT scanned).
- **Technical Profile (`pdfinfo` & raw PDF inspection):**
  - **PDF Version:** `1.4` (`Encrypted: no`, `Optimized: no`, `Form: none`, `JavaScript: no`)
  - **Producer:** `Skia/PDF m158 Google Docs Renderer`
  - **Page Count & Dimensions:** `5` pages, `612 x 792 pts` (US Letter), rotation `0`
  - **Accessibility / Structure:** `Tagged: yes` (`/StructTreeRoot` and `/MarkInfo` present); document outline/bookmarks present (`/Outlines` with 25 entries)
  - **Embedded Attachments (`pdfdetach -list`):** `0` embedded files; `0` annotations (`/Type /Annot`)
  - **Embedded Images (`pdfimages -list` / `/XObject` count):** **`0` images (`0` `/XObject` objects)** — no scanned raster pages or figures
- **Embedded Fonts (`pdffonts`):** All 3 fonts are embedded subsetted TrueType CID fonts (`Identity-H` encoding) with `ToUnicode` mappings (`uni = yes`), guaranteeing lossless character extraction:
  - `AAAAAA+Arial-BoldMT` (CID TrueType, embedded, subset, Unicode)
  - `BAAAAA+ArialMT` (CID TrueType, embedded, subset, Unicode)
  - `CAAAAA+Arial-ItalicMT` (CID TrueType, embedded, subset, Unicode)
- **Extractable Text Volume (`pdftotext`):** `8,482` characters / `1,136` whitespace-delimited words across all 5 pages:
  - Page 1: `2,005` chars (`32` non-empty lines)
  - Page 2: `1,884` chars (`44` non-empty lines)
  - Page 3: `1,933` chars (`76` non-empty lines)
  - Page 4: `1,922` chars (`65` non-empty lines)
  - Page 5: `738` chars (`17` non-empty lines)

*(Caveat: Although the sole existing PDF requires no OCR, PRD §5.2 explicitly anticipates "Poorly scanned PDF reports or tabular specifications" in the future construction corpus.)*

---

## 6. Structural Elements: Tables, Headers, Footers, and Numbered Clauses

### 6.1 `SiteShield AI (PRD) Team Fire.pdf`

| Element | Present? | Verified Details & Locations |
|---|---|---|
| **Tables** | **Yes (5 bordered grid tables)** | 1. **Page 2 — `2.2 Success Metrics & KPIs`:** 3 cols × 5 rows (`Metric`, `Target Benchmark`, `Evaluation Method`).<br>2. **Page 3 — `3.2 User Stories`:** 4 cols × 4 rows (`User Role`, `I Want To...`, `So That...`, `Acceptance Criteria`).<br>3. **Page 3 — `4.2 Proposed Technology Stack`:** 3 cols × 7 rows (`Component`, `Technology Options`, `Purpose`).<br>4. **Page 4 — `5.2 Edge Cases & Mitigation Strategies`:** 3 cols × 4 rows (`Edge Case`, `Risk Level`, `Mitigation Strategy`).<br>5. **Pages 4–5 — `6. Milestones & Sprint Execution Plan`:** 3 cols (`Phase / Week`, `Focus Area`, `Key Deliverables`) split across Page 4 (header + Weeks 1–5 partial) and Page 5 (repeated header + blank-key continuation row for Week 5). |
| **Running Page Headers** | **No** | Visual inspection of Pages 1–5 (`prd_page-1.png`–`5.png`) and XML coordinates confirm **no running page header**. Every page starts directly with body, list, section heading, or table content around `top="109"`–`128"` (in 1188-unit XML coordinates). |
| **Running Page Footers & Page Numbers** | **No** | Visual inspection and XML coordinates confirm **no running page footer and no printed page numbers** on any page. |
| **Numbered Clauses / Section Hierarchy** | **Yes (2-level PRD sections; 0 construction clauses)** | Top-level sections `1.` through `7.`; two-level subsections `1.1`–`1.3`, `2.1`–`2.2`, `3.1`–`3.2`, `4.1`–`4.2`, `5.1`–`5.2`. Section `3.1` uses named sub-blocks (`Feature 1:`–`Feature 4:`) rather than `3.1.1`–`3.1.4`. Sections `6` and `7` have no subsections. Section `4.1` contains a 3-item numbered list (`1.`–`3.`). **No real construction code clauses exist** (`Section 4.2.1` in `3.1` is an illustrative example only). |

### 6.2 Repository Markdown Files

- **`README.md`:** Numbered sections `1.` through `17.`, **8 Markdown tables** (lines 40, 143, 326, 353, 374, 388, 435, 458), 1 ASCII pipeline diagram (lines 56–103), 1 ASCII tree diagram (lines 163–215), and a numbered workflow list (`1.`–`10.` in §14).
- **`docs/OPEN_QUESTIONS.md`:** Numbered sections `1.` through `5.`, **5 Markdown tables** (`OQ-01`–`OQ-20`).

---

## 7. Missing or Inconsistent Metadata

### 7.1 Missing Metadata

1. **Zero Construction Domain Corpus & Metadata:** All required RAG filter fields specified in PRD §3.1 (`Document type`, `Region/Jurisdiction`, `Revision Date`, `Effective Date`, `Project ID`, `Version`) have no real document source values because the construction corpus does not yet exist in the repo.
2. **Incomplete PDF `/Info` & XMP Metadata in `SiteShield AI (PRD) Team Fire.pdf`:**
   - Populated: `Title` (`SiteShield AI (PRD) Team Fire`) and `Producer` (`Skia/PDF m158 Google Docs Renderer`).
   - **Missing:** `Author`, `Subject`, `Keywords`, `Creator`, `CreationDate`, `ModDate`, and XMP `Metadata Stream`.
3. **Missing In-Document Control Metadata in PRD:** No document ID, version (`v1.0`), approval status (`Draft` vs `Approved`), revision log, effective date, or printed page numbers appear on any of the 5 pages.

### 7.2 Verified Inconsistencies Across Existing Repository Files

| Topic | `SiteShield AI (PRD) Team Fire.pdf` | `README.md` / `docs/OPEN_QUESTIONS.md` | Impact on Engineering & Ingestion |
|---|---|---|---|
| **Product Naming** | `SiteShield AI (PRD) Team Fire` / `AI-Powered Site Inspection & Building Code Compliance Assistant` | `Site Shield AI` (two words) / `AI-Powered Construction Compliance Assistant` | Canonical product & document title normalization needed. |
| **Document Taxonomy** | 3 types: `Code vs. Spec vs. Report` (§3.1) | `README.md` §1 lists 4 (`building codes, project specifications, safety guidelines, inspection reports`); `OQ-01` lists `safety manuals` | `document_type` enum schema must standardize 3 vs 4 categories. |
| **PRD Path & Format** | Untracked root PDF: `SiteShield AI (PRD) Team Fire.pdf` (spaces & parentheses in filename) | `README.md` §7 & §15 reference `docs/PRD.md` (does not exist) | Filename/path mismatch; spaces/parentheses also complicate CLI/URL handling. |
| **Python Version** | `Python 3.10+` (§4.2) | `README.md` §8 specifies `Python 3.11+`; `OQ-14` notes local host runs `Python 3.14.4` | Needs pinned Python version (`3.11` or `3.12`) for PDF/vector DB wheels. |
| **Orchestration & Parsing Stack** | `LangChain / LlamaIndex` (§4.2); `pdfplumber or Unstructured` + OCR (§5.2) | `README.md` §6 lists `PyMuPDF / pdfplumber` without LangChain/LlamaIndex; `OQ-13` open | Ingestion & orchestration architecture decision unresolved. |
| **Vector Database Options** | `Chroma / Qdrant / Pinecone` (§4.2) | `README.md` §6 lists `ChromaDB / Qdrant` (drops Pinecone); `OQ-12` open | Metadata filtering contract depends on selected vector store. |
| **Team Roles vs Headcount** | Lists 3 members (`Aakash J, Jandy Y, Abhinivesh`) on p. 1, but defines **5** unmapped roles in §7 | `README.md` §13 defines **3** member-mapped responsibilities (`OQ-19` open) | Ownership mapping for Data/Pipeline vs Retrieval/Frontend needs confirmation. |
| **Retrieval Metric Naming** | §2.2 table row is named `Retrieval Precision @ Top-K` with target `≥ 85% top-3 recall` | `README.md` §11 separates `Precision@K` and `Recall@K` | Metric definitions conflated in PRD; evaluation spec must separate Precision@K and Recall@K. |
| **Thresholds & Targets** | §2.2 sets `< 3.0s` latency, `100%` cited claims, `0%` missing-doc hallucination; §5.1 requires min similarity threshold | `README.md` §11 states targets *"will be finalized after establishing a baseline"* (`OQ-16` open) | Requires reconciled acceptance criteria before Gate 8 benchmarking. |

---

## 8. Extraction Challenges

### 8.1 Directly Observed in `SiteShield AI (PRD) Team Fire.pdf`

1. **Stream-Order Table Column Scrambling (`pdftotext` without layout / naive PDF text loaders):**
   - *Verified Example (Page 3, `3.2 User Stories`):* Running standard `pdftotext` emits Column 1 vertically in full (`User Role`, `Site Engineer`, `Safety Inspector`, `Field Tech`) **before** emitting `I Want To...`, `So That...`, `Acceptance Criteria`, and the multi-line cell values. The same vertical column grouping scrambles `2.2 Success Metrics & KPIs` (Page 2), `4.2 Proposed Technology Stack` (Page 3), and `5.2 Edge Cases & Mitigation Strategies` (Page 4).
   - *Impact:* Naive text extraction destroys row-to-column associations, producing corrupted chunks (e.g., detaching `≥ 85% top-3 recall` or `< 3.0 seconds (e2e)` from their metric names).
2. **Cross-Page Split Table with Repeated Header & Orphan Blank-Key Row:**
   - *Verified Example (Pages 4–5, `6. Milestones & Sprint Execution Plan`):* The `Week 5` row splits mid-sentence across the page break:
     - Bottom of Page 4: `Week 5 | Evaluation, Hardening & Final Presentation | Accuracy benchmarking against test queries,`
     - Top of Page 5: Repeats the full table header (`Phase / Week | Focus Area | Key Deliverables`), followed by a single continuation row whose first two cells are **empty** and whose third cell contains `performance optimization, final viva & product submission.`
   - *Impact:* Page-isolated table extractors will produce two disjoint tables — leaving Page 4's `Week 5` truncated at a comma and creating a malformed Page 5 row with null `Phase / Week` and `Focus Area` keys.
3. **Minimal Horizontal Cell Padding Near Vertical Grid Borders:**
   - *Verified Example (Pages 3–4, rendered PNG inspection):* Text in dense table cells touches or sits immediately adjacent to vertical grid lines (e.g., `I Want To...`, `Field Tech`, `OpenAI text-embedding-3-small`, `Out-of-scope compliance query`).
   - *Impact:* Whitespace-gap table detectors can merge adjacent columns; vector border-line detection (e.g., `pdfplumber` explicit lines / `PyMuPDF` `find_tables()`) is required rather than text-gap heuristics.
4. **Zero-Width Space (`U+200B`) Pollution After List Markers:**
   - *Verified Example (Pages 1–5):* Direct inspection of `pdftotext` output reveals **27 occurrences of `\u200b` (`ZERO WIDTH SPACE`)** across all 5 pages immediately following bullet glyphs (`●\u200b`) and numbered list items (`1.\u200b`, `2.\u200b`, `3.\u200b`) — an artifact of Google Docs Skia/PDF export.
   - *Impact:* Invisible `\u200b` characters corrupt regex clause detection (`^\d+\.`), break exact substring/keyword matching, and split subword tokens inconsistently.
5. **Cross-Page List Continuation Without Repeated Subheading:**
   - *Verified Example (Page 1 → Page 2):* Section `2.1 Primary Objectives` contains 2 bullets at the bottom of Page 1 and places its 3rd bullet (`● Enforce strict anti-hallucination guardrails...`) at the top of Page 2 without repeating the `2.1` header.
   - *Impact:* Page-level chunkers sever the 3rd bullet from its parent section `2.1`, losing hierarchical context for citations.
6. **Absent Document Dates and Printed Page Numbers:**
   - Because `/CreationDate`, `/ModDate`, and printed footer page numbers are absent, citations must derive `page_number` strictly from the 1-based PDF page index, and temporal/version metadata cannot be automatically trusted from PDF header dictionaries or OS timestamps.

### 8.2 Anticipated Challenges for Pending Construction Corpus (Unverified Until Samples Arrive)

- **Scanned or skewed inspection reports & legacy codes** needing OCR (`OQ-02`, PRD §5.2).
- **Multi-column regulatory layouts** (two-column building codes where naive reading order interleaves columns).
- **Complex engineering tables** (merged headers, footnotes, load/dimension schedules, units like `mm`, `kN/m²`, `°C`, `≥`).
- **Deep hierarchical clause numbering** (`4.2.1(a)(ii)`, `Table 4.1`, `Annex B`) and cross-references (`"Subject to Clause 5.3.2"`).
- **Version supersession conflicts** between historical site inspection reports and amended building codes (`OQ-05`, `OQ-09`).

---

## 9. Recommended Document-Processing Strategy (Proposal for Review)

Because **no real construction documents exist in the repository yet**, the team should **not** hard-code production parsers against synthetic assumptions. Instead, follow a two-phase, evidence-first strategy:

### Phase 1: Corpus Intake & Gate 2 Preconditions (Immediate Next Step)
1. **Collect Representative Raw Corpus into `data/raw/`** (already gitignored in `.gitignore`, keeping confidential files out of Git and out of external cloud uploads):
   - Target at least 1–2 real/approved samples from each planned category (`Building Code`, `Project Specification`, `Inspection Report`).
2. **Establish a Manifest Schema (`corpus_manifest.yaml` or `metadata.json` outside Git if sensitive):**
   - For every source document ingested, record explicit, human-verified metadata that PDF headers often omit:
     - `doc_id` (stable slug), `title`, `doc_type` (`code | spec | report | safety_manual`), `jurisdiction`, `project_id` (nullable for codes), `version` / `revision_number`, `publication_date`, `effective_date`, `supersedes_doc_id` (nullable), `confidentiality_tier` (`public | internal | restricted`).
3. **Confidentiality / Data-Residency Gate (`OQ-06`):**
   - Confirm whether any construction documents are proprietary or confidential **before** sending extracted text to external embedding or LLM APIs; if restricted, mandate local parsing + local embeddings/LLMs (or an approved private VPC endpoint).

### Phase 2: Modular Ingestion Pipeline Architecture (Once Samples Are Inspected)
1. **Format & Scan Triage Router (Per-Page, Not Just Per-File):**
   - Inspect each PDF page for extractable text length + embedded font presence vs. full-page raster images (`pdfimages` / `PyMuPDF`).
   - Route digital text pages directly to native layout-aware extraction (`PyMuPDF` + `pdfplumber`); route only image-only or garbled-encoding pages to local OCR (e.g., Tesseract / PaddleOCR) and tag `extraction_method: "native" | "ocr"` + OCR confidence score in chunk metadata.
2. **Unicode & Structural Normalization (Deterministic Cleaning):**
   - Apply Unicode NFKC normalization, strip zero-width characters (`\u200b`, `\ufeff`), normalize bullet glyphs (`●`) and arrows (`→`), and preserve semantic punctuation (`≥`, `≤`, `°`, units).
   - Detect and strip recurring running headers/footers via top/bottom bounding-box repetition across pages (while extracting printed page labels separately if present).
3. **Layout-Aware & Cross-Page Table Extraction:**
   - Never use raw stream `pdftotext` on tables. Extract tables using vector line geometry (`pdfplumber` / `PyMuPDF` `find_tables()`), converting each table into structured Markdown/JSON rows **with header repetition**.
   - Implement a **cross-page table stitcher**: when a table ends at the bottom of page `N` and the top of page `N+1` starts with a table having identical column headers (as verified on PRD Pages 4–5), merge continuation rows (and propagate non-empty keys when leading key cells are blank) while recording `page_range: [N, N+1]`.
4. **Clause-Aware Hierarchical Chunking (Parent–Child / Section-Scoped):**
   - Parse section headings and numbered clauses (`1.`, `1.1`, `4.2.1(a)`) using font weight/size + numbering regexes.
   - Maintain a rolling section breadcrumb stack (`section_path`, e.g., `["3. Key Features", "3.2 User Stories"]`) across page boundaries so cross-page bullet continuations (like PRD Page 1 → Page 2) retain their parent heading.
   - Keep tables atomic when small, or chunk large tables row-group-by-row-group **with the column header row prepended to every chunk**.
5. **Citation-Ready Chunk Metadata Contract:**
   - Every chunk stored in the vector DB must carry:
     - `doc_id`, `doc_title`, `doc_type`, `jurisdiction`, `project_id`, `version`, `effective_date`, `page_start`, `page_end`, `section_id`, `section_path`, `content_type` (`prose | list | table`), `extraction_method` (`native | ocr`), `source_checksum` (SHA-256).
6. **Extraction Verification Harness (Before Vector Indexing):**
   - Add automated parser tests checking: zero `\u200b` leakage, intact row-column alignment on all tables, cross-page table row stitching, cross-page list heading preservation, and exact page-number attribution.

---

## 10. Unresolved Questions

In addition to the corpus questions already tracked in [`docs/OPEN_QUESTIONS.md`](file:///home/abhinivesh/Downloads/siteshield_ai/docs/OPEN_QUESTIONS.md) (`OQ-01` through `OQ-06`), this inspection surfaced the following concrete gaps requiring team/stakeholder resolution:

| ID | Question / Discrepancy | Observed Evidence | Blocks |
|---|---|---|---|
| **CQ-01** | Where is the actual construction document corpus (codes, specs, inspection reports), and when will representative sample files be placed in `data/raw/`? | 0 construction files exist in the repo; `SiteShield AI (PRD) Team Fire.pdf` is a software PRD (`OQ-01`–`OQ-03`). | Gate 2, Gate 4 |
| **CQ-02** | Which `document_type` taxonomy is canonical: 3 categories (`code`, `spec`, `report` per PRD §3.1) or 4 categories (`+ safety_guidelines / safety_manual` per `README.md` §1 & `OQ-01`)? | Inconsistent wording across PRD §3.1, `README.md` §1, and `OQ-01`. | Gate 2, Gate 4, Gate 6 |
| **CQ-03** | Which target jurisdictions, codes, and real `project_id`s are in scope (beyond the illustrative `Project #104` in PRD §3.2)? | Zero jurisdictions or standard bodies appear anywhere in repo files (`OQ-04`). | Gate 2, Gate 6 |
| **CQ-04** | Should the team reconcile the PRD vs. `README.md` conflicts (Python `3.10+` vs `3.11+` vs host `3.14.4`, `LangChain/LlamaIndex` vs custom, `Pinecone` inclusion/exclusion, `Precision@K` vs `Recall@K`, 5 PRD roles vs 3 `README.md` roles)? | Direct inconsistencies verified between `SiteShield AI (PRD) Team Fire.pdf` and `README.md`. | Gate 2, Gate 3, Gate 8 |
| **CQ-05** | Should `SiteShield AI (PRD) Team Fire.pdf` remain as-is, be tracked in `docs/`, or be converted/supplemented as `docs/PRD.md` (which `README.md` §7 & §15 reference)? | `README.md` references `docs/PRD.md`; root currently holds untracked `SiteShield AI (PRD) Team Fire.pdf`. | Gate 1, Gate 2 |
| **CQ-06** | Will real construction PDFs permit external LLM/embedding API calls, or do confidentiality/client NDA rules require local/self-hosted extraction, embeddings, and inference? | `OQ-06` remains open; no classification metadata exists yet. | Gate 2, Gate 3, Gate 8 |
| **CQ-07** | What canonical metadata sidecar format (e.g., `manifest.yaml` / `manifest.json`) will supply `effective_date`, `revision_number`, `jurisdiction`, and `project_id` when PDF `/Info` fields lack them (as observed in the PRD PDF)? | PRD PDF has no `/CreationDate`, `/ModDate`, XMP metadata, or body dates. | Gate 2, Gate 4, Gate 6 |
| **CQ-08** | How should the 4 pending Gate 1 commits (`chore: initialize Site Shield AI repository`, `docs: add team charter and project overview`, `docs: add initial product requirements`, `chore: configure Python and frontend gitignore`) map to the current working tree, given `README.md` is already committed (`a7e9c75`), no untracked team charter file exists, and active branch is `initialsetup` (`OQ-18`)? | Verified via `git status` and `git log`; requires user decision before committing. | Gate 1 |

---

*Prepared via local read-only file and PDF inspection (`pdfinfo`, `pdffonts`, `pdfimages`, `pdfdetach`, `pdftotext`, `pdftohtml`, `pdftoppm`). No files were uploaded externally, and no original repository files were modified or deleted.*
