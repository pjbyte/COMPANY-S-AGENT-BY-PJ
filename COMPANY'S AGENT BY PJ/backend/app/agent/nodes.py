"""Agent nodes. Each is a plain function: AgentState -> partial AgentState.

This is where the "agentic" behaviour lives:
  rewrite_query -> route -> retrieve -> grade_documents -> generate
                                                        -> check_grounded
with a self-corrective loop: if grading finds nothing relevant, the agent
rewrites and retries (optionally falling back to web search).
"""
from __future__ import annotations

import time

from app.agent.state import AgentState
from app.core import prompts
from app.core.generator import (
    format_context,
    generate_answer,
    generate_direct,
    generate_smalltalk,
    generate_web_fallback,
)
from app.core.llm import LLMClient, extract_json


def _now() -> float:
    return round(time.time() * 1000)


def rewrite_query(state: AgentState, llm: LLMClient) -> dict:
    question = state["question"]
    default = {"rewritten_query": question, "trace": [{"step": "rewrite_query", "detail": "kept original question", "ts": _now()}]}
    if not llm.available:
        return default
    try:
        rewritten = llm.generate(
            prompts.REWRITE_QUERY_PROMPT.format(
                question=question,
                history="\n".join(f"{m['role']}: {m['content']}" for m in state.get("history", [])[-4:]),
            ),
            temperature=0.0,
        ).strip()
        rewritten = rewritten.strip('"`')
        if not rewritten or len(rewritten) > 300:
            return default
        return {
            "rewritten_query": rewritten,
            "trace": [{"step": "rewrite_query", "detail": rewritten, "ts": _now()}],
        }
    except Exception:
        return default


def route(state: AgentState, llm: LLMClient) -> dict:
    question = state["question"]
    route, reason = "policy_docs", "default: treat as policy question"
    if llm.available:
        try:
            data = extract_json(
                llm.generate(prompts.ROUTER_PROMPT.format(question=question), temperature=0.0, json_mode=True)
            )
            if data and data.get("route") in ("policy_docs", "general", "smalltalk"):
                route = data["route"]
                reason = data.get("reason", reason)
        except Exception:
            pass
    return {
        "route": route,
        "route_reason": reason,
        "trace": [{"step": "route", "detail": f"{route} - {reason}", "ts": _now()}],
    }


def retrieve(state: AgentState, retriever) -> dict:
    docs = retriever.retrieve(state["rewritten_query"])
    return {
        "docs": docs,
        "trace": [
            {
                "step": "retrieve",
                "detail": f"{len(docs)} candidate chunks (hybrid search + rerank)",
                "ts": _now(),
            }
        ],
    }


def grade_documents(state: AgentState, llm: LLMClient) -> dict:
    docs = state.get("docs", [])
    if not llm.available:
        return {"trace": [{"step": "grade_documents", "detail": f"kept all {len(docs)} (no LLM key)", "ts": _now()}]}

    relevant, rejected = [], 0
    for idx, doc in enumerate(docs):
        try:
            data = extract_json(
                llm.generate(
                    prompts.GRADE_PROMPT.format(
                        question=state["rewritten_query"],
                        idx=idx + 1,
                        source=doc.get("source", "?"),
                        page=doc.get("page", "?"),
                        section=doc.get("section") or "n/a",
                        chunk=doc["text"][:1200],
                    ),
                    temperature=0.0,
                    json_mode=True,
                )
            )
            ok = bool(data and data.get("relevant"))
        except Exception:
            ok = True  # fail open: keep the chunk rather than lose the answer
        if ok:
            relevant.append(doc)
        else:
            rejected += 1

    return {
        "docs": relevant,
        "rejected": rejected,
        "trace": [
            {
                "step": "grade_documents",
                "detail": f"{len(relevant)} relevant / {rejected} rejected",
                "ts": _now(),
            }
        ],
    }


def needs_retry(state: AgentState) -> str:
    """Conditional edge after grading: retry with a new query, search the web,
    or generate from what we have."""
    if state.get("docs"):
        return "generate"
    if state.get("retries", 0) < 1:
        return "retry_retrieve"
    if state.get("web_results"):
        return "web_generate"
    return "no_docs"


def retry_retrieve(state: AgentState, retriever, llm: LLMClient) -> dict:
    """Broaden the query and try once more."""
    retries = state.get("retries", 0) + 1
    broadened = f"{state['rewritten_query']} OR {state['question']} general policy procedure rules"
    docs = retriever.retrieve(broadened)
    update: AgentState = {
        "retries": retries,
        "docs": docs,
        "trace": [{"step": "retry_retrieve", "detail": f"attempt {retries}: {len(docs)} chunks", "ts": _now()}],
    }
    if llm.available and docs:
        # re-grade cheaply: keep it simple, keep all this round
        return update
    return update


def generate(state: AgentState, llm: LLMClient) -> dict:
    if not llm.available:
        return {"demo": True, "trace": [{"step": "generate", "detail": "skipped (no API key)", "ts": _now()}]}
    answer = generate_answer(
        llm,
        state["question"],
        state["docs"],
        state.get("history", []),
        unsupported=state.get("unsupported_claims"),
    )
    return {"answer": answer, "trace": [{"step": "generate", "detail": f"{len(answer)} chars", "ts": _now()}]}


def check_grounded(state: AgentState, llm: LLMClient) -> dict:
    """Hallucination audit. If the answer contains unsupported claims, one
    stricter regeneration is triggered by the graph's conditional edge."""
    if not llm.available or state.get("demo"):
        return {}
    try:
        data = extract_json(
            llm.generate(
                prompts.HALLUCINATION_PROMPT.format(
                    question=state["question"],
                    context=format_context(state["docs"]),
                    answer=state["answer"],
                ),
                temperature=0.0,
                json_mode=True,
            )
        )
    except Exception:
        return {"grounded": True, "unsupported_claims": []}
    if data is None:
        return {"grounded": True, "unsupported_claims": []}
    grounded = bool(data.get("grounded", True))
    unsupported = [c for c in (data.get("unsupported_claims") or []) if c]
    return {
        "grounded": grounded,
        "unsupported_claims": unsupported,
        "trace": [
            {
                "step": "check_grounded",
                "detail": f"{'grounded' if grounded else 'unsupported claims: ' + '; '.join(unsupported[:2])}",
                "ts": _now(),
            }
        ],
    }


