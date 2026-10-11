"""Embedding layer. Turns text into vectors.

Two providers, chosen in config:
  - "local"  : sentence-transformers MiniLM on CPU. Free, private, fast enough.
  - "gemini" : Google embedding API. Needs the API key, no model download.
"""
from __future__ import annotations

import threading


class EmbeddingFunction:
    def __init__(self, provider: str, local_model: str, gemini_model: str, api_key: str = ""):
        self.provider = provider
        self.local_model_name = local_model
        self.gemini_model_name = gemini_model
        self.api_key = api_key
        self._model = None
        self._gemini_client = None
        self._lock = threading.Lock()

    @property
    def model_label(self) -> str:
        return (
            self.local_model_name.split("/")[-1]
            if self.provider == "local"
            else self.gemini_model_name
        )

    def _local_model(self):
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.local_model_name)
        return self._model

    def _gemini(self):
        with self._lock:
            if self._gemini_client is None:
                from google import genai

                self._gemini_client = genai.Client(api_key=self.api_key)
        return self._gemini_client

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "gemini":
            from google.genai import types

            resp = self._gemini().models.embed_content(
                model=self.gemini_model_name,
                contents=texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            return [e.values for e in resp.embeddings]
        vectors = self._local_model().encode(
            texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False
        )
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        if self.provider == "gemini":
            from google.genai import types

            resp = self._gemini().models.embed_content(
                model=self.gemini_model_name,
                contents=[text],
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
            )
            return resp.embeddings[0].values
        vec = self._local_model().encode([text], normalize_embeddings=False)[0]
        return vec.tolist()
