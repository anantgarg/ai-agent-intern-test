# Aster & Row AI Support Agent

A reliable, deterministic Retrieval-Augmented Generation (RAG) support agent built for Aster & Row. Handles company policies, product information, order lookups, multi-turn conversations, conflict detection, and safety enforcement without inventing data or exposing sensitive customer details.

---

## 1. Quick Setup & Run Instructions

### Prerequisites
- **Python 3.10+** (Tested on Python 3.13.7)

### Clean Clone & Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/<your-username>/ai-agent-intern-test.git
   cd ai-agent-intern-test
   ```

2. **Create & Activate Virtual Environment**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

5. **Run the Interactive CLI**
   ```bash
   python -m app.main
   ```

6. **Run the Evaluation Suite**
   ```bash
   python -m pytest -v
   ```

---

## 2. Environment Variables & `.env.example`

The project includes an `.env.example` file:

```ini
# Environment Configuration
DEBUG_LOGGING=true

# Optional: OPENAI_API_KEY is not required for local TF-IDF execution.
# OPENAI_API_KEY=your_optional_api_key_here
```

No external API keys or credentials are required. The system runs 100% locally out of the box using TF-IDF vector indexing and deterministic rule engines.

---

## 3. Tech Stack & Architectural Choices

| Component | Choice / Approach | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.13 | High developer velocity, rich NLP/ML ecosystem. |
| **Vector Retrieval** | Local TF-IDF + Cosine Similarity (`scikit-learn`) | Deterministic, zero-latency, zero-cost, runs completely offline. |
| **Text Analyzer** | Custom Regex Stemming Analyzer | Resolves word inflections (e.g. `ship` / `ships` / `shipping`, `return` / `returns`). |
| **Policy Authority Engine** | YAML Front-matter Metadata Weighting | Preferentially weights `active` & `official` sources over `superseded` or `draft` content. |
| **Storage** | Local Markdown (`knowledge-base/`) & JSON (`data/orders.json`) | Lightweight, zero-dependency data storage. |
| **State Management** | In-Memory `ConversationState` | Preserves order IDs, topics, and session history across turns. |
| **Testing** | `pytest` | Comprehensive unit, integration, and evaluation assertion suite. |

---

## 4. Architecture Explanation

```
                          [ User Input ]
                                |
                                v
               [ Step 1: Sensitive Data Guardrail ]
             (Refuses System Prompts & Secrets)
                                |
         +----------------------+----------------------+
         |                                             |
         v                                             v
  [ Order Lookup Intent ]                     [ Policy Question Intent ]
  - Checks Order ID                           - TF-IDF Stemmed Search
  - Normalizes Whitespace/Case                - Authority-Score Weighting
  - Queries data/orders.json                  - Genuine Conflict Detection
  - Sanitizes Private Fields                  - Multi-Section Chunk Join
         |                                             |
         +----------------------+----------------------+
                                |
                                v
                [ Output & Observability Logger ]
           - Answers with Citations / Tool Result
           - Human Handoff Recommendation (if needed)
           - Writes trace to logs/agent_trace.jsonl
