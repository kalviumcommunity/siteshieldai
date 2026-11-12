# Open Questions — Site Shield AI

This document tracks unresolved requirements, corpus unknowns, technical decisions, and operational constraints discovered during repository inspection and development gates.

**Policy:** Unknown details (document formats, corpus size, jurisdictions, regulation versions, user permissions, API credentials, and evaluation metrics) must never be invented. Record every open assumption here until confirmed by the team, mentors, or project stakeholders.

---

## 1. Document Corpus & Domain Scope (Blocks Gate 2 & Gate 4)

| ID | Question | Impacted Gates | Status | Why It Matters |
|---|---|---|---|---|
| OQ-01 | Where is the actual construction document corpus stored, and what documents are included (building codes, project specs, inspection reports, safety manuals)? | Gate 2, Gate 4 | Open | No corpus files exist in the repository yet; ingestion and chunking cannot be designed around unverified assumptions. |
| OQ-02 | Which file formats and structural characteristics must be supported (digital PDF, scanned PDF needing OCR, DOCX, XLSX/CSV tables, TXT, drawings)? | Gate 2, Gate 4 | Open | Determines whether `PyMuPDF`/`pdfplumber` alone suffice or whether OCR and table-extraction tools are required. |
| OQ-03 | What is the initial corpus size (document count, page count, total MB) and expected growth? | Gate 2, Gate 5 | Open | Affects chunking budget, embedding batching, storage sizing, and upload size limits. |
| OQ-04 | Which regulatory jurisdictions and standard-setting bodies apply to the target construction projects? | Gate 2, Gate 6 | Open | Required for accurate `jurisdiction` metadata normalization and query scoping. |
| OQ-05 | How are `revision_number`, `publication_date`, `effective_date`, and `project_id` represented in source documents, and how should superseded versions be handled during retrieval? | Gate 2, Gate 4, Gate 6 | Open | Prevents engineers from receiving outdated or out-of-scope regulations without warning. |
| OQ-06 | Are any source documents confidential, proprietary, or subject to data-residency restrictions? | Gate 2, Gate 3, Gate 8 | Open | Determines whether third-party cloud LLM/embedding APIs can receive document text or if local/private models are required. |

---

## 2. Users, Access Control & Product Behavior (Blocks Gate 2 & Gate 9)

| ID | Question | Impacted Gates | Status | Why It Matters |
|---|---|---|---|---|
| OQ-07 | What authentication and role-based permissions (e.g., Site Engineer, Inspector, Compliance Admin) are required for document upload, deletion, and project-scoped querying? | Gate 2, Gate 4, Gate 9 | Open | API endpoints (`POST /documents/ingest`, `GET /documents`, `POST /query`) require explicit authorization assumptions before exposure. |
| OQ-08 | Should queries enforce mandatory project/jurisdiction selection or allow cross-corpus search with explicit warnings? | Gate 2, Gate 6, Gate 9 | Open | Prevents accidental cross-project compliance mix-ups while keeping field UX practical. |
| OQ-09 | What exact behavior is expected when retrieved documents contain conflicting requirements across revisions or document types (e.g., building code vs. project spec)? | Gate 2, Gate 7 | Open | Governs conflict-detection heuristics and UI warning display. |

---

## 3. Approved Technology Stack & Environment Constraints (Blocks Gate 3)

| ID | Question | Impacted Gates | Status | Why It Matters |
|---|---|---|---|---|
| OQ-10 | **Frontend selection:** `README.md` currently lists Next.js, while the engineering specification permits either **Streamlit** (rapid prototype) or **Next.js** (separate frontend), but not both. Which one is approved for the 5-week timeline? | Gate 3, Gate 9 | Open | Avoids building an unapproved frontend stack or splitting team capacity. |
| OQ-11 | **LLM & Embedding providers:** Which model providers are approved, what API credentials/quotas are available, and are local fallback models required for offline/CI testing? | Gate 3, Gate 5, Gate 7 | Open | Required before implementing configuration adapters and estimating cost/latency. |
| OQ-12 | **Vector database:** Should the team standardize on **Chroma** (embedded local persistence) or **Qdrant** (client-server / rich payload filtering)? | Gate 3, Gate 5, Gate 6 | Open | Influences metadata filtering capability, Docker setup, and deployment architecture. |
| OQ-13 | **RAG orchestration:** Should we use a lightweight custom Python layer or LangChain? | Gate 3 | Open | Affects dependency footprint, debuggability, and test isolation. |
| OQ-14 | **Python runtime version:** `README.md` specifies Python 3.11+, while the current development host has Python `3.14.4` (and `uv` installed). Should we pin Python `3.11` or `3.12` (via `.python-version` / `uv` / Docker) to ensure wheel compatibility with PDF and vector DB libraries? | Gate 3, Gate 4, Gate 10 | Open | Newer Python releases (3.14) frequently lack prebuilt wheels or support for ML/PDF/vector packages. |

---

## 4. Testing, Evaluation & Acceptance Criteria (Blocks Gate 2 & Gate 8)

| ID | Question | Impacted Gates | Status | Why It Matters |
|---|---|---|---|---|
| OQ-15 | Who will author and review the labeled evaluation dataset (questions, expected source passages, expected citations, out-of-scope abstention cases, and conflict cases)? | Gate 2, Gate 8 | Open | Groundedness and retrieval evaluation cannot rely on synthetic self-generated labels alone. |
| OQ-16 | What target thresholds (Recall@K, citation correctness, abstention accuracy, max response latency) define Sprint 2 acceptance? | Gate 2, Gate 8 | Open | Baseline metrics must be evaluated against explicit mentor/team acceptance criteria. |
| OQ-17 | What deployment target (local Docker demo, cloud VM, managed container service) is expected for Gate 10? | Gate 3, Gate 10 | Open | Affects `Dockerfile`, `docker-compose.yml`, and environment configuration design. |

---

## 5. Collaboration & Git Governance (Gate 1 Review)

| ID | Question | Impacted Gates | Status | Why It Matters |
|---|---|---|---|---|
| OQ-18 | The repository currently has an active branch named `initialsetup` (at the same commit as `main`). Should Gate 1 changes be pushed/PR'd from `initialsetup` or renamed to `chore/repository-foundation` to match `README.md`? | Gate 1 | Open | Keeps branch naming consistent with team Git rules without discarding existing user branch work. |
| OQ-19 | Are the proposed team member responsibilities in `README.md` Section 13 (Aakash J, Jandy Y, Abhinivesh) confirmed by all members and mentors? | Gate 1 | Open | Clarifies ownership before Gate 2 and Gate 3 issues are assigned. |
| OQ-20 | Are GitHub branch protection rules on `main` (require PR, require review, status checks) and the project Kanban board active on `kalviumcommunity/siteshieldai`? | Gate 1 | Open | Enforces team PR rules technically rather than relying on manual discipline alone. |

