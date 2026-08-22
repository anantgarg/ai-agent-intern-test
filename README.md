# Steps: evaluate and submit the agent

Checklist to finish the Aster & Row take-home. Work top to bottom.

---

## A. Before you evaluate

1. Confirm Node **20+** and dependencies:
   ```bash
   npm install
   ```
2. Copy env and set a real key (never commit `.env`):
   ```bash
   cp .env.example .env
   # set OPENROUTER_API_KEY=...
   ```
3. Smoke-test the CLI:
   ```bash
   npm run chat
   ```
   Try one policy question, one order lookup (`ORD-1007`), and `/quit`.
4. Optional typecheck:
   ```bash
   npm run typecheck
   ```

---

## B. Run the evaluation suite

1. Run the full suite (visible + custom cases; live API calls):
   ```bash
   npm run eval
   ```
2. Confirm the output includes:
   - Per-case PASS/FAIL (not only a total score)
   - Category rollups (retrieval, groundedness, tool use, privacy, multi-turn, etc.)
3. If cases fail:
   - Re-run with debug while chatting: `DEBUG=1 npm run chat`
   - Inspect ranked sources / tool calls in the debug trace
   - Fix retrieval, prompts, tool sanitization, or assertions as needed
   - Re-run `npm run eval` until results look solid
4. Copy the final summary into your root **README** (overall + by category), e.g.:
   ```text
   Overall: ?/? passed
   By category:
     abstention: ?/?
     groundedness: ?/?
     multi-turn: ?/?
     privacy: ?/?
     prompt-security: ?/?
     retrieval: ?/?
     source-conflict: ?/?
     tool-use: ?/?
   ```
5. Keep an early **baseline** row as well (what improved after ranking/prompt/tool fixes). Details: [evaluation.md](./evaluation.md).

---

## C. Manual demo checks (before recording)

Walk these by hand in `npm run chat` so the GIF/video is honest:

1. Knowledge-base question with **citations** (filename + heading)
2. Order lookup (`ORD-1007` or similar) via the tool — no invented status
3. Multi-turn follow-up (e.g. international shipping → “What about Canada?”)
4. Abstention / **human handoff** (e.g. vegan materials, or tumbler care conflict)
5. Briefly show `npm run eval` running (or a clear clip of the rollup)

---

## D. README must-haves (submission checklist)

Root `README.md` should include all of these:

1. Setup + run from a clean clone
2. Required env vars + `.env.example` (no real keys)
3. Model, retrieval/embeddings approach, storage choice
4. Short architecture explanation
5. Eval command (`npm run eval`)
6. Baseline + final eval results by category
7. Bug diary (≥3 failures: repro, root cause, fix, regression)
8. Known limitations / pre-production improvements
9. AI coding tools used + one incomplete/wrong AI suggestion
10. Embedded **2–4 min GIF or video** covering the demo checks in section C

Your fuller write-up can live under `doc/` (see [project.md](./project.md)); reviewers still expect the items above in the root README.

---

## E. Repo hygiene before push

1. Ensure **no secrets**: no `.env`, API keys, or credentials in git
2. Confirm these are present:
   - Application source under `src/`
   - Eval suite (`evaluation/` + `npm run eval`)
   - `.env.example`
   - Root README with results, limitations, bug diary, demo
3. Do **not** submit separate slide decks or extra docs as the submission — only the GitHub repo link
4. `knowledge-base/` and supplied data stay unchanged (indexes/derived files are fine)

---

## F. Submit

1. Push to a public (or accessible) GitHub repository
2. Submit **one GitHub repository link** — that is all that is required
3. Double-check the link opens to the correct branch with the finished README and demo

---

## Quick command cheat sheet

| Goal | Command |
|---|---|
| Chat | `npm run chat` |
| Chat + traces | `DEBUG=1 npm run chat` |
| Evaluate | `npm run eval` |
| Typecheck | `npm run typecheck` |

In chat: `/reset` · `/debug` · `/quit`
