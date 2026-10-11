"""PolicyPilot evaluation harness.

Two layers:
  1. Retrieval hit-rate (no LLM needed): does the retriever surface the
     document/section that actually contains the answer in the top-k?
  2. LLM-as-judge (needs GEMINI_API_KEY): runs the full agent per question
     and scores faithfulness + correctness against the reference answer.

This mirrors what RAGAS measures (context precision/recall, faithfulness,
answer relevancy) in a single self-contained script with no extra deps.

Run from backend/:
    .venv/Scripts/python scripts/evaluate.py                 # both layers
    .venv/Scripts/python scripts/evaluate.py --retrieval-only
    .venv/Scripts/python scripts/evaluate.py --k 5 --out reports/eval_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import services  # noqa: E402
from app.agent.graph import run_agent  # noqa: E402
from app.config import DATA_DIR, settings  # noqa: E402
from app.core import prompts  # noqa: E402
from app.core.llm import extract_json  # noqa: E402

EVAL_SET = DATA_DIR / "eval" / "golden_qa.json"


def load_set() -> list[dict]:
    data = json.loads(EVAL_SET.read_text(encoding="utf-8"))
    return data["items"]


def retrieval_hit(item: dict, docs: list[dict]) -> bool:
    for doc in docs:
        doc_ok = item["expected_doc"].lower() in doc.get("doc_title", "").lower()
        section_ok = item["expected_section"].lower() in (doc.get("section") or "").lower()
        if doc_ok and section_ok:
            return True
    return False


def evaluate_retrieval(items: list[dict], k: int) -> list[dict]:
    results = []
    for item in items:
        start = time.perf_counter()
        docs = services.retriever.retrieve(item["question"], final_k=k)
        results.append(
            {
                "id": item["id"],
                "hit": retrieval_hit(item, docs),
                "latency_ms": round((time.perf_counter() - start) * 1000),
                "n_docs": len(docs),
            }
        )
        status = "HIT " if results[-1]["hit"] else "MISS"
        print(f"  [{status}] {item['id']} ({results[-1]['latency_ms']} ms)")
    return results


def judge_answer(item: dict, answer: str) -> dict:
    data = extract_json(
        services.llm.generate(
            prompts.JUDGE_PROMPT.format(question=item["question"], reference=item["reference"], answer=answer),
            temperature=0.0,
            json_mode=True,
        )
    )
    if not data:
        return {"faithfulness": None, "correctness": None, "note": "judge returned unparseable output"}
    return {
        "faithfulness": float(data.get("faithfulness", 0.0)),
        "correctness": float(data.get("correctness", 0.0)),
        "note": data.get("note", ""),
    }


def evaluate_end_to_end(items: list[dict], k: int) -> list[dict]:
    results = []
    for item in items:
        print(f"  running agent: {item['id']} ...", flush=True)
        start = time.perf_counter()
        try:
            state = run_agent(item["question"], [], services.llm, services.retriever, settings.web_search_enabled)
        except Exception as exc:
            results.append({"id": item["id"], "error": str(exc)})
            continue
        latency = round((time.perf_counter() - start) * 1000)
        answer = state.get("answer", "")
        scores = judge_answer(item, answer)
        hits = [c for c in state.get("citations", []) if retrieval_hit(item, [c])]
        results.append(
            {
                "id": item["id"],
                "latency_ms": latency,
                "answer": answer,
                "grounded": state.get("grounded", True),
                "cited_expected": bool(hits),
                "trace_steps": [t["step"] for t in state.get("trace", [])],
                **scores,
            }
        )
        print(f"    faith={scores['faithfulness']} correct={scores['correctness']} cited_expected={bool(hits)} ({latency} ms)")
    return results


def write_report(args, retrieval: list[dict], e2e: list[dict] | None) -> Path:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    hit_rate = sum(1 for r in retrieval if r["hit"]) / len(retrieval) if retrieval else 0.0
    lines = [
        "# PolicyPilot Evaluation Report",
        "",
        f"- Test set: {EVAL_SET.name} ({len(retrieval)} questions)",
        f"- Retrieval top-k: {args.k}",
        f"- Retrieval hit-rate@{args.k}: **{hit_rate:.0%}**",
    ]
    if e2e:
        scored = [r for r in e2e if r.get("faithfulness") is not None]
        latencies = sorted(r["latency_ms"] for r in e2e if "latency_ms" in r)
        if scored:
            avg_f = sum(r["faithfulness"] for r in scored) / len(scored)
            avg_c = sum(r["correctness"] for r in scored) / len(scored)
            cited = sum(1 for r in e2e if r.get("cited_expected"))
            lines += [
                f"- End-to-end faithfulness (LLM judge): **{avg_f:.2f}** avg over {len(scored)} scored answers",
                f"- End-to-end correctness (LLM judge): **{avg_c:.2f}**",
                f"- Answers citing the expected document+section: **{cited}/{len(e2e)}**",
            ]
            if latencies:
                lines.append(f"- Median end-to-end latency: **{latencies[len(latencies) // 2]} ms**")
    lines += ["", "| id | retrieval hit | judge scores |", "|---|---|---|"]
    for r in retrieval:
        e = next((x for x in (e2e or []) if x["id"] == r["id"]), {})
        score = (
            f"f={e['faithfulness']:.2f} c={e['correctness']:.2f}"
            if e.get("faithfulness") is not None
            else (e.get("error", "-") if e else "-")
        )
        lines.append(f"| {r['id']} | {'✅' if r['hit'] else '❌'} | {score} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out.parent / "eval_results.json").write_text(
        json.dumps({"retrieval": retrieval, "end_to_end": e2e}, indent=2), encoding="utf-8"
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5, help="final_k for retrieval hit-rate")
    parser.add_argument("--retrieval-only", action="store_true", help="skip the LLM-judge layer")
    parser.add_argument("--out", default="reports/eval_report.md", help="report output path")
    args = parser.parse_args()

    items = load_set()
    print(f"Evaluating {len(items)} questions (k={args.k})")

    print("\n--- Layer 1: retrieval hit-rate ---")
    retrieval = evaluate_retrieval(items, args.k)
    hits = sum(1 for r in retrieval if r["hit"])
    print(f"hit-rate@{args.k}: {hits}/{len(retrieval)} = {hits / len(retrieval):.0%}")

    e2e = None
    if not args.retrieval_only and services.llm.available:
        print("\n--- Layer 2: end-to-end answers + LLM judge ---")
        e2e = evaluate_end_to_end(items, args.k)
    elif not args.retrieval_only:
        print("\nLayer 2 skipped: GEMINI_API_KEY not set (run with --retrieval-only to silence this)")

    report = write_report(args, retrieval, e2e)
    print(f"\nReport written to {report}")


if __name__ == "__main__":
    main()
