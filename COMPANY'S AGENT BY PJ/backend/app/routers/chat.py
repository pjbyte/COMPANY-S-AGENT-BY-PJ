"""Chat endpoint - the main product surface.

POST /api/chat streams Server-Sent Events:
  meta    -> session info
  trace   -> the agent's decision path (for the UI's agent-trace bar)
  sources -> retrieved chunks used for the answer (citations panel)
  token   -> one piece of the answer text
  done    -> message id + final citations (client persists state)
"""
from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app import services
from app.agent.graph import run_agent
from app.config import settings
from app.core.llm import LLMNotConfigured
from app.db import database
from app.schemas import ChatRequest

router = APIRouter(prefix="/api", tags=["chat"])


def _get_or_create_session(session_id: str | None, question: str) -> tuple[str, str | None]:
    if session_id:
        rows = database.query("SELECT id, title FROM sessions WHERE id = ?", (session_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")
        return session_id, None
    new_id = uuid.uuid4().hex
    title = question.strip()[:60] or "New chat"
    database.execute("INSERT INTO sessions (id, title) VALUES (?, ?)", (new_id, title))
    return new_id, title


def _load_history(session_id: str) -> list[dict]:
    rows = database.query(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at, rowid",
        (session_id,),
    )
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def _demo_answer(question: str, docs: list[dict]) -> str:
    lines = [
        "**Demo mode** - no `GEMINI_API_KEY` is configured, so I can't write an AI answer, "
        "but the retrieval pipeline still works. Here are the most relevant passages I found:",
        "",
    ]
    for i, doc in enumerate(docs[:3], start=1):
        lines.append(
            f"**[{i}] {doc.get('doc_title', '')} - page {doc.get('page', '?')}"
            + (f" ({doc.get('section')})**" if doc.get("section") else "**")
        )
        lines.append(doc["text"][:320].strip() + "...")
        lines.append("")
    lines.append("Add your Gemini API key to `backend/.env` and restart to get full AI answers.")
    return "\n".join(lines)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    session_id, new_title = _get_or_create_session(request.session_id, request.question)
    history = _load_history(session_id)

    user_msg_id = uuid.uuid4().hex
    database.execute(
        "INSERT INTO messages (id, session_id, role, content) VALUES (?, ?, 'user', ?)",
        (user_msg_id, session_id, request.question),
    )

    async def event_stream():
        try:
            yield _sse({"type": "meta", "session_id": session_id, "title": new_title})

            state = await asyncio.to_thread(
                run_agent, request.question, history, services.llm, services.retriever, settings.web_search_enabled
            )

            answer = state.get("answer", "")
            demo = bool(state.get("demo"))
            if demo and not answer:
                answer = _demo_answer(request.question, state.get("docs", []))
            if not answer and not state.get("docs"):
                answer = "I could not find anything relevant in the indexed policies. Try uploading the document or rephrasing the question."

            yield _sse({"type": "trace", "trace": state.get("trace", [])})
            yield _sse({"type": "sources", "sources": state.get("citations", [])})

            # Stream the finished answer word-by-word so the UI feels live.
            for word in answer.split(" "):
                yield _sse({"type": "token", "value": word + " "})
                await asyncio.sleep(0.006)

            assistant_msg_id = uuid.uuid4().hex
            database.execute(
                "INSERT INTO messages (id, session_id, role, content, citations_json, trace_json, sources_json, demo) "
                "VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?)",
                (
                    assistant_msg_id,
                    session_id,
                    answer,
                    json.dumps(state.get("citations", []), ensure_ascii=False),
                    json.dumps(state.get("trace", []), ensure_ascii=False),
                    json.dumps(state.get("citations", []), ensure_ascii=False),
                    int(demo),
                ),
            )
            yield _sse(
                {
                    "type": "done",
                    "message_id": assistant_msg_id,
                    "demo": demo,
                    "citations": state.get("citations", []),
                }
            )
        except LLMNotConfigured:
            yield _sse({"type": "error", "message": "LLM not configured - set GEMINI_API_KEY in backend/.env"})
        except Exception as exc:  # keep the stream alive with a readable error
            yield _sse({"type": "error", "message": f"Agent failed: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions")
def list_sessions():
    return [dict(r) for r in database.query("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC LIMIT 50")]


@router.get("/sessions/{session_id}/messages")
def session_messages(session_id: str):
    rows = database.query(
        "SELECT id, role, content, citations_json, trace_json, demo, created_at "
        "FROM messages WHERE session_id = ? ORDER BY created_at, rowid",
        (session_id,),
    )
    return [
        {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "citations": json.loads(r["citations_json"] or "[]"),
            "trace": json.loads(r["trace_json"] or "[]"),
            "demo": bool(r["demo"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.delete("/sessions")
def clear_all_sessions():
    database.execute("DELETE FROM messages")
    database.execute("DELETE FROM sessions")
    return {"ok": True}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    database.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    database.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return {"ok": True}

