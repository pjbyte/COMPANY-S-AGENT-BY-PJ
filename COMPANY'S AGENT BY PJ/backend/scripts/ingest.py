"""CLI ingestion: parse PDFs -> chunk -> embed -> store, then rebuild BM25.

Run from backend/:
    .venv/Scripts/python scripts/ingest.py                     # data/policies/*.pdf
    .venv/Scripts/python scripts/ingest.py path/to/other.pdf   # specific file
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import services  # noqa: E402
from app.config import DATA_DIR, STORAGE_DIR, settings  # noqa: E402
from app.core.ingestion import ingest_pdf  # noqa: E402
from app.db import database  # noqa: E402


def ingest_file(path: Path) -> dict:
    parsed, chunks = ingest_pdf(
        path,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    print(f"  {path.name}: {len(parsed['pages'])} pages -> {len(chunks)} chunks, embedding...")
    embeddings = services.embedding_fn.embed_documents([c["text"] for c in chunks])
    services.vector_store.add_chunks(chunks, embeddings)
    database.init_db(STORAGE_DIR / "policypilot.db")
    database.execute(
        "INSERT OR REPLACE INTO documents (doc_id, title, filename, pages, chunks) VALUES (?, ?, ?, ?, ?)",
        (parsed["doc_id"], parsed["doc_title"], parsed["source"], len(parsed["pages"]), len(chunks)),
    )
    return {"title": parsed["doc_title"], "chunks": len(chunks)}


def main() -> None:
    targets = [Path(a) for a in sys.argv[1:]] or sorted((DATA_DIR / "policies").glob("*.pdf"))
    if not targets:
        print("No PDFs found. Generate sample policies first: python scripts/make_sample_policies.py")
        return
    print(f"Ingesting {len(targets)} file(s)...")
    for path in targets:
        ingest_file(path)
    total = services.retriever.rebuild_bm25()
    print(f"Done. Vector store + BM25 now hold {total} chunks.")


if __name__ == "__main__":
    main()
