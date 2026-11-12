# Site Shield AI — Backend Foundation

FastAPI backend service foundation for **Site Shield AI**, implementing environment-driven configuration, structured JSON logging, centralized error handling, Pydantic API contracts, and health verification.

> **Scope Notice:** This stage implements the backend foundation and the **document ingestion pipeline** (validation, PDF/Markdown/text extraction, cleaning, cross-page table stitching, hierarchical chunking, and SQLite manifest/chunk persistence). Embeddings, vector storage, retrieval, and LLM generation remain unimplemented pending subsequent sprint gates.

## Directory Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── documents.py    # POST /documents/ingest, GET /documents*
│   │   │   └── health.py       # GET /health endpoint
│   │   └── router.py           # Top-level API router
│   ├── core/
│   │   ├── config.py           # Environment-driven Pydantic Settings
│   │   ├── exceptions.py       # AppError hierarchy & FastAPI error handlers
│   │   └── logging.py          # Structured JSON/console logging + request_id context
│   ├── generation/             # Reserved for grounded generation & citation validation
│   ├── ingestion/              # Document validation, extraction, cleaning, chunking, SQLite store
│   ├── retrieval/              # Reserved for hybrid retrieval & reranking
│   ├── schemas/                # Pydantic v2 request/response schemas
│   └── main.py                 # FastAPI app factory & middleware
├── tests/
│   ├── unit/                   # Config, logging, exceptions, schemas, ingestion unit tests
│   └── integration/            # Health, error envelope, and end-to-end ingestion tests
├── pyproject.toml              # Ruff & pytest configuration
├── requirements.txt            # Runtime dependencies
└── requirements-dev.txt        # Runtime + test & lint dependencies
```

## Prerequisites

- Python `3.11+` (recommended `3.12` in Docker/CI for downstream ML/PDF wheel compatibility)
- Repository root `.env` configured (never commit `.env` or secrets to Git)

## Local Setup

From the `backend/` directory:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

For runtime-only installation (without test/lint tools):

```bash
pip install -r requirements.txt
```

## Environment Variables

`app/core/config.py` reads environment variables (and `.env` / `../.env`). Empty string values (e.g., `API_PORT=`) safely fall back to typed defaults.

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Site Shield AI` | Service display name |
| `ENVIRONMENT` | `development` | `development \| staging \| production \| test` |
| `LOG_LEVEL` | `INFO` | `DEBUG \| INFO \| WARNING \| ERROR \| CRITICAL` |
| `LOG_FORMAT` | `json` | `json \| console` |
| `API_HOST` | `127.0.0.1` | Server bind host |
| `API_PORT` | `8000` | Server bind port (`1–65535`) |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Comma-separated or JSON array of allowed origins |
| `INGESTION_DB_PATH` | `data/processed/siteshield_ingestion.db` | SQLite registry path for ingested documents & chunks |
| `MAX_UPLOAD_SIZE_MB` | `25` | Maximum upload size config (`1–500`) |
| `ALLOWED_DOCUMENT_EXTENSIONS` | `[".pdf", ".md", ".txt"]` | Comma-separated or JSON array of extensions |
| `VECTOR_DB_PROVIDER` | `None` | Deferred RAG vector store provider name |
| `EMBEDDING_PROVIDER` | `None` | Deferred RAG embedding provider name |
| `LLM_PROVIDER` | `None` | Deferred RAG LLM provider name |

## Running the Server

From `backend/` with `.venv` activated:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify endpoints:
- Health check: `GET http://127.0.0.1:8000/health`
- Document ingestion: `POST http://127.0.0.1:8000/documents/ingest`
- List documents: `GET http://127.0.0.1:8000/documents`
- Document details & chunks: `GET http://127.0.0.1:8000/documents/{doc_id}` and `/chunks`
- Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`

## Running CLI Document Ingestion

From the repository root with `backend/.venv` activated:

```bash
backend/.venv/bin/python scripts/ingest_documents.py \
  --file SiteShield_AI_PRD.pdf \
  --title "SiteShield AI (PRD) Team Fire" \
  --doc-type spec \
  --version v1.0 \
  --show-chunks
```

## Running Tests & Linting

From `backend/`:

```bash
# Run unit and integration tests
pytest

# Check lint and formatting with Ruff
ruff check .
ruff format --check .
```