def should_regenerate(state: AgentState) -> str:
    if state.get("grounded") or state.get("retries", 0) > 1:
        return "finish"
    return "regenerate"


def regenerate(state: AgentState, llm: LLMClient) -> dict:
    retries = state.get("retries", 0) + 1
    answer = generate_answer(
        llm,
        state["question"],
        state["docs"],
        state.get("history", []),
        unsupported=state.get("unsupported_claims"),
    )
    return {
        "answer": answer,
        "retries": retries,
        "grounded": True,  # accept the stricter rewrite without looping forever
        "trace": [{"step": "regenerate", "detail": "rewrote with stricter grounding rules", "ts": _now()}],
    }


def web_search(state: AgentState) -> dict:
    """Free web-search fallback (no API key). Results are clearly labelled as
    general information, never as company policy."""
    try:
        from ddgs import DDGS

        results = DDGS().text(state["question"], max_results=3) or []
    except Exception:
        results = []
    return {
        "web_results": results,
        "trace": [{"step": "web_search", "detail": f"{len(results)} public web results", "ts": _now()}],
    }


def web_generate(state: AgentState, llm: LLMClient) -> dict:
    if not llm.available:
        return {"demo": True}
    answer = generate_web_fallback(llm, state["question"], state.get("web_results", []))
    return {
        "answer": answer,
        "demo": True,
        "web_results": [],
        "trace": [{"step": "web_generate", "detail": "answered from web (labelled as general info)", "ts": _now()}],
    }


def no_docs(state: AgentState, llm: LLMClient) -> dict:
    return {
        "answer": prompts.NO_DOCS_ANSWER,
        "citations": [],
        "trace": [{"step": "no_docs", "detail": "no relevant policy found after retries", "ts": _now()}],
    }


def direct_generate(state: AgentState, llm: LLMClient) -> dict:
    if not llm.available:
        return {"demo": True, "trace": [{"step": "generate", "detail": "skipped (no API key)", "ts": _now()}]}
    answer = generate_direct(llm, state["question"], state.get("history", []))
    return {"answer": answer, "trace": [{"step": "generate", "detail": "direct answer (no retrieval)", "ts": _now()}]}


def smalltalk_generate(state: AgentState, llm: LLMClient) -> dict:
    if not llm.available:
        return {"demo": True, "trace": [{"step": "generate", "detail": "skipped (no API key)", "ts": _now()}]}
    answer = generate_smalltalk(llm, state["question"])
    return {"answer": answer, "trace": [{"step": "generate", "detail": "smalltalk reply", "ts": _now()}]}
