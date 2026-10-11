"""Feedback + stats + health endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app import services
from app.config import settings
from app.db import database
from app.schemas import FeedbackRequest

router = APIRouter(prefix="/api", tags=["misc"])


@router.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    rows = database.query("SELECT id FROM messages WHERE id = ?", (request.message_id,))
    if not rows:
        return {"ok": False, "detail": "message not found"}
    database.execute(
        "INSERT INTO feedback (message_id, rating, comment) VALUES (?, ?, ?)",
        (request.message_id, request.rating, request.comment),
    )
    return {"ok": True}


@router.get("/stats")
def stats():
    docs = database.query("SELECT COUNT(*) AS n FROM documents")[0]["n"]
    likes = database.query("SELECT COUNT(*) AS n FROM feedback WHERE rating = 1")[0]["n"]
    dislikes = database.query("SELECT COUNT(*) AS n FROM feedback WHERE rating = -1")[0]["n"]
    sessions = database.query("SELECT COUNT(*) AS n FROM sessions")[0]["n"]
    questions = database.query("SELECT COUNT(*) AS n FROM messages WHERE role = 'user'")[0]["n"]
    return {
        "documents": docs,
        "chunks": services.vector_store.count(),
        "sessions": sessions,
        "questions": questions,
        "feedback": {"up": likes, "down": dislikes},
        "llm": {
            "provider": "gemini" if services.llm.available else "demo-fallback",
            "model": settings.gemini_model if services.llm.available else None,
        },
        "embeddings": {"provider": settings.embeddings_provider, "model": services.embedding_fn.model_label},
        "reranker": {"enabled": services.reranker is not None and services.reranker.available, "model": settings.rerank_model},
        "hybrid_search": True,
        "agent": {"web_search_fallback": settings.web_search_enabled},
    }


@router.get("/health")
def health():
    return {"status": "ok", "chunks": services.vector_store.count(), "llm_ready": services.llm.available}
