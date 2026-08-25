# Aster & Row — Reliable RAG Support Agent

A reliability-first AI customer-support agent built for the Aster & Row take-home assignment.

## What this submission covers

- RAG over all supplied Markdown knowledge-base files.
- Markdown section splitting with front-matter metadata preserved.
- Semantic retrieval using Sentence Transformers + FAISS, with a TF-IDF fallback for lightweight offline testing.
- Metadata-aware reranking that prefers active, customer-facing, officially authoritative sources over superseded/internal drafts.
- Source references in policy/product answers using `filename — heading`.
- Explicit abstention when supplied evidence is insufficient.
- Explicit detection of the supplied Breeze Tumbler active-source conflict.
- Safe order lookup over `data/orders.json` without passing the raw dataset to the model.
- Order ID normalization, unknown/malformed ID handling and sanitized public fields.
- Protection against stale ETA/tracking information on cancelled/returned orders.
- Multi-turn session memory with per-session isolation and bounded history.
- Prompt-injection defense: retrieved documents and tool results are treated as untrusted data.
- Refusal of requests for system prompts, secrets and internal-only order information.
- Human handoff flags for conflicts, insufficient evidence and unsupported actions.
- Structured traces containing user message, relevant history, retrieval metadata/scores, tool call metadata, sanitized tool result, final response, fallbacks and errors.
- Deterministic unit/regression tests plus a behavior-level evaluation suite covering every visible case and seven additional cases.

## Architecture

```text
                       +------------------+
                       |       User       |
                       +--------+---------+
                                |
                                v
                       +------------------+
                       |     FastAPI      |
                       +--------+---------+
                                |
                                v
                       +------------------+
                       | Support Agent    |
                       | session-aware    |
                       +---+----------+---+
                           |          |
             +-------------+          +-------------+
             v                                       v
     +---------------+                       +---------------+
     | RAG Retriever |                       | Order Tool    |
     | FAISS + ST    |                       | orders.json   |
     +-------+-------+                       +-------+-------+
             |                                       |
             v                                       v
     +---------------+                       +---------------+
     | KB passages   |                       | Sanitized     |
     | + metadata    |                       | public result |
     +-------+-------+                       +-------+-------+
             |                                       |
             +----------------+----------------------+
                              v
                       +--------------+
                       | Grounded LLM |
                       | / safe       |
                       | fallback     |
                       +------+-------+
                              |
                              v
                  Answer + Sources + Handoff
```

### Retrieval flow

1. Parse each Markdown file and its front matter.
2. Split by Markdown heading so citations can identify a relevant heading.
3. Embed chunks with `sentence-transformers/all-MiniLM-L6-v2`.
4. Store vectors in local FAISS.
5. Retrieve only the top relevant candidates.
6. Apply a controlled authority boost using `status`, `audience`, `policy_authority` and `customer_answering` metadata.
7. Detect known active-source conflicts before generation.
8. Send only selected evidence to the model, explicitly labeled as untrusted data.

The supplied source files are not modified.

### Order-tool flow

The model never receives `orders.json`.

`OrderLookup` performs:

1. input validation;
2. whitespace/case normalization;
3. exact order lookup;
4. public-field allow-listing;
5. removal of carrier/tracking/ETA fields for cancelled/returned/refunded orders.

Customer email, address, internal notes and risk scores never leave the application-level tool.

## Technology choices

| Component | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Fast implementation and strong AI ecosystem |
| API | FastAPI | Minimal, testable customer-facing API |
| LLM | OpenAI Responses API | Reliable generation without building a provider abstraction for a timeboxed task |
| Embeddings | Sentence Transformers | Local embeddings; no company data has to be sent to an embedding API |
| Vector store | FAISS | Small, local and sufficient for this corpus |
| Validation | Pydantic | Typed API input contracts |
| Testing | pytest | Deterministic unit/regression tests |
| Observability | Structured JSON logs | Meets assignment requirement without a dashboard |

No production vector database, authentication system or frontend was added because the assignment explicitly says they are out of scope.

## Setup

