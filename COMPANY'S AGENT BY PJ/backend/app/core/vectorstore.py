"""ChromaDB wrapper - the persistent vector database.

Stores one collection of chunks. We pass embeddings explicitly instead of
letting Chroma embed for us, so the whole pipeline stays provider-agnostic.
"""
from __future__ import annotations

import threading

import chromadb


class VectorStore:
    def __init__(self, persist_dir, collection_name: str = "policies"):
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._lock = threading.Lock()

    def count(self) -> int:
        return self.collection.count()

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        with self._lock:
            self.collection.add(
                ids=[c["chunk_id"] for c in chunks],
                documents=[c["text"] for c in chunks],
                embeddings=embeddings,
                metadatas=[
                    {
                        "doc_id": c["doc_id"],
                        "doc_title": c["doc_title"],
                        "source": c["source"],
                        "page": c["page"],
                        "section": c["section"],
                    }
                    for c in chunks
                ],
            )

    def query(self, embedding: list[float], k: int) -> list[dict]:
        if self.count() == 0:
            return []
        res = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(k, self.count()),
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for i in range(len(res["ids"][0])):
            meta = res["metadatas"][0][i]
            cosine_dist = res["distances"][0][i]
            hits.append(
                {
                    "chunk_id": res["ids"][0][i],
                    "text": res["documents"][0][i],
                    "score": 1.0 - cosine_dist,  # cosine similarity
                    **meta,
                }
            )
        return hits

    def get_all(self) -> list[dict]:
        """All chunks - used to (re)build the BM25 keyword index."""
        if self.count() == 0:
            return []
        res = self.collection.get(include=["documents", "metadatas"])
        return [
            {
                "chunk_id": res["ids"][i],
                "text": res["documents"][i],
                **res["metadatas"][i],
            }
            for i in range(len(res["ids"]))
        ]

    def delete_document(self, doc_id: str) -> int:
        with self._lock:
            before = self.count()
            self.collection.delete(where={"doc_id": doc_id})
            return before - self.count()
