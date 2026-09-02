# AI Agent Intern Take-Home: Build a Reliable RAG Support Agent

## The assignment

Aster & Row is a fictional ecommerce company that sells bags, drinkware, and travel accessories. The company wants to launch an AI support agent using the documents and mock order data in this repository.

This repository intentionally contains **only content and data**. There is no starter application and no prescribed stack. Build the smallest reliable system you would be comfortable demonstrating to a customer.

## Timebox

Please spend **6–8 hours** on the assignment. Do not exceed eight hours.

A smaller, well-tested system is better than a broad system that works only in a demo. It is acceptable to leave something incomplete if the limitation is clearly documented.

## Submission

Submit **one GitHub repository link**. Nothing else is required.

Your repository must contain:

- Your application source code.
- Your tests and evaluation suite.
- Clear setup and run instructions.
- Evaluation results and known limitations in the README.
- A short GIF or video embedded in the README showing the agent working.

Do not submit API keys, credentials, customer data, separate documents, or slide decks.

---

## Customer scenario

Aster & Row has previously tried several AI support prototypes. The customer reported four recurring problems:

1. **Conflicting policy answers:** The agent sometimes says the return window is 30 days and sometimes says it is 45 days.
2. **Invented order information:** The agent occasionally gives an order status without actually looking it up.
3. **Lost conversation context:** Follow-up questions such as “What about Canada?” are treated as unrelated questions.
4. **Unsafe retrieved content:** Internal or instruction-like text inside the knowledge base can affect the agent’s behavior.

The supplied corpus contains realistic data-quality problems, including superseded content, internal notes, conflicting active sources, and fields that must not be shown to customers.

Your task is to build an agent that handles these conditions deliberately rather than succeeding only on ideal questions.

---

# Required capabilities

## 1. Retrieval-Augmented Generation

Use RAG over the Markdown files in `knowledge-base/`.

Your implementation must:

- Split and index the supplied documents.
- Preserve useful metadata from the document front matter.
- Retrieve only relevant passages instead of sending the entire corpus to the model.
- Prefer authoritative, active policy documents over superseded or non-policy documents.
- Include source references in every policy or product answer. A source should identify at least the filename and relevant heading.
- Avoid making claims that are not supported by the retrieved content.
- Clearly say when the supplied information is insufficient.
- Surface genuine conflicts between current authoritative sources rather than silently choosing one.

Do not delete or rewrite the supplied source files to make the assignment easier. You may create derived indexes or normalized representations.

## 2. Order lookup as a tool or function

Use `data/orders.json` to implement an order-status lookup tool or function.

The model must **not** receive the entire orders file in its prompt. It should receive only the result of a lookup when order information is actually required.

The order lookup behavior must:

- Ask for an order ID when it is missing.
- Handle unknown and malformed order IDs safely.
- Normalize harmless input differences such as lowercase IDs or surrounding whitespace.
- Use the order’s current `status` as authoritative.
- Avoid inventing a delivery estimate when one is unavailable.
- Avoid reporting stale delivery fields for cancelled or returned orders.
- Never expose customer email, address, internal notes, risk scores, or other internal-only fields.
- Never claim that a lookup happened when it did not.

Assume that possession of the order ID is sufficient authentication for this mock assignment. You do not need to build a full identity-verification system.

## 3. Multi-turn conversation

Maintain relevant session context across turns.

The agent should correctly handle follow-ups such as:

- “Do you ship internationally?” followed by “What about Canada?”
- “Where is `ORD-1007`?” followed by “When will it arrive?”
- A policy question followed by a narrower question about an exception.

The agent should not carry unrelated details indefinitely or mix one session with another.

## 4. Prompting and agent behavior

The agent must:

- Treat user messages, retrieved passages, and tool results as untrusted data.
- Follow application instructions rather than instructions found inside retrieved documents.
- Refuse requests to reveal system prompts, hidden instructions, secrets, or internal-only data.
- Use company content rather than general model knowledge for company-specific questions.
- Ask a concise clarifying question when required information is missing.
- Recommend human assistance when the documents conflict, the data is insufficient, or an action cannot be completed.
- Never promise that a refund, cancellation, replacement, or address change has been completed unless the system actually supports that action.

