"""Document management: upload PDFs, list them, delete them."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app import services
from app.config import STORAGE_DIR, settings
from app.core.ingestion import ingest_pdf
from app.db import database

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(file: UploadFile):
    raw_name = file.filename or ""
    if not raw_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Sanitize filename to prevent directory traversal or invalid characters
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", Path(raw_name).name)
    if not safe_name or safe_name == ".pdf":
        safe_name = f"doc_{uuid.uuid4().hex[:8]}.pdf"

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    upload_path = STORAGE_DIR / "uploads" / f"{uuid.uuid4().hex}_{safe_name}"

    # Read and validate magic header (PDF magic bytes: %PDF)
    header = await file.read(1024)
    if not header.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file format or corrupted header")

    # Stream write while enforcing maximum file size limit
    size = len(header)
    with upload_path.open("wb") as f:
        f.write(header)
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                upload_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum allowed size of {settings.max_upload_size_mb}MB",
                )
            f.write(chunk)

    try:
        parsed, chunks = ingest_pdf(
            upload_path,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
    except Exception as exc:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {exc}") from exc

    if not chunks:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="No extractable text found (scanned PDF? needs OCR)")

    embeddings = services.embedding_fn.embed_documents([c["text"] for c in chunks])
    services.vector_store.add_chunks(chunks, embeddings)
    total_chunks = services.retriever.rebuild_bm25()

    database.execute(
        "INSERT INTO documents (doc_id, title, filename, pages, chunks) VALUES (?, ?, ?, ?, ?)",
        (parsed["doc_id"], parsed["doc_title"], parsed["source"], len(parsed["pages"]), len(chunks)),
    )
    return {
        "doc_id": parsed["doc_id"],
        "title": parsed["doc_title"],
        "pages": len(parsed["pages"]),
        "chunks": len(chunks),
        "total_chunks": total_chunks,
    }


@router.get("")
def list_documents():
    return [
        dict(r)
        for r in database.query("SELECT doc_id, title, filename, pages, chunks, ingested_at FROM documents ORDER BY ingested_at DESC")
    ]


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    deleted = services.vector_store.delete_document(doc_id)
    services.retriever.rebuild_bm25()
    database.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Document not found in the index")
    return {"ok": True, "chunks_removed": deleted}
