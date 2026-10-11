"""Wire the agent nodes into a LangGraph state machine.

Flow (policy questions):
    rewrite -> route -> retrieve -> grade -> generate -> audit -> citations
                            ^        |
                            |        +--> retry (broadened query) --> grade
                            +--> web_search fallback --> generate (labelled)

Flow (everything else):
    rewrite -> route -> direct answer / smalltalk -> citations
"""
from __future__ import annotations

import time

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import AgentState
from app.core.llm import LLMClient


def _now() -> float:
    return round(time.time() * 1000)


def build_citations(state: AgentState) -> dict:
    docs = state.get("docs", [])
    return {
        "citations": [
            {
                "index": i + 1,
                "doc_title": d.get("doc_title", ""),
                "page": d.get("page"),
                "section": d.get("section") or "",
                "source": d.get("source", ""),
                "chunk_id": d.get("chunk_id", ""),
                "snippet": d["text"][:400],
                "score": round(d.get("score", 0.0), 3),
            }
            for i, d in enumerate(docs)
        ]
    }


def build_graph(llm: LLMClient, retriever, web_enabled: bool):
    graph = StateGraph(AgentState)
    graph.add_node("rewrite_query", lambda s: nodes.rewrite_query(s, llm))
    graph.add_node("route", lambda s: nodes.route(s, llm))
    graph.add_node("retrieve", lambda s: nodes.retrieve(s, retriever))
    graph.add_node("grade_documents", lambda s: nodes.grade_documents(s, llm))
    graph.add_node("retry_retrieve", lambda s: nodes.retry_retrieve(s, retriever, llm))
    graph.add_node("web_search", lambda s: nodes.web_search(s))
    graph.add_node("generate", lambda s: nodes.generate(s, llm))
    graph.add_node("check_grounded", lambda s: nodes.check_grounded(s, llm))
    graph.add_node("regenerate", lambda s: nodes.regenerate(s, llm))
    graph.add_node("web_generate", lambda s: nodes.web_generate(s, llm))
    graph.add_node("direct_generate", lambda s: nodes.direct_generate(s, llm))
    graph.add_node("smalltalk_generate", lambda s: nodes.smalltalk_generate(s, llm))
    graph.add_node("no_docs", lambda s: nodes.no_docs(s, llm))
    graph.add_node("build_citations", build_citations)

    graph.add_edge(START, "rewrite_query")
    graph.add_edge("rewrite_query", "route")

    def after_route(s: AgentState) -> str:
        return {
            "policy_docs": "retrieve",
            "general": "direct_generate",
            "smalltalk": "smalltalk_generate",
        }[s["route"]]

    graph.add_conditional_edges("route", after_route, {"retrieve": "retrieve", "direct_generate": "direct_generate", "smalltalk_generate": "smalltalk_generate"})
    graph.add_edge("direct_generate", "build_citations")
    graph.add_edge("smalltalk_generate", "build_citations")

    def after_grading(s: AgentState) -> str:
        if s.get("docs"):
            return "generate"
        if s.get("retries", 0) < 1:
            return "retry_retrieve"
        if web_enabled and llm.available:
            return "web_search"
        return "no_docs"

    graph.add_edge("retrieve", "grade_documents")
    graph.add_conditional_edges(
        "grade_documents",
        after_grading,
        {"generate": "generate", "retry_retrieve": "retry_retrieve", "web_search": "web_search", "no_docs": "no_docs"},
    )
    graph.add_edge("retry_retrieve", "grade_documents")
    graph.add_edge("web_search", "web_generate")
    graph.add_edge("web_generate", "build_citations")
    graph.add_edge("no_docs", "build_citations")

    def after_audit(s: AgentState) -> str:
        if s.get("demo"):
            return "finish"
        if s.get("grounded", True) or s.get("retries", 0) > 1:
            return "finish"
        return "regenerate"

    graph.add_edge("generate", "check_grounded")
    graph.add_conditional_edges("check_grounded", after_audit, {"finish": "build_citations", "regenerate": "regenerate"})
    graph.add_edge("regenerate", "build_citations")

    graph.add_edge("build_citations", END)
    return graph.compile()


def run_agent(question: str, history: list[dict], llm: LLMClient, retriever, web_enabled: bool) -> AgentState:
    app_graph = build_graph(llm, retriever, web_enabled)
    start = _now()
    final = app_graph.invoke(
        {"question": question, "history": history, "retries": 0, "trace": [{"step": "start", "detail": "agent invoked", "ts": start}]},
        {"recursion_limit": 25},
    )
    final["trace"].append({"step": "end", "detail": f"completed in {_now() - start} ms", "ts": _now()})
    return final
