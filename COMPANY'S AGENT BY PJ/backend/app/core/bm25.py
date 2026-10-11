"""BM25 keyword index - the 'lexical' half of hybrid search.

Vector search finds chunks that *mean* the same thing; BM25 finds chunks
containing the exact *words* (policy codes, names, numbers). Reciprocal
Rank Fusion in retriever.py combines both rankings.
"""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self):
        self._bm25 = None
        self._chunks: list[dict] = []

    def rebuild(self, chunks: list[dict]) -> None:
        self._chunks = chunks
        corpus = [_tokenize(c["text"]) for c in chunks]
        self._bm25 = BM25Okapi(corpus) if corpus and any(corpus) else None

    def search(self, query: str, k: int) -> list[dict]:
        if self._bm25 is None:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(zip(scores, self._chunks), key=lambda pair: pair[0], reverse=True)
        return [{**chunk, "score": float(score)} for score, chunk in ranked[:k] if score > 0]
