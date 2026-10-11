"""Shared state for the LangGraph agent.

The state is a plain TypedDict; every node receives it and returns a dict of
fields to update. LangGraph handles the plumbing between nodes.
"""
from __future__ import annotations

from typing import Annotated, TypedDict


def merge_trace(current: list, update: list) -> list:
    """Trace is append-only so the UI can show the agent's full decision path."""
    return (current or []) + (update or [])


class AgentState(TypedDict):
    # inputs
    question: str
    history: list[dict]

    # intermediate
    rewritten_query: str
    route: str                      # policy_docs | general | smalltalk
    route_reason: str
    docs: list[dict]                # retrieved + graded relevant chunks
    rejected: int                   # chunks the grader rejected
    retries: int
    web_results: list[dict]

    # outputs
    answer: str
    citations: list[dict]           # per-citation info used by the UI
    grounded: bool
    unsupported_claims: list[str]
    demo: bool

    # observability
    trace: Annotated[list[dict], merge_trace]