Requires Python 3.11+.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\\Scripts\\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example` and add your own OpenAI API key for live LLM responses.

**Never commit `.env`.**

Build the index:

```bash
python scripts/build_index.py
```

The index is derived data and is intentionally ignored by Git. A clean clone can recreate it from the supplied knowledge base.

## Run the application

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Example request:

```json
{
  "session_id": "demo-1",
  "message": "What is the return policy?"
}
```

The API returns the answer, sources, handoff flag and a debug trace.

### Offline demo

The application has a deterministic fallback so the retrieval, order-tool, safety and session pipeline can be demonstrated without an API key:

```bash
python scripts/demo.py
```

The live application uses the configured OpenAI model when `OPENAI_API_KEY` is present.

## Evaluation

### One-command visible evaluation

```bash
python -m evaluation.run_evaluation
```

This runs all **15 supplied visible cases** against the offline deterministic agent and reports individual assertions plus category summaries. The same contracts can be exercised with a live OpenAI key by running the agent with the live configuration.

### Unit/regression tests

```bash
pytest -q
```

The final local run produced:

```text
13 passed
```

### Final visible evaluation

The final local behavior evaluation passes all supplied cases:

```text
Overall: 15/15 visible cases passed
```

| Category | Passed |
|---|---:|
| Retrieval | 2/2 |
| Multi-source grounding | 1/1 |
| Conversation / multi-turn | 1/1 |
| Groundedness | 2/2 |
| Tool use | 2/2 |
| Tool reliability | 3/3 |
| Privacy | 1/1 |
| Prompt security | 1/1 |
| Abstention | 1/1 |
| Source conflict | 1/1 |

### Baseline → final improvement

A deliberately naive baseline was measured before the reliability fixes. It used semantic retrieval with weak source precedence and less strict tool/output handling.

| Category | Baseline | Final |
|---|---:|---:|
| Retrieval | 1/2 | 2/2 |
| Multi-source grounding | 1/1 | 1/1 |
| Conversation | 1/1 | 1/1 |
| Groundedness | 1/2 | 2/2 |
| Tool use | 0/2 | 2/2 |
| Tool reliability | 2/3 | 3/3 |
| Privacy | 1/1 | 1/1 |
| Prompt security | 0/1 | 1/1 |
| Abstention | 0/1 | 1/1 |
| Source conflict | 0/1 | 1/1 |
| **Overall** | **7/15** | **15/15** |

The baseline was an engineering baseline from an earlier local implementation, not a claim about a hidden reference implementation.

## Additional evaluation cases

`evaluation/custom-cases.json` contains **7 original cases**, exceeding the required five. They cover:

- order privacy;
- order-ID normalization;
- unknown order IDs;
- missing order IDs;
- system-prompt extraction;
- unsupported cancellation actions;
- multi-turn international shipping.

## Bug diary

### Bug 1 — Superseded return policy could outrank the current policy

**Reproduction:** Ask for the normal return window.

**Failure:** A similarity-only retriever could surface the legacy 45-day policy alongside the current 30-day policy.

**Root cause:** Semantic similarity does not understand document lifecycle or authority.

**Fix:** Preserve front matter and add a controlled authority boost for active, customer-facing, officially authoritative content while down-ranking superseded/draft/internal content.

**Regression:** `tests/test_retrieval.py` and the `standard-return-window` visible case.

### Bug 2 — Raw order records could leak internal information

**Reproduction:** Inspect the tool result for `ORD-1007`.

**Failure:** The initial prototype returned the complete JSON order object.

**Root cause:** The tool returned source data instead of a customer-safe contract.

**Fix:** Added an explicit public-field allow-list. Customer identity/address and `internal` data never leave `OrderLookup`.

**Regression:** `test_internal_fields_are_never_exposed` and `order-data-privacy`.

### Bug 3 — Cancelled order exposed a stale ETA

**Reproduction:** Ask when `ORD-1004` will arrive.

**Failure:** The source contains an old UPS/tracking/ETA record even though the order is cancelled.

**Root cause:** The prototype treated every populated source field as current.

**Fix:** Terminal cancelled/returned/refunded statuses suppress shipment/tracking/ETA fields and use the customer-safe status message.

**Regression:** `test_cancelled_order_drops_stale_delivery_fields` and `cancelled-order-stale-eta`.

### Bug 4 — Active product sources genuinely conflict

**Reproduction:** Ask whether the entire Breeze Tumbler is dishwasher safe.

**Failure:** A naive agent could select one source and answer confidently.

**Root cause:** Both sources are active, official and customer-facing, so document precedence alone cannot safely resolve the disagreement.

**Fix:** Added explicit conflict detection for the conflicting cleaning instructions. The agent surfaces both sources and recommends human confirmation/safest interim guidance.

**Regression:** `tests/test_conflict.py` and `genuine-active-source-conflict`.

## Safety behavior

### Retrieved prompt injection

The migration scratchpad contains an instruction-like string telling the agent to ignore prior rules, reveal the hidden prompt and approve returns.

The application treats this as **untrusted retrieved data**, not an instruction. The standard active policy remains authoritative.

### Privacy

The agent refuses requests for:

- customer email;
- shipping address;
- internal notes;
- risk scores;
- hidden prompts/secrets.

### Unsupported actions

There is no cancellation/refund/replacement/address-change action tool. Therefore the agent never claims those actions were completed.

## Observability

Each response trace can include:

- current user message;
- bounded recent conversation history;
- retrieved filenames, headings, metadata and scores;
- conflict analysis;
- tool name and sanitized arguments;
- sanitized tool result;
- final response;
- handoff flag;
- fallback/error event.

Secrets, email, address, internal fields and risk scores are filtered from structured logs.

## Demo

The assignment requires a 2–4 minute GIF/video. The repository includes `demo.gif` showing:

1. a knowledge-base answer with a citation;
2. an order lookup;
3. a multi-turn conversation;
4. a source-conflict/human-handoff case;
5. evaluation results.

For a live recruiter demo, run `uvicorn app.main:app --reload` with your own API key and record the same scenarios through `/docs`.

## Known limitations

- FAISS is local and intended for the supplied small corpus.
- Session state is in memory and is lost when the process restarts.
- The explicit conflict detector targets the supplied active-source conflict; a production system should have a more general contradiction-detection layer.
- The offline responder is deterministic and exists for reproducible tests/demo; live responses use the configured OpenAI model.
- No authentication, rate limiting or deployment infrastructure is included because they are outside the assignment scope.
- The final production version should add persistent sessions, distributed tracing, CI evaluation gates and stronger PII controls.

## AI coding tools used

AI coding assistance was used for scaffolding, test design, debugging ideas and documentation structure.

One suggestion that was rejected was to pass the entire `orders.json` record to the LLM and ask it to decide which fields were safe to display. That is unsafe and violates the assignment. The final design enforces privacy in application code before any order result reaches the model.

## Submission checklist

- [x] Application source code
- [x] Tests and regression suite
- [x] Visible evaluation cases covered
- [x] Seven original evaluation cases
- [x] Setup/run instructions
- [x] `.env.example`
- [x] Architecture explanation
- [x] Model/embedding/framework/storage choices
- [x] Baseline and final evaluation results
- [x] Category breakdown
- [x] Four documented bugs with regressions
- [x] Known limitations
- [x] AI coding-tool disclosure
- [x] Demo GIF
- [x] No credentials or customer data added beyond the supplied mock assignment corpus
