"""CLI utility for repeatable local document ingestion and chunk inspection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402
from app.ingestion.service import IngestionService  # noqa: E402
from app.ingestion.store import IngestionStore  # noqa: E402
from app.schemas.documents import DocumentIngestMetadata  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Site Shield AI document ingestion pipeline on local files."
    )
    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to a supported document (.pdf, .md, .txt).",
    )
    parser.add_argument("--title", required=True, help="Canonical document title.")
    parser.add_argument(
        "--doc-type",
        required=True,
        choices=["code", "spec", "report", "safety_manual"],
        help="Canonical document category.",
    )
    parser.add_argument("--jurisdiction", default="UNSPECIFIED", help="Regulatory jurisdiction.")
    parser.add_argument("--project-id", default=None, help="Optional project identifier.")
    parser.add_argument("--version", default="v1.0", help="Document version or revision.")
    parser.add_argument(
        "--confidentiality",
        default="internal",
        choices=["public", "internal", "restricted"],
        help="Confidentiality classification.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=REPO_ROOT / "data" / "processed" / "siteshield_ingestion.db",
        help="Path to SQLite ingestion registry.",
    )
    parser.add_argument(
        "--show-chunks",
        action="store_true",
        help="Include extracted chunk summaries in JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings(_env_file=None, ingestion_db_path=str(args.db_path), log_level="WARNING")
    store = IngestionStore(args.db_path)
    service = IngestionService(settings=settings, store=store)

    metadata = DocumentIngestMetadata(
        doc_title=args.title,
        doc_type=args.doc_type,
        jurisdiction=args.jurisdiction,
        project_id=args.project_id,
        version=args.version,
        confidentiality_tier=args.confidentiality,
    )
    result = service.ingest_file(args.file, metadata)
    payload: dict[str, object] = {"ingest_result": result.model_dump(mode="json")}

    if args.show_chunks:
        chunks = store.get_chunks(result.doc_id)
        payload["chunks"] = [
            {
                "chunk_index": chk.chunk_index,
                "chunk_id": chk.chunk_id,
                "page_start": chk.page_start,
                "page_end": chk.page_end,
                "section_id": chk.section_id,
                "section_path": chk.section_path,
                "content_type": chk.content_type.value,
                "token_estimate": chk.token_estimate,
                "preview": chk.text_verbatim[:160],
            }
            for chk in chunks
        ]

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

