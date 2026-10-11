# PolicyPilot Learning Guide — every concept, in plain English

This guide explains every technique used in the project **through this project's own
code**, then gives the interview question each concept answers. Read one section, open
the file it points to, and it will make sense.

---

## 1. What RAG actually is

**Problem:** LLMs only know their training data. Ask Gemini about *your company's leave
policy* and it will either refuse or make something up.

**RAG (Retrieval-Augmented Generation)** = before answering, **retrieve** relevant
passages from your own documents and hand them to the LLM as context, with the
instruction *"answer only from these, and cite them"*.

In this project: `core/generator.py` builds that prompt; the numbered chunks come from
the retriever; the model's answer cites them as `[1]`, `[2]`...

> **Interview Q:** "Explain RAG simply."
> *"It's open-book exams for LLMs: instead of trusting memory, we fetch the relevant
> pages and make the model answer from them with citations."*

## 2. Embeddings (`core/embeddings.py`)

An embedding turns text into a **list of numbers (a vector)** where similar meanings
end up close together. "How many vacation days?" and "annual leave entitlement" use
different words but produce nearby vectors — that's why search works on *meaning*.

We use `all-MiniLM-L6-v2`: 384 numbers per chunk, runs free on your CPU.

> **Interview Q:** "What is an embedding?"
> *"A learned numeric representation of text such that distance approximates semantic
> similarity. I use 384-dim MiniLM vectors, normalized, compared with cosine similarity."*

## 3. Vector database (`core/vectorstore.py`)

A database optimized to store millions of vectors and find the **k nearest** to a query
vector fast (approximate nearest neighbour search). We use **ChromaDB**, which persists
to disk — restart the server and the index is still there.

> **Interview Q:** "Which vector DBs have you used and why Chroma?"
> *"Chroma for this scale — simple, persistent, metadata filtering. Pinecone/Qdrant/
> pgvector when you need managed scale or existing Postgres."*

## 4. Chunking (`core/ingestion.py`)

You can't embed a whole PDF. You split it into **chunks** (here ~900 characters with
150 overlap so a sentence cut at a boundary also exists whole in the next chunk).

The subtle, high-value detail: our chunks are cut **at section headings**. A chunk that
mixes "Password Requirements" with "Data Classification" retrieves badly for both.
This one change is what took retrieval to 100% hit-rate — a great before/after story.

> **Interview Q:** "How do you choose chunk size?"
> *"Small enough to be topically pure, big enough to be self-contained. I measured:
> section-aware 900-char chunks with 150 overlap hit 100% hit-rate@5 on my eval set."*

## 5. Hybrid search + Reciprocal Rank Fusion (`core/retriever.py`, `core/bm25.py`)

Vector search finds *meaning*, but misses **exact words** — try asking vector-only
search for "Rs. 1,500" or "WPA3". **BM25** is classic keyword search; it nails exact
terms but misses paraphrases. Production systems use **both**, then merge the two
rankings with **Reciprocal Rank Fusion**: each chunk scores
`sum(1 / (60 + rank))` across lists.

> **Interview Q:** "Why not just vector search?"
> *"I measured queries where exact numbers/policy codes matter. Hybrid + RRF covers
> both paraphrase and exact-term failure modes; it's the default in production RAG."*

## 6. Reranking (also `core/retriever.py`)

Retrieval speed comes from cheap first-pass methods. A **cross-encoder** then reads
*(query, chunk)* pairs together and scores true relevance much more accurately — but
it's slow, so we only rerank the top ~8 candidates. We use `ms-marco-MiniLM-L-6-v2`.

> **Interview Q:** "Bi-encoder vs cross-encoder?"
> *"Bi-encoder embeds query and doc separately — fast, searchable. Cross-encoder reads
> the pair jointly — accurate but O(candidates). I use bi-encoder for recall, cross-
> encoder to rerank for precision."*

## 7. The agent & LangGraph (`agent/graph.py`, `agent/nodes.py`)

A **RAG pipeline** is a fixed assembly line. An **agent** is a pipeline with *decisions
and loops*. **LangGraph** implements it as a state machine: nodes are functions that
read/write a shared state, edges can be conditional.

Our loop, in `graph.py`:

```
rewrite → route ─┬─ policy_docs → retrieve → grade ─┬─ relevant? → generate → audit ─┬─ grounded → done
                 ├─ general    → answer directly     ├─ nothing?  → retry (broader)   └─ not → regenerate (stricter)
                 └─ smalltalk  → chat               └─ still none? → web search (labelled!) or refuse
```

Every node appends a step to `state["trace"]` — that's what the UI's step-pills show,
and it's the difference between *claiming* you built an agent and *showing* it.

