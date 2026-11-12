"""SQLite persistence registry for ingested documents, checksums, and verified chunks."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from app.ingestion.models import DocumentChunk
from app.schemas.documents import (
    ChunkRecord,
    ConfidentialityTier,
    ContentType,
    DocumentRecord,
    DocumentStatus,
    DocumentType,
    ExtractionMethod,
)


def _parse_optional_date(raw: str | None) -> date | None:
    return date.fromisoformat(raw) if raw else None


class IngestionStore:
    """Thread-safe SQLite store supporting repeatable ingestion and unchanged detection."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    doc_title TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    project_id TEXT,
                    standard_code TEXT,
                    version TEXT NOT NULL,
                    publication_date TEXT,
                    effective_date TEXT,
                    supersedes_doc_id TEXT,
                    status TEXT NOT NULL,
                    confidentiality_tier TEXT NOT NULL,
                    source_filename TEXT NOT NULL,
                    sha256_checksum TEXT NOT NULL UNIQUE,
                    page_count INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    tables_extracted INTEGER NOT NULL,
                    native_pages INTEGER NOT NULL,
                    ocr_pages INTEGER NOT NULL,
                    warnings_json TEXT NOT NULL,
                    ingested_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    page_start INTEGER NOT NULL,
                    page_end INTEGER NOT NULL,
                    printed_page_label TEXT,
                    section_id TEXT,
                    section_path_json TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    extraction_method TEXT NOT NULL,
                    ocr_confidence REAL,
                    char_start INTEGER NOT NULL,
                    char_end INTEGER NOT NULL,
                    token_estimate INTEGER NOT NULL,
                    text_for_embedding TEXT NOT NULL,
                    text_verbatim TEXT NOT NULL,
                    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_documents_checksum
                    ON documents(sha256_checksum);
                CREATE INDEX IF NOT EXISTS idx_chunks_doc_id
                    ON chunks(doc_id, chunk_index);
                """
            )

    @staticmethod
    def _row_to_document(row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            doc_id=row["doc_id"],
            doc_title=row["doc_title"],
            doc_type=DocumentType(row["doc_type"]),
            jurisdiction=row["jurisdiction"],
            project_id=row["project_id"],
            standard_code=row["standard_code"],
            version=row["version"],
            publication_date=_parse_optional_date(row["publication_date"]),
            effective_date=_parse_optional_date(row["effective_date"]),
            supersedes_doc_id=row["supersedes_doc_id"],
            status=DocumentStatus(row["status"]),
            confidentiality_tier=ConfidentialityTier(row["confidentiality_tier"]),
            source_filename=row["source_filename"],
            sha256_checksum=row["sha256_checksum"],
            page_count=row["page_count"],
            chunk_count=row["chunk_count"],
            ingested_at=datetime.fromisoformat(row["ingested_at"]),
        )

    def get_by_checksum(self, sha256_checksum: str) -> tuple[DocumentRecord, dict[str, int]] | None:
        """Look up an already-ingested document by exact SHA-256 content hash."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE sha256_checksum = ?",
                (sha256_checksum,),
            ).fetchone()
            if row is None:
                return None
            stats = {
                "tables_extracted": int(row["tables_extracted"]),
                "native_pages": int(row["native_pages"]),
                "ocr_pages": int(row["ocr_pages"]),
            }
            return self._row_to_document(row), stats

    def get_by_identity(
        self,
        *,
        source_filename: str,
        doc_type: DocumentType,
        project_id: str | None,
    ) -> DocumentRecord | None:
        """Find an existing document sharing source filename, type, and project scope."""
        with self._connect() as conn:
            if project_id is None:
                row = conn.execute(
                    """
                    SELECT * FROM documents
                    WHERE source_filename = ? AND doc_type = ? AND project_id IS NULL
                    """,
                    (source_filename, doc_type.value),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM documents
                    WHERE source_filename = ? AND doc_type = ? AND project_id = ?
                    """,
                    (source_filename, doc_type.value, project_id),
                ).fetchone()
            return self._row_to_document(row) if row is not None else None

    def upsert_document(
        self,
        record: DocumentRecord,
        chunks: list[DocumentChunk],
        *,
        tables_extracted: int,
        native_pages: int,
        ocr_pages: int,
        warnings: list[str],
    ) -> None:
        """Atomically persist or replace a document manifest and its chunks."""
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE doc_id = ?", (record.doc_id,))
            conn.execute(
                """
                INSERT INTO documents (
                    doc_id, doc_title, doc_type, jurisdiction, project_id, standard_code,
                    version, publication_date, effective_date, supersedes_doc_id, status,
                    confidentiality_tier, source_filename, sha256_checksum, page_count,
                    chunk_count, tables_extracted, native_pages, ocr_pages, warnings_json,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    doc_title = excluded.doc_title,
                    doc_type = excluded.doc_type,
                    jurisdiction = excluded.jurisdiction,
                    project_id = excluded.project_id,
                    standard_code = excluded.standard_code,
                    version = excluded.version,
                    publication_date = excluded.publication_date,
                    effective_date = excluded.effective_date,
                    supersedes_doc_id = excluded.supersedes_doc_id,
                    status = excluded.status,
                    confidentiality_tier = excluded.confidentiality_tier,
                    source_filename = excluded.source_filename,
                    sha256_checksum = excluded.sha256_checksum,
                    page_count = excluded.page_count,
                    chunk_count = excluded.chunk_count,
                    tables_extracted = excluded.tables_extracted,
                    native_pages = excluded.native_pages,
                    ocr_pages = excluded.ocr_pages,
                    warnings_json = excluded.warnings_json,
                    ingested_at = excluded.ingested_at
                """,
                (
                    record.doc_id,
                    record.doc_title,
                    record.doc_type.value,
                    record.jurisdiction,
                    record.project_id,
                    record.standard_code,
                    record.version,
                    record.publication_date.isoformat() if record.publication_date else None,
                    record.effective_date.isoformat() if record.effective_date else None,
                    record.supersedes_doc_id,
                    record.status.value,
                    record.confidentiality_tier.value,
                    record.source_filename,
                    record.sha256_checksum,
                    record.page_count,
                    record.chunk_count,
                    tables_extracted,
                    native_pages,
                    ocr_pages,
                    json.dumps(warnings),
                    record.ingested_at.isoformat(),
                ),
            )
            conn.executemany(
                """
                INSERT INTO chunks (
                    chunk_id, doc_id, chunk_index, page_start, page_end, printed_page_label,
                    section_id, section_path_json, content_type, extraction_method,
                    ocr_confidence, char_start, char_end, token_estimate,
                    text_for_embedding, text_verbatim
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chk.chunk_id,
                        chk.doc_id,
                        chk.chunk_index,
                        chk.page_start,
                        chk.page_end,
                        chk.printed_page_label,
                        chk.section_id,
                        json.dumps(chk.section_path),
                        chk.content_type.value,
                        chk.extraction_method.value,
                        chk.ocr_confidence,
                        chk.char_start,
                        chk.char_end,
                        chk.token_estimate,
                        chk.text_for_embedding,
                        chk.text_verbatim,
                    )
                    for chk in chunks
                ],
            )

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        """Retrieve a single persisted document record."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
            return self._row_to_document(row) if row is not None else None

    def list_documents(
        self,
        *,
        doc_type: DocumentType | None = None,
        jurisdiction: str | None = None,
        project_id: str | None = None,
        status: DocumentStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DocumentRecord], int]:
        """List persisted documents with optional metadata filters."""
        clauses: list[str] = []
        params: list[str | int] = []
        if doc_type is not None:
            clauses.append("doc_type = ?")
            params.append(doc_type.value)
        if jurisdiction is not None:
            clauses.append("jurisdiction = ?")
            params.append(jurisdiction)
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM documents {where_sql}",
                params,
            ).fetchone()
            total = int(total_row["cnt"]) if total_row is not None else 0

            rows = conn.execute(
                f"""
                SELECT * FROM documents {where_sql}
                ORDER BY ingested_at DESC, doc_id ASC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
            return [self._row_to_document(row) for row in rows], total

    def get_chunks(self, doc_id: str) -> list[ChunkRecord]:
        """Return all verified chunk records with full source metadata for a document."""
        doc = self.get_document(doc_id)
        if doc is None:
            return []

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index ASC",
                (doc_id,),
            ).fetchall()

        return [
            ChunkRecord(
                chunk_id=row["chunk_id"],
                doc_id=doc.doc_id,
                doc_title=doc.doc_title,
                doc_type=doc.doc_type,
                jurisdiction=doc.jurisdiction,
                project_id=doc.project_id,
                standard_code=doc.standard_code,
                version=doc.version,
                publication_date=doc.publication_date,
                effective_date=doc.effective_date,
                status=doc.status,
                confidentiality_tier=doc.confidentiality_tier,
                source_filename=doc.source_filename,
                sha256_checksum=doc.sha256_checksum,
                chunk_index=row["chunk_index"],
                page_start=row["page_start"],
                page_end=row["page_end"],
                printed_page_label=row["printed_page_label"],
                section_id=row["section_id"],
                section_path=json.loads(row["section_path_json"]),
                content_type=ContentType(row["content_type"]),
                extraction_method=ExtractionMethod(row["extraction_method"]),
                ocr_confidence=row["ocr_confidence"],
                char_start=row["char_start"],
                char_end=row["char_end"],
                token_estimate=row["token_estimate"],
                text_for_embedding=row["text_for_embedding"],
                text_verbatim=row["text_verbatim"],
            )
            for row in rows
        ]

