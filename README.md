# Site Shield AI

**AI-Powered Construction Compliance Assistant**

> Helping construction teams find, understand, and verify applicable building regulations through reliable, source-grounded AI.

## 1. Project Overview

Construction projects must comply with multiple documents, including building codes, project specifications, safety guidelines, and inspection reports.

However, site engineers often spend significant time searching through lengthy documents to identify the regulations applicable to a particular construction activity. Misinterpreting an outdated regulation or overlooking an important requirement can lead to compliance issues, project delays, and additional costs.

**Site Shield AI** aims to simplify this process using Retrieval-Augmented Generation (RAG).

It allows site engineers to ask construction-related compliance questions in natural language and receive answers grounded in relevant project documents, with references to the original sources.

The goal is not simply to generate answers, but to help users verify where the information came from.

## 2. Problem Statement

A construction firm maintains building codes, project specifications, and inspection reports, but site engineers cannot quickly confirm which regulation applies, risking costly compliance errors.

## 3. Proposed Solution

Site Shield AI provides an AI-powered document intelligence system that:

- Processes construction-related documents.
- Extracts and organizes relevant information.
- Converts document content into vector embeddings.
- Stores embeddings with document metadata in a vector database.
- Retrieves relevant information based on user questions.
- Generates answers using the retrieved evidence.
- Provides source references so users can verify the information.
- Identifies insufficient or conflicting evidence instead of confidently generating unsupported answers.

## 4. Key Features

The following features represent the planned project scope. Their implementation status will be updated as development progresses.

| Feature | Description |
|---|---|
| Document Processing | Extract text and relevant metadata from construction documents. |
| Intelligent Chunking | Divide documents into meaningful sections while preserving context. |
| Vector Embeddings | Convert document chunks into numerical representations. |
| Semantic Search | Retrieve relevant document sections based on user questions. |
| AI-Powered Answers | Generate responses grounded in retrieved evidence. |
| Source Citations | Display document references and relevant page or section details when available. |
| Evidence Validation | Check whether retrieved evidence supports the generated answer. |
| Conflict Detection | Identify potentially conflicting information across documents. |
| Safe Abstention | Indicate when sufficient evidence is unavailable. |

## 5. How It Works

Site Shield AI follows a Retrieval-Augmented Generation (RAG) pipeline.

```text
             CONSTRUCTION DOCUMENTS
                       |
                       v
              Document Processing
                       |
                       v
              Text Extraction
                       |
                       v
               Text Cleaning
                       |
                       v
              Document Chunking
                       |
                       v
              Generate Embeddings
                       |
                       v
                Vector Database
                       |
                       |
              USER ASKS A QUESTION
                       |
                       v
              Query Embedding
                       |
                       v
              Semantic Retrieval
                       |
                       v
             Retrieve Relevant Chunks
                       |
                       v
             Evidence-Grounded LLM
                       |
                       v
             Citation & Evidence Check
                       |
                       v
               FINAL RESPONSE
                       |
            +----------+----------+
            |          |          |
            v          v          v
         Supported   Needs      Not Found
          Answer     Review      / Abstain
```

### RAG Pipeline Explanation

**1. Document Ingestion**

Construction documents such as building codes, project specifications, and inspection reports are collected and processed.

**2. Text Extraction**

Text and available document metadata are extracted from supported file formats.

**3. Text Cleaning and Chunking**

Extracted content is cleaned and divided into smaller, meaningful chunks. Document headings, page numbers, sections, and other useful metadata are preserved wherever available.

**4. Embedding Generation**

Each chunk is converted into a vector embedding using an embedding model.

**5. Vector Storage**

The generated embeddings and associated metadata are stored in a vector database.

**6. Semantic Retrieval**

When an engineer submits a question, the system converts it into an embedding and searches for relevant document chunks.

**7. Grounded Answer Generation**

The retrieved evidence is provided to the language model as context. The model generates an answer based on the available evidence rather than relying solely on its general knowledge.

**8. Evidence and Citation Validation**

The system checks whether the answer can be supported by retrieved sources. If evidence is insufficient or conflicting, it should communicate that limitation.

## 6. Technology Stack

The following is the proposed technology stack. Final selections will be confirmed against the approved architecture.

| Layer | Proposed Technology | Purpose |
|---|---|---|
| Programming Language | Python | Backend and RAG implementation |
| Backend Framework | FastAPI | REST API development |
| Data Validation | Pydantic | Request and response validation |
| Document Processing | PyMuPDF / pdfplumber | PDF text extraction |
| Embedding Model | To be finalized | Convert text into vector representations |
| Vector Database | ChromaDB / Qdrant | Store and retrieve embeddings |
| Large Language Model | To be finalized | Generate evidence-grounded responses |
| Frontend | Next.js | User interface |
| Testing | pytest | Automated backend testing |
| Code Quality | Ruff | Python linting and formatting |
| Version Control | Git and GitHub | Collaboration and source management |
| CI/CD | GitHub Actions | Automated checks and validation |
| Containerization | Docker | Consistent application environments |

