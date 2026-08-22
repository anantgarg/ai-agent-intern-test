

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


---



| Goal | Command |
|---|---|
| Chat | `npm run chat` |
| Chat + traces | `DEBUG=1 npm run chat` |
| Evaluate | `npm run eval` |
| Typecheck | `npm run typecheck` |

In chat: `/reset` · `/debug` · `/quit`
