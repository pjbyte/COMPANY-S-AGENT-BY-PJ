"""Ingestion pipeline: PDF -> clean text per page -> overlapping chunks.

Each chunk keeps the metadata needed for citations:
  {doc_id, doc_title, source, page, section, chunk_id, text}
Chunks never span pages, so every citation points at an exact page.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import pymupdf as fitz

_HEADING_RE = re.compile(
    r"^\s*(?:SECTION\s+\d+.*|\d+(\.\d+)*\s+[A-Z][A-Za-z].{0,70}|[A-Z][A-Z \-/&]{4,70})\s*$"
)


def _clean(text: str) -> str:
    text = text.replace("\u00ad", "")  # soft hyphens
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_headings(page_text: str) -> list[tuple[int, str]]:
    """Return [(char_offset, heading_text)] for lines that look like section titles."""
    headings = []
    offset = 0
    for line in page_text.splitlines(keepends=True):
        stripped = line.strip().rstrip("\n")
        if stripped and len(stripped) < 80 and _HEADING_RE.match(stripped):
            headings.append((offset, stripped))
        offset += len(line)
    return headings


def _split_with_overlap(text: str, size: int, overlap: int) -> list[tuple[int, str]]:
    """Split text into (start_offset, chunk) pieces on sentence/line boundaries."""
    if len(text) <= size:
        return [(0, text)] if text.strip() else []
    boundaries = [m.end() for m in re.finditer(r"[.!?\n]", text)]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # snap the cut to the last boundary inside the window
            candidates = [b for b in boundaries if start + size * 0.6 < b <= end]
            if candidates:
                end = candidates[-1]
        piece = text[start:end].strip()
        if piece:
            chunks.append((start, piece))
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def parse_pdf(path: str | Path, doc_title: str | None = None) -> dict:
    """Parse a PDF into per-page text + metadata (no chunking yet)."""
    path = Path(path)
    with fitz.open(path) as pdf:
        pages = [_clean(page.get_text("text")) for page in pdf]
        meta_title = (pdf.metadata or {}).get("title") or ""
    return {
        "doc_id": uuid.uuid4().hex[:12],
        "doc_title": doc_title or meta_title or path.stem.replace("_", " ").title(),
        "source": path.name,
        "pages": pages,  # index i == page number i+1
    }


def chunk_document(parsed: dict, chunk_size: int = 900, chunk_overlap: int = 150) -> list[dict]:
    chunks: list[dict] = []
    for page_idx, page_text in enumerate(parsed["pages"]):
        if not page_text:
            continue
        headings = _find_headings(page_text)
        # Segment the page at section headings so a chunk never mixes two
        # sections - topically pure chunks retrieve much better.
        segments = []
        for i, (offset, heading) in enumerate(headings):
            end = headings[i + 1][0] if i + 1 < len(headings) else len(page_text)
            segments.append((offset, end, heading))
        if not segments or segments[0][0] > 0:
            first_start = segments[0][0] if segments else len(page_text)
            segments.insert(0, (0, first_start, ""))
        for start, end, section in segments:
            segment_text = page_text[start:end]
            for local_idx, (rel_start, piece) in enumerate(
                _split_with_overlap(segment_text, chunk_size, chunk_overlap)
            ):
                if not piece:
                    continue
                chunks.append(
                    {
                        "chunk_id": f'{parsed["doc_id"]}:p{page_idx + 1}:{local_idx}:{start + rel_start}',
                        "doc_id": parsed["doc_id"],
                        "doc_title": parsed["doc_title"],
                        "source": parsed["source"],
                        "page": page_idx + 1,
                        "section": section,
                        "text": piece,
                    }
                )
    return chunks


def ingest_pdf(path: str | Path, chunk_size: int, chunk_overlap: int, doc_title: str | None = None):
    parsed = parse_pdf(path, doc_title)
    chunks = chunk_document(parsed, chunk_size, chunk_overlap)
    return parsed, chunks