## 7. Project Architecture

The application is organized into separate layers to make development, testing, and maintenance easier.

```text
site-shield-ai/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │
│   │   ├── core/
│   │   │
│   │   ├── ingestion/
│   │   │
│   │   ├── retrieval/
│   │   │
│   │   ├── generation/
│   │   │
│   │   ├── schemas/
│   │   │
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── evaluation/
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│
├── docs/
│   ├── PRD.md
│   ├── RAG_ARCHITECTURE.md
│   ├── DOCUMENT_CORPUS_ANALYSIS.md
│   ├── API_SPECIFICATION.md
│   ├── EVALUATION_PLAN.md
│   ├── SECURITY.md
│   └── DECISIONS.md
│
├── scripts/
│   ├── ingest_documents.py
│   └── evaluate_retrieval.py
│
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   └── PULL_REQUEST_TEMPLATE.md
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

*Note: This is the proposed target structure. Directories and files will be introduced incrementally as their corresponding features are implemented.*

## 8. Installation and Local Setup

### Prerequisites

Install the following before starting development:

- Python 3.11 or a version supported by the selected dependencies.
- Node.js and npm.
- Git.
- Docker (if using containerized development).
- API credentials for the selected embedding and LLM providers.

### Step 1: Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd site-shield-ai
```

### Step 2: Backend Setup

```bash
cd backend

python -m venv .venv
```

Activate the virtual environment.

**Linux / macOS:**

```bash
source .venv/bin/activate
```

**Windows:**

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create a `.env` file using the example configuration:

```bash
cp .env.example .env
```

Add the required API credentials and configuration values.

Example:

```env
APP_NAME=Site Shield AI
ENVIRONMENT=development

LLM_PROVIDER=
LLM_API_KEY=

EMBEDDING_PROVIDER=
EMBEDDING_API_KEY=

VECTOR_DB_PROVIDER=
VECTOR_DB_PATH=
```

Use the actual variable names defined by the application configuration.

**Important:** Never commit `.env` files, API keys, passwords, or other secrets to GitHub.

### Step 4: Run the Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

Once the backend is running, access the FastAPI documentation at:

```text
http://127.0.0.1:8000/docs
```

### Step 5: Run the Frontend

Once the frontend has been implemented:

```bash
cd frontend
npm install
npm run dev
```

The frontend development server will display its local URL in the terminal.

## 9. API Design

The following endpoints are proposed for the application. Their request and response contracts will be defined in the API specification.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check application health |
| POST | `/documents/ingest` | Upload and process a document |
| GET | `/documents` | Retrieve available documents |
| GET | `/documents/{id}` | Retrieve document details |
| POST | `/query` | Submit a compliance question |
| GET | `/evaluation/summary` | View evaluation results |

## 10. Reliability and Safety

Construction compliance information can have real-world consequences. Therefore, Site Shield AI prioritizes evidence quality and traceability.

The system is designed around the following principles:

- **Source traceability:** Answers should identify the supporting document and page or section whenever that information is available.
- **No fabricated regulations:** The model must not invent building codes, section numbers, or document references.
- **Evidence-based responses:** Answers should be grounded in retrieved document content.
- **Insufficient evidence handling:** The system should communicate when it cannot find enough information.
- **Conflict awareness:** Conflicting document versions or requirements should be surfaced for human review.
- **Document version awareness:** Document revisions and effective dates should be preserved when available.
- **Human verification:** AI-generated responses are decision-support information and should not replace qualified professional judgment or official regulatory verification.

## 11. Testing and Evaluation

The project will be evaluated across different stages of the RAG pipeline.

| Evaluation Area | What We Measure |
|---|---|
| Document Extraction | Whether relevant document text is extracted correctly |
| Chunking | Whether meaningful context is preserved |
| Retrieval | Whether relevant document sections are retrieved |
| Precision@K | How many retrieved results are relevant |
| Recall@K | How many relevant results are successfully retrieved |
| Answer Grounding | Whether generated answers are supported by evidence |
| Citation Accuracy | Whether references point to the correct sources |
| Abstention | Whether the system avoids unsupported answers |
| Conflict Handling | Whether contradictory evidence is identified |
| Response Latency | How long the system takes to answer |

A curated evaluation dataset will contain representative construction compliance questions, expected evidence, and expected answer behavior.

