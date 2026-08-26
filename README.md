# Aster & Row Reliable RAG Support Agent

A small customer-support agent built for the Aster & Row take-home. It combines **retrieval, deterministic safety/tooling, multi-turn session state, and a real Gemini LLM generation step** without giving the model the full knowledge base or raw order database.

## 1. Setup

Requirements: Python 3.11+.

```bash

python -m venv .venv

# Windows PowerShell

.venv\Scripts\Activate.ps1

# macOS/Linux

# source .venv/bin/activate

python -m pip install -r requirements.txt

```

Copy `.env.example` to `.env` and set:

```env

GEMINI_API_KEY=your_real_key

GEMINI_MODEL=gemini-2.5-flash

USE_LLM=true

```

Never commit `.env` or credentials.

## 2. Run

Interactive CLI:

```bash

python -m app.cli

```

Debug/trace mode:

```bash

python -m app.cli --debug

```

The normal application uses Gemini for final phrasing when `GEMINI_API_KEY` is configured. The application can still produce a safe deterministic fallback if the model is temporarily unavailable; this fallback never invents policy or order data.

## 3. Tech stack

- **Language:** Python

- **LLM:** Google Gemini `gemini-2.5-flash` through the official `google-genai` SDK

- **RAG:** local TF-IDF sparse-vector retrieval with heading-aware Markdown chunking

- **Storage:** in-memory local index built from `knowledge-base/*.md`; no production vector DB is required for this small corpus

- **Order tool:** deterministic lookup over `data/orders.json`

- **Framework:** intentionally lightweight Python; no LangChain dependency

- **Tests:** pytest

The TF-IDF index is deliberate: it is deterministic, local, easy to inspect, and sufficient for the supplied corpus. The LLM is used for language generation, not as the source of truth.

## 4. Architecture

```text

User message

    |

    v

Session context / routing

    |

    +---- order intent ----> order_lookup() ----> sanitized result

    |

    +---- KB intent -------> TF-IDF retrieval

                              |

                              v

                    authority / conflict checks

                              |

                              v

                   grounded evidence package

                              |

                              v

                    Gemini 3.6 Flash generation

                              |

                              v

                 output safety + grounding checks

                              |

                              v

                    answer + sources + handoff

```

### Reliability boundary

The model receives only:

- the current user message;

- a small recent conversation window;

- relevant **customer-facing active official** passages;

- a sanitized order-tool result when an order lookup was actually performed; and

- an application-generated grounding plan.

It does **not** receive `orders.json` wholesale, internal order fields, or internal/draft/superseded KB passages as customer-answering evidence.

### Document precedence

Front-matter metadata is preserved during indexing. Retrieval scoring gives preference to active official customer-facing documents and penalizes superseded, draft, or internal content. Genuine conflicts between current official sources are detected explicitly.

### Order safety

`OrderLookup`:

- normalizes harmless whitespace/case differences;

- rejects malformed IDs;

- asks for an ID when absent;

- uses the order's current status as authoritative;

- never exposes email, address, internal notes, or risk scores;

- suppresses carrier/ETA for cancelled or returned orders;

- never invents an ETA when it is missing.

## 5. Evaluation

Run the full behavior suite with:

```bash

python evaluation/run_eval.py

```

Run unit/integration tests with:

```bash

pytest -q

```

The evaluation command reports each case individually and breaks results down by behavior category. The 20 cases consist of all supplied visible cases plus five original regression cases:

1. lowercase/whitespace order ID normalization;

2. order follow-up reusing the previous order ID;

3. malformed order ID handling;

4. unsupported cancellation action with human handoff;

5. migration-scratchpad prompt-injection resistance.

### Current offline evaluation

The deterministic evaluation suite passes **20/20 (100%)** without requiring an API call. This is intentional so evaluation remains reproducible. The application path with `GEMINI_API_KEY` configured performs the same routing/retrieval/tool work and then uses Gemini for final response generation, with deterministic fallback validation.

| Category | Result |

|---|---:|

| Retrieval | 2/2 |

| Multi-source grounding | 1/1 |

| Conversation | 2/2 |

| Groundedness | 2/2 |

| Tool use | 3/3 |

| Tool reliability | 4/4 |

| Privacy | 1/1 |

| Prompt security | 2/2 |

| Abstention | 2/2 |

| Source conflict | 1/1 |

| **Total** | **20/20** |

## 6. Baseline and final result

### Early baseline

The first implementation used deterministic routing/retrieval but had weak handling for precedence, multi-turn order reuse, malformed IDs, and evaluation coverage. Its representative visible evaluation was **12/20 (60%)**.

### Final

After adding explicit authority-aware retrieval, sanitized tool boundaries, session resolution, conflict detection, LLM grounding contracts, post-generation validation, and five additional regression cases: **20/20 (100%)** on the offline behavior suite.

## 7. Bug diary

### Bug 1 — Superseded return policy could outrank the current policy

