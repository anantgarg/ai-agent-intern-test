# Aster & Row Support Agent

CLI support agent that answers from the knowledge base, looks up orders safely, and hands off when unsure.

---

## Setup

Node 20+.

```bash
cp .env.example .env
# set OPENROUTER_API_KEY=...

npm install
npm run chat
```

### Env vars

| Variable | Required | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter key |
| `OPENROUTER_MODEL` | No | Default `openai/gpt-4o-mini` |
| `DEBUG` | No | `1` = write traces |
| `MAX_HISTORY_TURNS` | No | Default `8` |
| `RETRIEVAL_TOP_K` | No | Default `6` |

Do not commit `.env`.

Chat commands: `/reset` · `/debug` · `/quit`

---

## Stack

| Piece | Choice |
|---|---|
| Model | OpenRouter (`openai/gpt-4o-mini`) |
| Retrieval | BM25 (no embeddings) |
| Storage | In-memory index from `knowledge-base/` |
| Orders | `lookup_order` on `data/orders.json` |
| UI | CLI |

---

## Architecture

```text
message → history → BM25 retrieve → model (+ order tool) → answer + sources + handoff
```

- Prefer current official docs over old/internal ones  
- Never invent order status  
- Never expose email, address, or internal fields  
- If info is missing or sources conflict → say so and suggest a human  

---

## Evaluation

```bash
npm run eval
```

Runs `evaluation/visible-cases.json` + 5 custom cases. Prints per-case PASS/FAIL and category totals.

### Baseline → final

| Check | Baseline | Final |
|---|---|---|
| Standard return finds current policy | Often wrong section | Top results |
| Tumbler conflict finds both docs | Partial | Both in top-k |
| Messy order ID (`  ord-1007 `) | Weak | Normalized, PII stripped |
| Cancelled order ETA | Could leak stale ETA | Cleared |

**Final live results** (`openai/gpt-4o-mini`):

```text
Overall: 20/20 passed
By category:
  abstention: 1/1
  groundedness: 2/2
  multi-turn: 3/3
  privacy: 1/1
  prompt-security: 1/1
  retrieval: 4/4
  source-conflict: 1/1
  tool-use: 7/7
```

---

## Bug diary

**1. Wrong returns section ranked first**  
Repro: “How long to return an unused backpack?”  
Cause: BM25 matched “return” everywhere.  
Fix: Heading boost + filename diversity.  
Regression: `standard-return-window`, `paraphrased-standard-return`.

**2. Cancelled orders showed ETA**  
Repro: Ask arrival time for a cancelled order.  
Cause: Tool returned raw fields.  
Fix: Clear shipping fields when status is cancelled/returned.  
Regression: `cancelled-order-stale-eta`.

**3. Internal note treated like policy**  
Repro: Prompt-injection text from migration notes.  
Cause: Draft/internal docs not demoted enough.  
Fix: Strong demotion + system rules ignore embedded instructions.  
Regression: `retrieved-prompt-injection`.

**4. “What about Canada?” lost context**  
Repro: International shipping → Canada follow-up.  
Cause: Retrieval used only the short follow-up.  
Fix: Include recent user turns in the query.  
Regression: `canada-multiturn`, `order-then-arrival-followup`.

---

## Limitations

- BM25 can miss odd paraphrases  
- Soft eval wording can fail even when the answer is right  
- History is in-memory only  
- Lookup only — no refunds/cancellations/address changes  
- Live eval = cost + small variance  
- Next: denser retrieval for paraphrases; persistent sessions  

---

## AI tools

Used **Cursor** for scaffolding, retrieval/tool loop, eval harness, and README.

**Incomplete AI suggestion:** “Just BM25 + tell the model to ignore old docs.” Not enough — ranking needed heading boost and diversity.

---

## Demo

Add your 2–4 min GIF/video here (policy + citations, order lookup, multi-turn, handoff, `npm run eval`).

```markdown
![demo](./demo.gif)
```
