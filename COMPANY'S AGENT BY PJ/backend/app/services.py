"""Process-wide singletons: LLM client, embeddings, vector store, retriever.
Initialised once at startup and shared by every request."""
from __future__ import annotations

import logging

from app.config import STORAGE_DIR, settings
from app.core.embeddings import EmbeddingFunction
from app.core.llm import LLMClient
from app.core.retriever import HybridRetriever, Reranker
from app.core.vectorstore import VectorStore

logger = logging.getLogger("policypilot")

llm = LLMClient(
    api_key=settings.gemini_api_key,
    model=settings.gemini_model,
    temperature=settings.llm_temperature,
)

embedding_fn = EmbeddingFunction(
    provider=settings.embeddings_provider,
    local_model=settings.embeddings_model,
    gemini_model=settings.gemini_embedding_model,
    api_key=settings.gemini_api_key,
)

vector_store = VectorStore(persist_dir=STORAGE_DIR / "chroma")

reranker = Reranker(settings.rerank_model) if settings.rerank_enabled else None

retriever = HybridRetriever(vector_store=vector_store, embedding_fn=embedding_fn, reranker=reranker)


def warm_up() -> None:
    """Load heavy pieces once so the first request is fast."""
    chunks = retriever.rebuild_bm25()
    logger.info("BM25 index built over %d chunks", chunks)
    if llm.available:
        logger.info("LLM ready: %s", settings.gemini_model)
    else:
        logger.warning("GEMINI_API_KEY not set - running in demo fallback mode")
    if settings.embeddings_provider == "local":
        embedding_fn.embed_query("warmup")
        logger.info("Embedding model loaded: %s", embedding_fn.model_label)
    if reranker is not None:
        if reranker.available:
            logger.info("Reranker loaded: %s", settings.rerank_model)
        else:
            logger.warning("Reranker unavailable - continuing with fusion ordering only")
