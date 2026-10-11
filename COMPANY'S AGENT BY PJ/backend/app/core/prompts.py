"""All LLM prompts in one place. Every prompt is explicit about the output
format because downstream code parses it - this is the core of prompt
engineering for pipelines (not chat, but contract design)."""

SYSTEM_RULES = """You are PolicyPilot, a precise enterprise knowledge assistant.
Rules you must always follow:
1. Answer ONLY from the numbered context chunks you are given. Never invent facts.
2. Cite every claim with the chunk number in square brackets, e.g. [2].
3. If the context does not contain the answer, say plainly:
   "I could not find this in the indexed policies." and suggest what to check.
4. Be concise and structured. Use short bullets where helpful.
5. Quote exact numbers (day counts, amounts, deadlines) exactly as written."""

REWRITE_QUERY_PROMPT = """Rewrite the user's question so it retrieves the right policy
documents. Expand abbreviations (WFH -> work from home, PL -> privileged leave), add
likely section keywords, keep it under 40 words. Reply with ONLY the rewritten query.

Conversation so far:
{history}

User question: {question}"""

ROUTER_PROMPT = """Classify the user's latest message into exactly one category:
- "policy_docs": asks about company policies, HR, IT rules, benefits, procedures, or
  anything that needs the indexed documents.
- "general": answerable without documents (explaining a concept, meta questions about
  this assistant, general knowledge).
- "smalltalk": greetings, thanks, or social messages.

Reply with JSON only: {{"route": "...", "reason": "one short sentence"}}

Latest message: {question}"""

GRADE_PROMPT = """You grade retrieved document chunks for a policy Q&A system.
Question: {question}

Chunk [{idx}] (source: {source}, page {page}, section: {section}):
{chunk}

Is this chunk USEFUL for answering the question? Judge whether it contains relevant
facts, even if partial. Reply JSON only:
{{"relevant": true}} or {{"relevant": false}}"""

GENERATE_PROMPT = """{rules}

Context chunks from the company policy library, each numbered:

{context}

Recent conversation:
{history}

User question: {question}

Write the answer now, following every rule above."""

HALLUCINATION_PROMPT = """You audit an AI answer against its sources.

Question: {question}

Sources (numbered chunks):
{context}

Answer to audit:
{answer}

Check every factual claim in the answer against the sources. Reply JSON only:
{{"grounded": true|false, "unsupported_claims": ["claim", ...], "verdict": "one short sentence"}}"""

RETRY_GENERATE_PROMPT = """{rules}

IMPORTANT: A previous draft of this answer contained claims not present in the sources:
{unsupported}

Context chunks from the company policy library, each numbered:

{context}

Recent conversation:
{history}

User question: {question}

Write the corrected answer now. Only state what the sources literally support."""

NO_DOCS_ANSWER = """I could not find this in the indexed policies.

The retrieval and grading steps did not surface any relevant chunks for this question.
Things to try:
- Upload the policy document that would contain this answer
- Rephrase using words a policy document would use (e.g. "annual leave carry forward")"""

SMALLTALK_PROMPT = """You are PolicyPilot, a friendly enterprise assistant for company
policies. Reply to the message naturally in 1-3 sentences and, if it fits, mention that
you can answer questions about HR, IT and workplace policies.

Message: {question}"""

DIRECT_PROMPT = """You are PolicyPilot, an enterprise knowledge assistant. The user's
question does not require the indexed policy documents. Answer helpfully in under 120
words. If the question is actually about company policies, say you can look it up in
the indexed policies if they ask again.

Recent conversation:
{history}

Question: {question}"""

WEB_FALLBACK_PROMPT = """{rules}

NOTE: The company policy library had nothing relevant, so these are PUBLIC WEB results.
They are NOT company policy - clearly label them as general information, not company
policy, and recommend confirming with HR.

Web results:
{web_context}

User question: {question}"""

JUDGE_PROMPT = """You evaluate a RAG system's answer for one test question.

Test question: {question}

Reference answer (ground truth): {reference}

System answer: {answer}

Score strictly:
- "faithfulness": 1.0 if every factual claim in the system answer is supported by the
  reference, 0.0 if it contradicts it, partial score for extra unsupported claims.
- "correctness": how well the system answer matches the reference on the key facts
  (0.0 to 1.0).
Reply JSON only: {{"faithfulness": 0.0, "correctness": 0.0, "note": "one sentence"}}"""