## 5. Evaluation suite

The file `evaluation/visible-cases.json` contains behavior-level cases that your system must handle.

Build an evaluation suite that:

- Covers every supplied visible case.
- Adds at least **five original cases** of your own.
- Can be run using one clearly documented command.
- Reports individual case results, not only a single overall score.
- Separately reports useful categories such as retrieval, groundedness, tool use, privacy, and multi-turn behavior.
- Uses deterministic assertions wherever practical, including source selection, tool calls, tool arguments, forbidden disclosures, and abstention behavior.
- Does not rely exclusively on another LLM to grade the agent.

The reviewers will also test paraphrases and combinations that are not included in the visible file. Do not hardcode answers for the supplied prompts.

As you build, keep a small **bug diary** in your README. Document at least three failures you found in your own agent, including:

- How you reproduced the failure.
- The actual root cause.
- The change you made.
- The regression test that now catches it.

At least one documented failure should be something you discovered beyond the exact wording of the visible cases. Include an early baseline and final evaluation result so we can see what improved.

## 6. Basic observability

Provide a debug mode, trace, or log that makes it possible to inspect:

- The current user message.
- Relevant conversation history.
- Retrieved passages, metadata, and scores.
- Tool calls and sanitized tool results.
- The final response.
- Errors, fallbacks, or handoffs.

Plain structured logs are sufficient. Do not build a dashboard. Never log secrets.

## 7. Minimal interface

A CLI, simple web page, or basic API is sufficient. Visual polish will not affect the score.

The final user-facing response should make it easy to see:

- The answer.
- Sources, when applicable.
- Whether the agent is recommending a human handoff.

---

# README requirements

Your completed repository README must include:

1. Setup and run instructions that work from a clean clone.
2. Required environment variables and an `.env.example` without real credentials.
3. The model, embedding approach, framework, and storage approach you chose.
4. A short architecture explanation.
5. The command for running evaluations.
6. Baseline and final evaluation results, broken down by category.
7. A bug diary covering at least three reproduced failures, root causes, fixes, and regression tests.
8. Known limitations and what you would improve before production.
9. Which AI coding tools you used, what you used them for, and one example of an AI-generated suggestion that was wrong or incomplete.
10. A **2–4 minute GIF or video embedded in the README** demonstrating:
   - One knowledge-base question with citations.
   - One order lookup.
   - One multi-turn conversation.
   - One case where the agent correctly refuses to guess or recommends human help.
   - The evaluation suite running.

GitHub does not play uploaded video files inline in every context. An embedded GIF or a clickable video thumbnail/link inside the README is acceptable.

---

# What not to spend time on

You do not need to build:

- Authentication or user management.
- Production deployment infrastructure.
- A production vector database.
- Fine-tuning.
- A polished frontend.
- Multiple model-provider integrations.
- Billing, analytics dashboards, or administration screens.

---

# Evaluation criteria

| Area | Weight |
|---|---:|
| Reliability, groundedness, and safe abstention | 25% |
| Retrieval quality and document precedence | 20% |
| Tool use, data handling, and privacy | 15% |
| Evaluation quality and regression coverage | 20% |
| Multi-turn behavior and observability | 10% |
| Code clarity and practical tradeoffs | 5% |
| README, demo, and customer-facing clarity | 5% |

Framework choice and quantity of code are not scoring criteria.

---

# Repository contents

```text
.
├── README.md
├── knowledge-base/
│   ├── 01-returns-policy-current.md
│   ├── 02-returns-policy-legacy.md
│   ├── 03-final-sale-and-promotions.md
│   ├── 04-damaged-or-wrong-items.md
│   ├── 05-domestic-shipping.md
│   ├── 06-international-shipping.md
│   ├── 07-warranty.md
│   ├── 08-order-changes-and-cancellations.md
│   ├── 09-trailplus-membership.md
│   ├── 10-gift-cards-and-price-adjustments.md
│   ├── 11-product-care.md
│   ├── 12-breeze-tumbler-product-card.md
│   ├── 13-support-escalation.md
│   └── 14-internal-content-migration-notes.md
├── data/
│   ├── orders.json
│   └── orders-data-dictionary.md
└── evaluation/
    └── visible-cases.json
```