Performance targets will be finalized after establishing a baseline.

## 12. Development Roadmap

The project is planned across five weeks.

| Week | Focus | Expected Outcome |
|---|---|---|
| Week 1 | Project foundation, corpus analysis, PRD, RAG architecture | Approved requirements and architecture |
| Week 2 | Document ingestion, extraction, cleaning, chunking, embeddings, vector storage | Working document indexing pipeline |
| Week 3 | Semantic retrieval, grounded generation, citations, guardrails | Working RAG backend |
| Week 4 | Frontend and backend integration | Usable compliance assistant |
| Week 5 | Evaluation, testing, deployment, documentation, demonstration | Validated and demonstrable application |

## 13. Team

**Team:** Team Fire (Team 02)  
**Squad:** Kalvium Squad 76  
**Sprint:** Sprint 2

| Member | Responsibility |
|---|---|
| Aakash J | Project coordination and backend integration |
| Jandy Y | Document processing and retrieval pipeline |
| Abhinivesh | Generation, evidence validation, frontend integration and evaluation |

*Responsibilities are a working proposal and should be updated to reflect the team's final agreed ownership.*

## 14. Git Workflow and Contribution Guidelines

We follow a feature-branch workflow to maintain code quality and simplify collaboration.

### Branch Naming

```text
main
├── chore/repository-foundation
├── docs/initial-prd
├── docs/rag-architecture
├── feature/document-ingestion
├── feature/embedding-pipeline
├── feature/vector-store
├── feature/semantic-retrieval
├── feature/grounded-generation
├── feature/citation-validation
├── feature/answer-guardrails
├── feature/qa-interface
└── test/rag-evaluation
```

### Development Workflow

1. Pick an issue from the project Kanban board.
2. Create a feature branch from the latest `main`.
3. Implement only the assigned functionality.
4. Add or update relevant tests.
5. Run tests and code-quality checks locally.
6. Commit changes using clear conventional commit messages.
7. Push the branch to GitHub.
8. Open a Pull Request against `main`.
9. Request a team review and address feedback.
10. Merge only after the required checks and approvals.

### Commit Message Convention

We use conventional commit prefixes:

| Prefix | Purpose |
|---|---|
| `feat` | New functionality |
| `fix` | Bug fixes |
| `docs` | Documentation changes |
| `test` | Test additions or changes |
| `refactor` | Code restructuring |
| `chore` | Configuration and maintenance |
| `ci` | CI/CD changes |

Examples:

```bash
git commit -m "docs: add initial project README"
git commit -m "feat(ingestion): implement PDF text extraction"
git commit -m "feat(retrieval): add semantic search"
git commit -m "test(evaluation): add retrieval benchmark cases"
```

## 15. Documentation

Project documentation will be maintained in the `docs/` directory.

| Document | Purpose |
|---|---|
| `PRD.md` | Product requirements and scope |
| `RAG_ARCHITECTURE.md` | RAG pipeline and technical architecture |
| `DOCUMENT_CORPUS_ANALYSIS.md` | Source document inventory and analysis |
| `API_SPECIFICATION.md` | API endpoints and contracts |
| `EVALUATION_PLAN.md` | Testing methodology and evaluation metrics |
| `SECURITY.md` | Security considerations |
| `DECISIONS.md` | Important technical decisions and their rationale |

Daily development journals, pull requests, test evidence, and demonstration recordings will also be maintained as required by the sprint guidelines.

## 16. Current Project Status

The following is the initial project status. Update it as work is completed.

- [ ] Repository and collaboration setup
- [ ] Team charter and project overview
- [ ] Construction document corpus collection
- [ ] Document corpus analysis
- [ ] Product Requirements Document approval
- [ ] RAG architecture approval
- [ ] Document ingestion pipeline
- [ ] Embedding generation
- [ ] Vector database integration
- [ ] Semantic retrieval
- [ ] Grounded answer generation
- [ ] Citation validation
- [ ] Insufficient evidence handling
- [ ] Conflict detection
- [ ] Frontend integration
- [ ] Automated testing and evaluation
- [ ] CI/CD setup
- [ ] Application deployment
- [ ] Final demonstration

## 17. Project Vision

**Site Shield AI aims to make construction compliance information easier to find, understand, and verify.**

By combining document intelligence, semantic retrieval, and evidence-grounded language generation, the project aims to reduce the time spent searching through technical documentation while improving the traceability of compliance-related information.

The central principle is simple:

**Every answer should be supported by evidence, every source should be traceable, and uncertainty should never be hidden.**

---

**Built by Team Fire | Kalvium Squad 76 | Sprint 2**