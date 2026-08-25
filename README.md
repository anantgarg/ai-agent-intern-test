# AI Agent Intern Take-Home: Aster & Row Reliable RAG Support Agent

## Overview

This repository contains a fully functional, highly reliable AI support agent for Aster & Row. It is designed to handle common customer inquiries, look up order statuses securely, and reliably navigate conflicting documents, prompt injections, and missing information using RAG (Retrieval-Augmented Generation).

## 1. Setup & Run Instructions

**Prerequisites:** Python 3.10+

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd ai-agent-intern-test
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
4. **Set up your environment variables:**
   - Copy the example `.env` file:
     ```bash
     cp .env.example .env
     ```
   - Add your **Fireworks API Key** inside `.env`.

5. **Run the interactive CLI agent:**
   ```bash
   python main.py
   ```
   *(You can add the `--debug` flag to see retrieved chunks, tool calls, and logic traces: `python main.py --debug`)*

## 2. Environment Variables

- `FIREWORKS_API_KEY`: Required to authenticate with the Fireworks API (or any OpenAI-compatible endpoint). See `.env.example`.

## 3. Tech Stack

- **Model**: `accounts/fireworks/models/qwen3p8-max` (via Fireworks AI). Chosen for its excellent function-calling and strict reasoning capabilities.
- **Embeddings & Storage**: `chromadb` using the local `all-MiniLM-L6-v2` ONNX model. It's lightweight, fully local, and runs seamlessly without external database setup.
- **Framework**: Standard Python with the `openai` SDK (for Fireworks compatibility). I avoided heavy abstractions like LangChain to ensure maximum observability, control over tool sanitization, and deterministic prompt structures.
- **Parsing**: `python-frontmatter` to extract metadata and cleanly chunk markdown documents.

## 4. Architecture

1. **Ingestion (`rag.py`)**: The system parses markdown files, extracts frontmatter, and chunks documents by section headers. It inserts these into an in-memory ChromaDB instance.
2. **Retrieval**: When a user asks a question, the agent performs a similarity search. The retrieved context (including status metadata) is invisibly appended to the user's message in the LLM context.
3. **Tool Sanitization (`tools.py`)**: The `lookup_order` tool acts as a strict privacy boundary. It intercepts the raw `orders.json` data and strips all PII (email, address) and internal notes/risk scores *before* returning data to the LLM. It also handles status precedence (e.g., removing stale ETAs for cancelled orders).
4. **Agent Loop (`agent.py`)**: A custom chat loop maintains multi-turn conversation history. The system prompt strongly anchors the agent against prompt injection and enforces strict rules (e.g., highlighting conflicting sources instead of guessing).

## 5. Running Evaluations

Run the automated evaluation suite (includes all visible cases + 5 custom regression tests):

```bash
python evaluate.py
```

## 6. Evaluation Results

- **Baseline Results (Initial attempt with malformed parsing)**: 
  - Passed: 0/20, Failed: 20/20.
- **Final Evaluation Results**:
  - **Total**: 20/20 (100% Pass Rate)
  - **By Category**:
    - retrieval: 3/3
    - multi-source-grounding: 1/1
    - conversation: 2/2
    - groundedness: 2/2
    - tool-use: 3/3
    - tool-reliability: 3/3
    - privacy: 2/2
    - prompt-security: 1/1
    - abstention: 2/2
    - source-conflict: 1/1

## 7. Bug Diary

1. **Model Endpoint Incompatibility (404 Not Found)**
   - **Reproduction:** Running `python evaluate.py` with `llama-v3p1-70b-instruct` resulted in all 20 cases failing with a 404 error from Fireworks AI.
   - **Root Cause:** The model ID `llama-v3p1-70b-instruct` was incorrect or unavailable for the provided key.
   - **Fix:** Switched to `accounts/fireworks/models/qwen3p8-max`, which is highly capable and active on the platform.
   - **Regression Test:** `evaluate.py` verifies the model endpoint responds successfully across all 20 tests.

2. **Tool Argument Parsing Error (`'str' object has no attribute 'get'`)**
   - **Reproduction:** During `evaluate.py`, cases requiring `order_lookup` crashed.
   - **Root Cause:** The LLM occasionally returns the tool `arguments` as a raw string instead of a valid JSON dictionary depending on the model's function-calling strictness. When `json.loads` parsed it, it remained a string, causing `.get("order_id")` to fail.
   - **Fix:** Updated `agent.py` to robustly check `isinstance(args, dict)` and fall back to string parsing.
   - **Regression Test:** Included in the `valid-order-lookup` and `custom-1-missing-order-id` cases.

3. **Database Iteration Error (`'str' object has no attribute 'get'`)**
   - **Reproduction:** After fixing the argument parsing, the tool cases failed again with the same error message deep inside `tools.py`.
   - **Root Cause:** The root of `orders.json` is a dictionary `{"dataset_name": "...", "orders": [...]}`. My code was doing `for o in orders_db`, iterating over the *keys* of the root dictionary (which are strings) instead of the list of orders.
   - **Fix:** Updated `tools.py` to extract the list properly: `orders_db = load_orders().get('orders', [])`.
   - **Regression Test:** The entire `tool-reliability` suite relies on this iteration working flawlessly.

## 8. Known Limitations & Future Improvements

- **Scalability**: ChromaDB is currently running in-memory. For production, it should connect to a persistent Vector DB (e.g., Pinecone or Postgres pgvector).
- **Hardcoded Tool Logic**: The `lookup_order` tool handles JSON arrays. In production, this would be an API call to a real database (e.g., Shopify or an OMS), which would handle its own sanitization before returning payloads.
- **Evaluation Strictness**: The evaluation currently relies on deterministic string matching (`must_include`, `must_not_include`). In a real environment, adding an "LLM-as-a-judge" for nuanced responses would provide better qualitative metrics.

## 9. AI Coding Tools Used

- **Google Gemini (Antigravity IDE Agent)**: Used to architect the solution, write the core Python logic (`agent.py`, `tools.py`, `rag.py`), execute background tasks to test and evaluate the code, and debug stack traces dynamically.
- **Example of incorrect suggestion**: The AI initially wrote `orders_db = load_orders()` and iterated over it assuming it was a JSON array, failing to realize the provided `orders.json` was wrapped in a root object containing metadata (like `dataset_name`). The AI had to read the raw JSON file to discover its own mistake.

## 10. Demonstration

Here is the demonstration of the agent in action:
[View Demo Video](https://drive.google.com/file/d/1zCkda84i_ebKuiUa4fbIihQxVgp9c7_p/view?usp=sharing)
