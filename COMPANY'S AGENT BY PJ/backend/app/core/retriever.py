"""Hybrid retriever: vector search + BM25 keyword search -> Reciprocal Rank
Fusion -> optional cross-encoder reranking.

This is the part that separates a toy RAG from a production one: vector-only
retrieval misses exact terms ("WFH stipend", policy codes), BM25-only misses
paraphrases. Hybrid + rerank consistently scores highest in retrieval evals.
"""
from __future__ import annotations

import threading

from app.config import settings
from app.core.bm25 import BM25Index


class Reranker:
    """Cross-encoder reranker, lazily loaded (downloads ~80MB on first use)."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._failed = False
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        if not settings.rerank_enabled:
            return False
        try:
            self._load()
            return True
        except Exception:
            return False

    def _load(self):
        with self._lock:
            if self._model is None and not self._failed:
                try:
                    from sentence_transformers import CrossEncoder

                    self._model = CrossEncoder(self.model_name, max_length=512)
                except Exception:
                    self._failed = True
                    raise
        return self._model

    def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        model = self._load()
        pairs = [(query, c["text"]) for c in chunks]
        scores = model.predict(pairs)
        ranked = sorted(zip(scores, chunks), key=lambda p: p[0], reverse=True)
        return [{**c, "score": float(s)} for s, c in ranked]


def reciprocal_rank_fusion(result_lists: list[list[dict]], k: int) -> list[dict]:
    """Fuse multiple ranked lists into one score: sum of 1/(rrf_k + rank)."""
    fused: dict[str, dict] = {}
    for results in result_lists:
        for rank, chunk in enumerate(results):
            entry = fused.setdefault(chunk["chunk_id"], {**chunk, "score": 0.0})
            entry["score"] += 1.0 / (k + rank + 1)
    return sorted(fused.values(), key=lambda c: c["score"], reverse=True)


class HybridRetriever:
    def __init__(self, vector_store, embedding_fn, reranker: Reranker | None = None):
        self.vector_store = vector_store
        self.embedding_fn = embedding_fn
        self.reranker = reranker
        self.bm25 = BM25Index()
        self._lock = threading.Lock()

    def rebuild_bm25(self) -> int:
        chunks = self.vector_store.get_all()
        with self._lock:
            self.bm25.rebuild(chunks)
        return len(chunks)

    def retrieve(self, query: str, retrieval_k: int | None = None, final_k: int | None = None) -> list[dict]:
        retrieval_k = retrieval_k or settings.retrieval_k
        final_k = final_k or settings.final_k
        if self.vector_store.count() == 0:
            return []

        query_embedding = self.embedding_fn.embed_query(query)
        vector_hits = self.vector_store.query(query_embedding, k=retrieval_k)
        with self._lock:
            bm25_hits = self.bm25.search(query, k=retrieval_k)

        fused = reciprocal_rank_fusion([vector_hits, bm25_hits], k=settings.rrf_k)

        if self.reranker is not None:
            try:
                fused = self.reranker.rerank(query, fused[:retrieval_k])
            except Exception:
                pass  # reranker unavailable -> keep fusion order
        return fused[:final_k]
