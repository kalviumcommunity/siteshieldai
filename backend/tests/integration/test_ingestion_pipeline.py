"""Integration tests for repeatable document ingestion, PDF edge cases, and API routes."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.ingestion.service import IngestionService
from app.ingestion.store import IngestionStore
from app.schemas.documents import (
    ContentType,
    DocumentIngestMetadata,
    DocumentType,
    ExtractionMethod,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PRD_PDF = REPO_ROOT / "SiteShield_AI_PRD.pdf"
ROOT_README = REPO_ROOT / "README.md"


def _make_blank_pdf_bytes() -> bytes:
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def _make_encrypted_pdf_bytes() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Confidential Building Spec")
    data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner")
    doc.close()
    return data


def _make_image_only_pdf_bytes() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 100), False)
    pix.clear_with(240)
    page.insert_image(pymupdf.Rect(72, 72, 272, 272), pixmap=pix)
    data = doc.tobytes()
    doc.close()
    return data


def test_ingest_real_prd_pdf_and_detect_unchanged_repeat(client: TestClient) -> None:
    metadata = {
        "doc_title": "SiteShield AI PRD",
        "doc_type": "spec",
        "jurisdiction": "UNSPECIFIED",
        "version": "v1.0",
        "confidentiality_tier": "internal",
    }
    pdf_bytes = PRD_PDF.read_bytes()

    first = client.post(
        "/documents/ingest",
        files={"file": (PRD_PDF.name, pdf_bytes, "application/pdf")},
        data={"metadata": json.dumps(metadata)},
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["status"] == "ingested"
    assert first_body["unchanged"] is False
    assert first_body["page_count"] == 5
    assert first_body["tables_extracted"] == 5
    assert first_body["extraction_summary"] == {"native_pages": 5, "ocr_pages": 0}
    doc_id = first_body["doc_id"]

    # Repeat ingestion of identical file + metadata must detect unchanged document
    second = client.post(
        "/documents/ingest",
        files={"file": (PRD_PDF.name, pdf_bytes, "application/pdf")},
        data={"metadata": json.dumps(metadata)},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["doc_id"] == doc_id
    assert second_body["status"] == "unchanged"
    assert second_body["unchanged"] is True
    assert second_body["chunks_created"] == first_body["chunks_created"]

    # Verify list, detail, and chunks endpoints
    listed = client.get("/documents")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    detail = client.get(f"/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["sha256_checksum"] == first_body["sha256_checksum"]

    chunks_res = client.get(f"/documents/{doc_id}/chunks")
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()["chunks"]
    assert len(chunks) == first_body["chunks_created"]

    # Verify cleaning, cross-page list section preservation, and stitched Week 5 table
    all_text = "\n".join(chk["text_verbatim"] for chk in chunks)
    assert "\u200b" not in all_text
    assert "≥ 85% top-3 recall" in all_text

    table_chunks = [chk for chk in chunks if chk["content_type"] == ContentType.TABLE.value]
    assert len(table_chunks) == 5
    milestone_table = next(
        chk
        for chk in table_chunks
        if "Accuracy benchmarking against test queries," in chk["text_verbatim"]
    )
    assert milestone_table["page_start"] == 4
    assert milestone_table["page_end"] == 5
    expected_week5 = (
        "Accuracy benchmarking against test queries, performance optimization, "
        "final viva & product submission."
    )
    assert expected_week5 in milestone_table["text_verbatim"]


def test_ingest_real_readme_markdown_and_update_on_change(client: TestClient) -> None:
    meta = {
        "doc_title": "Site Shield AI Project Overview",
        "doc_type": "spec",
        "jurisdiction": "GLOBAL",
        "version": "v1.0",
    }
    first = client.post(
        "/documents/ingest",
        files={"file": ("README.md", ROOT_README.read_bytes(), "text/markdown")},
        data={"metadata": json.dumps(meta)},
    )
    assert first.status_code == 201
    doc_id = first.json()["doc_id"]
    assert first.json()["tables_extracted"] == 8

    # Modified content with same logical identity must update cleanly without duplicates
    updated_md = b"# Updated Spec\n## 1.1 Curing\nMinimum curing duration is 14 days.\n"
    second = client.post(
        "/documents/ingest",
        files={"file": ("README.md", updated_md, "text/markdown")},
        data={"metadata": json.dumps({**meta, "version": "v1.1"})},
    )
    assert second.status_code == 201
    assert second.json()["doc_id"] == doc_id
    assert second.json()["status"] == "updated"

    chunks_res = client.get(f"/documents/{doc_id}/chunks")
    assert chunks_res.status_code == 200
    assert chunks_res.json()["total_chunks"] == second.json()["chunks_created"]
    assert client.get("/documents").json()["total"] == 1


def test_ingest_handles_malformed_empty_encrypted_and_duplicate_files(client: TestClient) -> None:
    meta_json = json.dumps(
        {
            "doc_title": "Faulty Doc",
            "doc_type": "report",
            "version": "v1.0",
            "project_id": "Project #104",
        }
    )

    empty_res = client.post(
        "/documents/ingest",
        files={"file": ("empty.txt", b"", "text/plain")},
        data={"metadata": meta_json},
    )
    assert empty_res.status_code == 422
    assert empty_res.json()["error"]["code"] == "EMPTY_DOCUMENT"

    blank_pdf_res = client.post(
        "/documents/ingest",
        files={"file": ("blank.pdf", _make_blank_pdf_bytes(), "application/pdf")},
        data={"metadata": meta_json},
    )
    assert blank_pdf_res.status_code == 422
    assert blank_pdf_res.json()["error"]["code"] == "EMPTY_DOCUMENT"

    corrupt_pdf_res = client.post(
        "/documents/ingest",
        files={"file": ("corrupt.pdf", b"%PDF-1.4\n%%corrupted-stream", "application/pdf")},
        data={"metadata": meta_json},
    )
    assert corrupt_pdf_res.status_code == 422
    assert corrupt_pdf_res.json()["error"]["code"] == "MALFORMED_DOCUMENT"

    encrypted_res = client.post(
        "/documents/ingest",
        files={"file": ("locked.pdf", _make_encrypted_pdf_bytes(), "application/pdf")},
        data={"metadata": meta_json},
    )
    assert encrypted_res.status_code == 422
    assert encrypted_res.json()["error"]["code"] == "ENCRYPTED_DOCUMENT"

    # Duplicate content under different filename returns 409 Conflict
    content = b"# Safety Note\nWear helmet on scaffolding.\n"
    ok_res = client.post(
        "/documents/ingest",
        files={"file": ("note_a.txt", content, "text/plain")},
        data={"metadata": meta_json},
    )
    assert ok_res.status_code == 201

    dup_res = client.post(
        "/documents/ingest",
        files={"file": ("note_b.txt", content, "text/plain")},
        data={"metadata": meta_json},
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "DUPLICATE_DOCUMENT_CONTENT"


def test_scanned_pdf_routes_to_ocr_callback_hook(test_settings: Settings) -> None:
    store = IngestionStore(test_settings.ingestion_db_path)

    def fake_ocr(_png: bytes, page_no: int) -> tuple[str, float]:
        return f"4.2.1 Scaffolding inspection passed on page {page_no}.", 0.94

    service = IngestionService(settings=test_settings, store=store, ocr_fn=fake_ocr)
    res = service.ingest_bytes(
        "scan.pdf",
        _make_image_only_pdf_bytes(),
        DocumentIngestMetadata(
            doc_title="Scanned Inspection Report",
            doc_type=DocumentType.REPORT,
            project_id="Project #104",
            version="v1.0",
        ),
    )
    assert res.extraction_summary.ocr_pages == 1
    assert res.extraction_summary.native_pages == 0
    chunks = store.get_chunks(res.doc_id)
    assert len(chunks) == 1
    assert chunks[0].extraction_method == ExtractionMethod.OCR
    assert chunks[0].ocr_confidence == 0.94
    assert "Scaffolding inspection passed" in chunks[0].text_verbatim