```

### Key Subsystems
1. **Front-Matter Metadata Parser (`app/rag.py`)**: Extracts `document_id`, `status`, `policy_authority`, `audience`, and `supersedes` metadata from Markdown front-matter.
2. **Authority Ranking Engine (`app/rag.py`)**: Computes `final_score = score + authority_score`. Gives `+6.0` boost to active official customer policies while deprioritizing draft/internal migration notes.
3. **Conflict Detection Engine (`app/rag.py`)**: Automatically detects genuine contradictions between active official documents (e.g., return window conflicts or product care contradictions).
4. **Order Lookup Tool (`app/orders.py`)**: Normalizes order IDs (`ORD-1007`), redacts private customer fields (`email`, `address`, `risk_score`, `notes`), and protects against stale ETAs on cancelled/returned orders.
5. **Session State Manager (`app/agent_state.py`)**: Remembers context across multi-turn sessions (e.g., order ID follow-ups and shipping follow-ups).

---

## 5. Evaluation Command & Category Results

### Run Evaluation Command
```bash
python -m pytest tests/test_evaluation.py -v
```

### Overall Suite Result
Run all 55 tests across unit, integration, visible behavior, and evaluation suites:
```bash
python -m pytest -v
```
**Result**: **55 / 55 Passed (100% Pass Rate)** in **2.57 seconds**.

### Evaluation Breakdown by Category

| Category | Baseline Score | Final Score | Pass Rate | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Retrieval** | 4 / 6 | 6 / 6 | 100% | PASSED |
| **Groundedness & Authority** | 3 / 4 | 4 / 4 | 100% | PASSED |
| **Tool Use & Order Lookup** | 6 / 6 | 6 / 6 | 100% | PASSED |
| **Privacy & Security** | 3 / 3 | 3 / 3 | 100% | PASSED |
| **Multi-Turn Conversation** | 2 / 3 | 3 / 3 | 100% | PASSED |
| **Conflict Handling** | 1 / 2 | 2 / 2 | 100% | PASSED |
| **Abstention & Handoff** | 2 / 3 | 3 / 3 | 100% | PASSED |
| **Original Extension Cases** | 0 / 6 | 6 / 6 | 100% | PASSED |
| **TOTAL** | **21 / 33 (63.6%)** | **34 / 34 (100%)** | **100%** | **PASSED** |

---

## 6. Bug Diary (Root Cause Analysis & Fixes)

### Bug 1: Superseded Policy Document Overpowering Active Policy
- **Reproduction**: User asked `"How long does a regular customer have to return an unused backpack?"`.
- **Root Cause**: Raw TF-IDF score of `02-returns-policy-legacy.md` (0.2818) was slightly higher than `01-returns-policy-current.md` (0.2226) because the legacy document was shorter. The document selection loop sorted by raw TF-IDF score before authority score.
- **Fix**: Changed candidate sorting to use `final_score = score + authority_score`, giving active official documents a +6.0 authority boost over superseded ones.
- **Regression Test**: `tests/test_agent_requirements.py::test_policy_answer_contains_source` & `tests/test_rag.py::test_rank_results_prefers_authoritative_content`.

### Bug 2: Multi-Turn Context Fragmentation on International Shipping
- **Reproduction**: Turn 1: `"Do you ship internationally?"` -> Turn 2: `"What about Canada, and how long does it take?"`.
- **Root Cause**: Retrieval selected only 1 section (`Supported destinations`) of `06-international-shipping.md`, omitting the `Canada delivery estimate` chunk ("5–9 business days after dispatch") located in another section.
- **Fix**: Updated RAG answer assembly to collect all active chunks from the matched authoritative source document (`best["filename"]`) in logical document order.
- **Regression Test**: `tests/test_visible_behaviors.py::test_canada_multiturn`.

### Bug 3: False Grounding on Undocumented & Insufficient Information Queries *(Discovered Beyond Visible Wording)*
- **Reproduction**: User asked `"What is the policy for something that is not documented?"` & `"Are all fabrics and adhesives in your bags vegan?"`.
- **Root Cause**: Generic word matches (`policy`, `fabric`) produced weak TF-IDF similarity scores (~0.17) against irrelevant chunks (`08-order-changes-and-cancellations.md Agent limitations` and `11-product-care.md`), causing the agent to answer with irrelevant text instead of abstaining.
- **Fix**: Added explicit keyword verification and score thresholding. When retrieved active chunks lack query keywords (e.g., `vegan`, `undocumented`) or active score is insufficient, the agent returns `handoff = True` with a clear abstention message.
- **Regression Test**: `tests/test_agent_integration.py::test_agent_hands_off_when_information_is_insufficient` & `tests/test_evaluation.py::test_original_case_5_unsupported_vegan_material_claim`.

---

## 7. Basic Observability & Debug Logging

When `DEBUG_LOGGING=true` is set in `.env`, the agent logs structured JSON traces to `logs/agent_trace.jsonl`:

```json
{
  "user_message": "Where is ORD-1007 and when should it arrive?",
  "history": [
    {"role": "user", "content": "Where is ORD-1007 and when should it arrive?"}
  ],
  "sources": [],
  "tool_call": {
    "name": "lookup_order",
    "arguments": {"order_id": "ORD-1007"},
    "result": {"found": true, "status": "shipped", "carrier": "UPS"}
  },
  "handoff": false,
  "answer": "Order ORD-1007 is currently shipped. Carrier: UPS. Estimated delivery: August 22, 2026."
}
```

*Note: Sensitive customer details (email, address, internal notes, risk score) are automatically sanitized and never logged.*

---

## 8. Demo GIF / Video

[![Aster & Row Support Agent Demo](https://img.shields.com/badge/Demo-Watch%20Agent%20in%20Action-blue?style=for-the-badge&logo=youtube)](file:///d:/Projects/ai-agent-intern-test/docs/demo.gif)

*(Embedded GIF demonstrating knowledge-base citation, order lookup, multi-turn conversation, human handoff, and test suite execution.)*

---

## 9. AI Coding Tools Disclosure

- **AI Tools Used**: Antigravity / Gemini 3.6 Flash (High).
- **What Used For**: Assistance with debugging RAG ranking algorithms, writing pytest test suites, and formatting structured evaluation outputs.
- **Example of an Incorrect AI Suggestion**:
  - *Incorrect Suggestion*: An early suggestion recommended ignoring conflict detection entirely for all shipping queries (`shipping_query = True -> conflict_detected = False`).
  - *Why it was wrong*: While this suppressed a false conflict on Canada shipping, it was overly broad and risked hiding legitimate document conflicts.
  - *Correction*: Refined conflict detection to evaluate genuine contradictions strictly among active official documents relevant to the exact same topic.

---

## 10. Known Limitations & Production Roadmap

1. **Lexical vs. Dense Embeddings**:
   - *Current Limitation*: TF-IDF with custom stemming relies on keyword similarity.
   - *Production Improvement*: Upgrade to dense neural embeddings (e.g. `bge-small-en-v1.5` or `text-embedding-3-small`) paired with FAISS vector store for semantic similarity.
2. **Order Identity Verification**:
   - *Current Limitation*: Possessing `ORD-XXXX` is assumed sufficient for mock lookup.
   - *Production Improvement*: Add 2-Factor Authentication (SMS/Email OTP) before disclosing order status.
3. **LLM Generation Layer**:
   - *Current Limitation*: Grounded answers use structured chunk extraction to guarantee zero hallucinations.
   - *Production Improvement*: Add a constrained LLM synthesis layer (e.g., Gemini 1.5 / GPT-4o-mini) with JSON schema validation for even smoother natural language responses.
