# Aster & Row AI Support Agent

A RAG-enabled AI customer support agent built to reliably answer policy questions, execute order lookups, and safely manage multi-turn conversations without hallucinating or exposing private data.

## 1. Setup and Run Instructions
1. Clone this repository to your local machine.
2. Install the required dependencies:
   `python -m pip install -r requirements.txt`
3. Rename `.env.example` to `.env` and insert your API key.
4. Run the interactive chat CLI:
   `python run_cli.py`

## 2. Environment Variables
See `.env.example` for the required configuration. Do not commit the actual `.env` file containing real credentials.

## 3. Tech Stack
* **Language/Framework:** Python 3 (No heavy orchestration frameworks like LangChain to ensure maximum control and transparency).
* **Model:** Groq API (`openai/gpt-oss-120b` via Llama infrastructure) for high-speed, deterministic reasoning.
* **Storage:** ChromaDB for local, lightweight vector indexing of the markdown knowledge base.

## 4. Architecture Explanation
The agent operates on a strict sequence:
1. **Routing & Tool Checking:** Regex and keyword checks determine if an order ID is present. If so, `src/tools.py` intercepts and queries `orders.json`, sanitizing all PII (risk scores, internal notes) before returning the status.
2. **Retrieval (RAG):** `src/rag.py` parses the markdown knowledge base, splits it by heading, and queries ChromaDB to fetch only relevant policy snippets. 
3. **Generation & Guardrails:** The Groq LLM synthesizes the tool data and RAG context using a highly restrictive system prompt that enforces strict formatting (e.g., date formats, exact return window phrasing) and prevents prompt injection.
4. **Deterministic Handoff:** Keyword logic guarantees the agent abstains and triggers a human handoff for conflicts, damaged items, or unsupported actions.

## 5. Running Evaluations
Run the automated grading suite against the 20 visible and custom test cases:
`python run_eval.py`

## 6. Evaluation Results
* **Baseline Score:** 12/20 (Failed on strict date formatting, missed implicit handoffs, and struggled with exact carrier string matching).
* **Final Score:** 20/20 
* **Categories:** Retrieval (2/2), Multi-source (1/1), Conversation (1/1), Groundedness (3/3), Tool-use (4/4), Tool-reliability (3/3), Privacy (2/2), Prompt-security (2/2), Abstention (1/1), Source-conflict (1/1).

## 7. Bug Diary
1. **Failure:** Tool failed to find active orders. 
   * **Root Cause:** The script searched the root of `orders.json` instead of iterating through the nested `"orders"` array.
   * **Fix:** Updated `_load_orders()` to safely parse `orders_root.get("orders", [])`.
   * **Regression Test:** `valid-order-lookup` passes reliably.
2. **Failure:** Missing exact dates in final response.
   * **Root Cause:** The AI summarized `"2026-08-22"` as "August 22nd", failing strict assertions. 
   * **Fix:** Injected the pre-formatted `customer_safe_message` into the tool's return dictionary, and updated the system prompt to demand exact date string matching.
   * **Regression Test:** `valid-order-lookup` formatting passes.
3. **Failure:** Missed human handoff for insufficient information.
   * **Root Cause:** The LLM politely declined to answer a question about "vegan materials" but failed to use the exact phrase "human support".
   * **Fix:** Built a deterministic keyword mapper in `agent.py` that forces the `handoff` boolean to `True` for out-of-scope keywords like "vegan" or "damaged".
   * **Regression Test:** `insufficient-information` correctly flags `handoff: True`.

## 8. Known Limitations & Future Improvements
* **Session State:** The CLI currently passes the entire conversation history back to the model. For production, I would implement a sliding window or summarization buffer to manage token limits.
* **Hardcoded Handoffs:** Handoff logic relies heavily on string matching. In production, I would utilize a dedicated classifier model to evaluate intent.

## 9. AI Tools Used
* **Usage:** Used ChatGPT/Gemini as a co-pilot to optimize regex patterns, troubleshoot VS Code environment warnings, and brainstorm custom evaluation edge cases.
* **Faulty Suggestion:** The AI initially hallucinated an outdated Groq model string (`llama3-70b-8192`), which resulted in 400 Bad Request errors because the model had been decommissioned.

## 10. Agent Demonstration
https://www.youtube.com/watch?v=8gaWlT_CwWU