> **Interview Q:** "What makes your system 'agentic'?"
> *"Dynamic routing, a retrieval-relevance grader, and self-correction: it rewrites and
> re-retrieves when grading fails and regenerates when the hallucination audit finds
> unsupported claims. Implemented as a LangGraph state machine with conditional edges."*

## 8. Tool calling (`nodes.py: web_search`)

**Tool calling** = the model (or graph) can invoke functions instead of only producing
text. Here, when the policy corpus has nothing relevant, the agent calls a **web search
tool** (`ddgs`, no API key needed) and the generator *must label results as general
information, not company policy*.

> **Interview Q:** "Give an example of tool calling in your project."
> *"A web-search fallback tool the agent invokes only after grading fails twice; the
> prompt forces clear labelling so policy answers never silently come from the internet."*

## 9. Hallucination guardrails (`check_grounded` in `nodes.py`)

Three layers, in order: (1) prompt contract — "answer ONLY from numbered chunks";
(2) **grader** — an LLM discards irrelevant chunks before generation; (3) **auditor** —
a separate LLM check compares every claim in the draft against the sources; unsupported
claims trigger exactly one stricter regeneration, then the system accepts or disclaims.

> **Interview Q:** "How do you reduce hallucinations?"
> *"Grounded prompting, relevance grading pre-generation, a post-generation audit with
> regeneration, citations in the UI, and refusal when retrieval is empty. Guardrails are
> layers, not one trick."*

## 10. Prompt engineering (`core/prompts.py`)

For pipelines, prompt engineering = **designing contracts**: fixed output formats
(JSON for graders), explicit refusal language, exact-number quoting, citation syntax.
Every prompt here states its output format and `llm.extract_json` tolerates markdown
fences when parsing.

> **Interview Q:** "Show me a prompt you engineered."
> *"The router returns strict JSON `{'route': ..., 'reason': ...}`; the generator must
> cite chunk numbers and quote figures exactly; the auditor returns
> `{'grounded': bool, 'unsupported_claims': [...]}` that drives a graph edge."*

## 11. Evaluation (`scripts/evaluate.py`, `data/eval/golden_qa.json`)

You can't improve what you don't measure. We built a **golden QA set** (22 questions
with reference answers and the exact expected document+section) and measure:

- **Retrieval hit-rate@k** — right document AND right section in top-k? (100% @5 here)
- **Faithfulness (LLM-as-judge)** — is every claim supported by sources?
- **Correctness (LLM-as-judge)** — does it match the reference?
- Latency and the agent's trace per question.

These are the same four metrics the **RAGAS** library popularized — we implemented them
transparently instead of importing them.

> **Interview Q:** "How do you know your RAG works?"
> *"A 22-question golden set from the corpus, hit-rate@5 for retrieval, LLM-as-judge
> for faithfulness/correctness, saved reports. Chunking decisions were made from those
> numbers, not vibes."*

## 12. FastAPI + SSE streaming (`routers/chat.py`)

`POST /api/chat` returns a **Server-Sent Events** stream: first `trace`, then
`sources`, then `token` events, then `done`. That's why the UI feels live. Sessions,
messages and feedback persist in SQLite; documents in ChromaDB.

> **Interview Q:** "Why SSE over WebSockets?"
> *"One-directional server→client streaming over plain HTTP; simpler auth/proxying,
> works through nginx with buffering off. WebSockets only if the client must stream too."*

## 13. Docker & deployment

Two images: `backend/Dockerfile` (python-slim + uvicorn) and `frontend/Dockerfile`
(node build stage → nginx serving static files and proxying `/api` with `proxy_buffering
off` for SSE). `docker compose up` runs both. The README has the AWS EC2 steps.

> **Interview Q:** "How would you deploy this?"
> *"Compose on a small EC2 to start; model and index on a mounted volume. For scale:
> move Chroma to a managed service, put Rerank/LLM behind queues, add health checks and
> CI. I kept the README's EC2 path concrete."*

---

## Study path (2 weeks, ~1 hour/day)

1. **Day 1-2:** run the app (README quickstart). Ask it 10 questions. Watch the trace bar.
2. **Day 3-4:** `core/ingestion.py` + `embeddings.py` + `vectorstore.py`. Re-run
   `scripts/ingest.py`. Explain chunking out loud.
3. **Day 5-6:** `bm25.py` + `retriever.py`. Change `FINAL_K` in config, watch answers change.
4. **Day 7-8:** `prompts.py` + `generator.py`. Break a prompt on purpose; see what degrades.
5. **Day 9-10:** `agent/` — trace one question on paper: which nodes ran and why.
6. **Day 11-12:** `scripts/evaluate.py` — run both layers; read `reports/eval_report.md`.
7. **Day 13-14:** frontend + Docker. Then push to GitHub with a 30-second demo GIF.

**Rule for interviews:** never say a word you can't trace to a file you can open and
explain. With this repo, you always can.