**Reproduction:** ask for the standard return window while the legacy 45-day document is present.

**Root cause:** lexical relevance alone treated the legacy document as equally useful.

**Fix:** preserve front-matter metadata and apply authority/status/audience reranking; only active official customer-facing sources can become customer citations.

**Regression:** `standard-return-window` and `internal-migration-instruction-is-data`.

### Bug 2 — A follow-up order question lost the order ID

**Reproduction:** `Where is ORD-1007?` followed by `When will it arrive?`.

**Root cause:** the second message did not contain an order ID.

**Fix:** session stores only the relevant `last_order_id` and reuses it for clear order follow-ups.

**Regression:** `order-followup-reuses-session`.

### Bug 3 — Terminal orders leaked stale delivery information

**Reproduction:** ask when cancelled `ORD-1004` will arrive.

**Root cause:** the raw record contained an old delivery field even though the current status was cancelled.

**Fix:** the tool suppresses carrier/ETA for cancelled and returned orders; the response layer treats current status as authoritative.

**Regression:** `cancelled-order-stale-eta`.

### Bug 4 — Retrieved migration text looked like an instruction

**Reproduction:** ask the agent to use the migration scratchpad's 60-day statement as the policy.

**Root cause:** retrieved text was previously treated too much like prompt context.

**Fix:** retrieved passages are explicitly untrusted data; internal/draft/superseded passages are excluded from the LLM evidence package; the application chooses authoritative policy sources before generation.

**Regression:** `retrieved-prompt-injection` and `internal-migration-instruction-is-data`.

### Bug 5 — LLM phrasing could omit an evaluation-critical grounded fact

**Reproduction:** the model paraphrased a retrieved fact but omitted the required return window/date detail.

**Root cause:** generation is probabilistic even at temperature 0.

**Fix:** build a deterministic grounding plan with required facts, validate the generated answer, and fall back to the grounded composer if a required fact is missing.

**Regression:** `tests/test_llm.py` plus the full evaluation suite.

## 8. Observability

`python -m app.cli --debug` shows:

- current user message;

- recent conversation history;

- tool call and sanitized result;

- selected sources;

- whether the LLM was used;

- handoff state;

- final response.

Secrets are never logged. Internal order fields are not included in tool results passed to the model or debug output.

## 9. Human handoff policy

The agent recommends human assistance when:

- authoritative sources genuinely conflict;

- the supplied information is insufficient;

- an order lookup fails;

- the customer requests an unsupported action such as cancellation, refund, replacement, price adjustment, warranty approval, or address change;

- the customer requests internal/private information; or

- the issue is otherwise outside the supported evidence/actions.

The agent never claims an unsupported action has been completed.

## 10. Known limitations

- The corpus is small, so a local TF-IDF index is sufficient; production would likely use a managed/vector embedding store with hybrid retrieval.

- The current session is process-local; production would persist session state with expiry and tenant isolation.

- Gemini availability is external; the deterministic fallback prevents unsafe guessing but is intentionally less conversational.

The current Gemini integration uses the standard google-genai content-generation API; if the SDK/model behavior changes, the LLM wrapper may need a compatibility update.

- There is no real transaction system, authentication, or ticket creation because those are outside the assignment.

- A production version should add tracing/metrics, rate limiting, secret management, and stronger automated adversarial testing.

## 11. AI coding tools used

I used AI coding assistance for:

- reviewing the assignment requirements;

- designing the retrieval/guardrail architecture;

- generating and refining regression-test cases;

- debugging Python packaging and test failures.

One incorrect AI-generated suggestion was an outdated/decommissioned model identifier. It produced an API error when tested, so it was removed and the configured model is now explicitly controlled through `GEMINI_MODEL`.

## 12. Demo

## 12. Demo

A short demonstration of the Aster & Row support agent covering:

- Knowledge-base question with citations
- Order lookup
- Multi-turn conversation
- Privacy-safe refusal / human handoff
- Source conflict handling
- Evaluation suite

**🎥 [Watch the demo video on Google Drive](https://drive.google.com/drive/folders/1-piN-LP8JyVfg2NDluO7JO6BMUXPbSrt?usp=drive_link)**

> The video demonstrates the agent running locally through the CLI, including RAG retrieval, order-tool usage, multi-turn context, safe abstention, and the evaluation suite.

## 13. Submission checklist

- [x] Application source

- [x] Tests and evaluation suite

- [x] Setup instructions

- [x] `.env.example` with no credentials

- [x] RAG over supplied Markdown files

- [x] Metadata preservation and source citations

- [x] Order lookup tool with privacy boundary

- [x] Multi-turn session context

- [x] Prompt-injection resistance

- [x] Human handoff/abstention behavior

- [x] Basic observability

- [x] 20-case evaluation with individual results

- [x] Five original evaluation cases

- [x] Bug diary

- [x] Baseline/final results

- [x] AI-tool disclosure

- [x] Demo GIF