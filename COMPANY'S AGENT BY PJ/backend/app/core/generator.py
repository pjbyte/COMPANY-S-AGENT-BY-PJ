"""Answer generation: build the grounded prompt and (optionally) stream."""
from __future__ import annotations

from app.core import prompts
from app.core.llm import LLMClient


def format_context(docs: list[dict]) -> str:
    parts = []
    for i, doc in enumerate(docs, start=1):
        header = (
            f"[{i}] source: {doc.get('doc_title', 'unknown')} | "
            f"page {doc.get('page', '?')} | section: {doc.get('section') or 'n/a'}"
        )
        parts.append(f"{header}\n{doc['text']}")
    return "\n\n".join(parts)


def format_history(history: list[dict], max_messages: int = 8) -> str:
    """history = [{'role': 'user'|'assistant', 'content': str}, ...]"""
    trimmed = history[-max_messages:]
    if not trimmed:
        return "(none)"
    return "\n".join(f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in trimmed)


def generate_answer(
    llm: LLMClient,
    question: str,
    docs: list[dict],
    history: list[dict],
    unsupported: list[str] | None = None,
) -> str:
    context = format_context(docs)
    hist = format_history(history)
    if unsupported:
        prompt = prompts.RETRY_GENERATE_PROMPT.format(
            rules=prompts.SYSTEM_RULES,
            unsupported="\n".join(f"- {c}" for c in unsupported),
            context=context,
            history=hist,
            question=question,
        )
    else:
        prompt = prompts.GENERATE_PROMPT.format(
            rules=prompts.SYSTEM_RULES,
            context=context,
            history=hist,
            question=question,
        )
    return llm.generate(prompt)


def generate_direct(llm: LLMClient, question: str, history: list[dict]) -> str:
    return llm.generate(
        prompts.DIRECT_PROMPT.format(history=format_history(history), question=question)
    )


def generate_smalltalk(llm: LLMClient, question: str) -> str:
    return llm.generate(
        prompts.SMALLTALK_PROMPT.format(question=question), temperature=0.6
    )


def generate_web_fallback(llm: LLMClient, question: str, web_results: list[dict]) -> str:
    web_context = format_context(
        [
            {
                "text": f"{r.get('title', '')}\n{r.get('body', '')}\nURL: {r.get('href', '')}",
                "doc_title": "Web result",
                "page": "-",
                "section": "",
            }
            for r in web_results
        ]
    )
    return llm.generate(
        prompts.WEB_FALLBACK_PROMPT.format(rules=prompts.SYSTEM_RULES, web_context=web_context, question=question)
    )