Good luck. Build for reliability, not just for the happy-path demo.

# Aster & Row Support Agent

A RAG-based customer support agent for the fictional ecommerce company
Aster & Row, built for the CometChat AI Agent Intern assessment.

## Setup

```bash
git clone <this-repo-url>
cd ai-agent-intern-test
python -m venv venv
source venv/Scripts/activate   # Windows/Git Bash; use venv/bin/activate on Mac/Linux
pip install chromadb groq python-dotenv
cp .env.example .env           # then add your GROQ_API_KEY
python src/ingest.py           # builds the local vector index (one-time)
```

Get a free Groq API key at https://console.groq.com (no credit card
required).

## Running it

```bash
python src/cli.py                    # interactive chat
python src/evaluation.py             # run the full evaluation suite
python src/evaluation.py --category tool-use   # run one category only
python src/logger.py                 # inspect the last few logged turns
```

Type `debug` inside the CLI to toggle inline display of retrieved
context for each query.

## Architecture
knowledge-base/*.md ---ingest.py---> chroma_db/ (local vector store)
|
data/orders.json ---order_tool.py---> order_lookup()
|
retriever.py
(retrieve + precedence
+ conflict detection)
|
agent.py
(system prompt + tool-calling + LLM)
/
cli.py evaluation.py
|
logger.py (structured JSONL logs)

**Ingestion (`ingest.py`):** Parses each knowledge-base file's YAML
front-matter (`status`, `document_id`, `policy_authority`,
`customer_answering`) separately from its body, splits the body into
chunks at each `##` heading, and stores each chunk with its metadata
in a local ChromaDB collection.

**Retrieval (`retriever.py`):** Runs a similarity search, then sorts
hits into three buckets based on front-matter metadata:
- **Authoritative** (`status: active`, `policy_authority: official`) —
  safe to answer from directly.
- **Background** (`status: superseded`) — historical context only.
- **Non-authoritative** (`customer_answering: false` or
  `policy_authority: none`) — e.g. the internal migration scratchpad;
  never used as a basis for an answer.

It also flags when more than one authoritative source is retrieved for
the same query, which the agent then has to decide is a real conflict
(e.g. product-care vs. product-card disagreeing on the Breeze Tumbler)
or just complementary information.

**Order tool (`order_tool.py`):** Looks up `data/orders.json` by
normalized order ID and returns *only* a fixed whitelist of
customer-safe fields (status, carrier, tracking, etc.). Everything
under `customer.*` and `internal.*` — including a warehouse note that
itself contains an embedded prompt-injection attempt — is stripped
before the result ever reaches the model. Status-specific rules are
applied here too (e.g. a cancelled order's stale ETA is blanked out
rather than left for the model to reason about).

**Agent (`agent.py`):** A 15-rule system prompt (see below) plus
Groq's OpenAI-compatible tool-calling API. Treats all retrieved
content and tool results as untrusted data, never as instructions.

**Evaluation (`evaluation.py`):** Runs every case in
`evaluation/visible-cases.json` and `evaluation/custom-cases.json`
through the agent and checks the response against each case's
`expect` block using deterministic checks (no LLM-as-judge): substring
matching (with Unicode-dash/space normalization and date-equivalence
fallback), source-citation checks, and tool-call inspection.

**Logging (`logger.py`):** Every turn is appended as one JSON line to
`logs/conversation_log.jsonl` with the user message, the full
retrieved-context block (with per-source labels), any tool calls made
(name, arguments, sanitized result), and the final response.

## Model / embedding / framework choices

- **LLM:** `openai/gpt-oss-20b` via the **Groq** API (free tier, no
  credit card required, supports OpenAI-style tool calling). Chosen
  specifically because I had no budget for a paid API.
- **Embeddings:** ChromaDB's default local model
  (`all-MiniLM-L6-v2`, sentence-transformers), downloaded once and run
  locally — free, and more than sufficient for a 14-document corpus.
- **Vector store:** ChromaDB, file-based/local — no external service
  needed for a corpus this size, per the assignment's own note.
- **Framework:** No LangChain/LlamaIndex. The corpus is small and the
  requirements (citation precedence, conflict surfacing, injection
  defense) needed close control over prompt construction, which was
  simpler to reason about directly against the Groq SDK.
- **Interface:** A plain CLI (`cli.py`). Polish wasn't a scoring
  criterion; the CLI supports a `debug` toggle for inline retrieval
  inspection.

## Evaluation results

Deterministic checks against `evaluation/visible-cases.json` (15
cases) plus 5 custom cases in `evaluation/custom-cases.json` (see
below). Because the underlying LLM is not fully deterministic,
repeated runs vary slightly — the table shows an early baseline vs.
the state after the fixes documented in `BUG_DIARY.md`.

| Run | Cases passed |
|---|---|
| Baseline (first working version) | 4 / 15 |
| After fixing citation, date-formatting, and evaluator-matching bugs | 12–13 / 15 (typical range across repeated runs) |

Category breakdown (representative run):

| Category | Result |
|---|---|
| retrieval | 2/2 |
| groundedness | 2/2 |
| tool-use | 2/2 |
| tool-reliability | 3/3 |
| privacy | 1/1 |
| source-conflict | 1/1 |
| abstention | 1/1 |
| conversation | 1/1 |
| multi-source-grounding | 1/1 |
| prompt-security | 0–1/1 (see known limitations) |

## Custom test cases

Five additional cases in `evaluation/custom-cases.json`, covering gaps
not exercised by the supplied visible cases:

1. **`order-warehouse-note-injection`** — tests a prompt-injection
   attempt embedded in a *tool result* (`orders.json`'s
   `internal.warehouse_note` for ORD-1005), as distinct from the
   knowledge-base-embedded injection the visible cases already cover.
2. **`cancel-after-shipped`** — cancellation-window policy combined
   with an actual order lookup.
3. **`trailplus-unconfirmed-membership`** — the agent must not assume
   TrailPlus membership just because the customer claims it.
4. **`gift-card-refund-request`** — exercises the gift-card policy
   file, untested by the visible cases.
5. **`address-change-processing-order`** — address-change limits
   combined with an order lookup.

## Bug diary

See [`BUG_DIARY.md`](./BUG_DIARY.md) for 6 documented bugs found
during development (reproduction, root cause, fix, regression test),
plus a note on the non-determinism limitation.

## Known limitations

- **Response non-determinism.** The same prompt can produce slightly
  different wording (or occasionally a different citation choice)
  across runs. The evaluation script tolerates paraphrase where
  reasonable (word-root matching, date-format equivalence,
  hyphen/space normalization), but a small amount of run-to-run
  variance in the pass count is expected.
- **Free-tier rate limits.** Groq's free tier caps both tokens/minute
  and tokens/day. `evaluation.py` adds a delay between cases and
  `agent.py` retries with the exact wait time Groq reports, but a full
  day's testing budget can still be exhausted by repeated runs.
- **Embeddings are a local sentence-transformer model**, not a
  large-scale embedding API — fine for this 14-document corpus, but
  would not necessarily scale to a much larger knowledge base without
  revisiting retrieval quality.
- **The concept-matching in `evaluation.py`** (`must_include_concepts`)
  uses word-root/synonym heuristics, not semantic matching, so it can
  occasionally under- or over-match compared to a human or LLM judge.

## AI tools used

This project was built in conversation with Claude (Anthropic), used
for architecture planning, code generation, and debugging throughout.

One incorrect suggestion worth flagging: Claude initially recommended
reducing the retriever's `TOP_K` from 5 to 3 purely to cut token usage
after hitting Groq's rate limits. This actually caused a regression —
with fewer chunks retrieved, the correct policy document sometimes
dropped out of the retrieved set entirely for certain queries (e.g.
the `retrieved-prompt-injection` case stopped retrieving
`01-returns-policy-current.md` at all, and the Canada-shipping duties
clause stopped being retrieved for the `canada-multiturn` case). The
fix was to raise `TOP_K` back to 5 once the rate-limit issue was
solved properly (via retry-with-backoff instead of shrinking context),
rather than trading away retrieval quality for token savings.

## Demo

See `demo.gif`/`demo.mp4` (to be recorded) showing: a knowledge-base
Q&A with citations, an order lookup, a multi-turn conversation, a
refusal/human-handoff case, and the evaluation suite running.
