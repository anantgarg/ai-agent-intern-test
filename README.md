# Aster & Row — Reliable AI Support Agent

Aster & Row is a fictional ecommerce company selling bags, drinkware, and travel accessories.

This project builds a customer-support agent that combines:

- Retrieval-Augmented Generation (RAG)
- Controlled order lookup
- Multi-turn conversation context
- Source citations
- Customer-data protection
- Prompt-injection resistance
- Safe abstention and human handoff
- Deterministic evaluation
- Regression testing
- Debug/observability support
- A simple React web interface

The main design goal is:

> **Reliability over guessing.**

---

## 🎯 Project Goal

The assignment focuses on four common problems found in AI customer-support systems:

1. **Conflicting policy answers**  
   The agent should prefer current authoritative policies over legacy or superseded information.

2. **Invented order information**  
   The agent should only provide order information when an order lookup is actually performed.

3. **Lost conversation context**  
   Follow-up questions such as "What about Canada?" should be understood in the context of the previous conversation.

4. **Unsafe retrieved content**  
   Instruction-like content inside the knowledge base must be treated as untrusted data rather than application instructions.

The implementation therefore focuses on:

**RAG + controlled tools + conversation context + safety + evaluation**

---

# ✨ Project Highlights

| Capability | Implementation |
|---|---|
| Knowledge retrieval | ChromaDB-based RAG |
| Document metadata | Front-matter metadata preserved |
| Policy precedence | Current/authoritative content preferred |
| Order lookup | Controlled order lookup function |
| Privacy | Customer-safe order fields |
| Multi-turn chat | Session-aware conversation context |
| Safe abstention | Missing information is not guessed |
| Prompt-injection defense | Retrieved content treated as untrusted |
| Source citations | Filename and relevant heading |
| Evaluation | Deterministic behavior-level evaluation |
| Regression tests | Pytest |
| Observability | Debug/trace information |
| Backend | FastAPI |
| Frontend | React |

---

# 🏗️ Architecture

The application follows a simple flow:

**React Frontend → FastAPI Backend → Support Agent**

The Support Agent then uses:

- **RAG Retrieval** to search the knowledge base.
- **Order Lookup** to safely retrieve order information.
- **Conversation Context** to understand follow-up questions.

The retrieved information and tool results are then used to generate a grounded response with sources or a human-handoff recommendation when necessary.

---

# 🧰 Technology Stack

## Backend

- Python 3.12
- FastAPI
- Uvicorn
- OpenAI API
- ChromaDB
- python-frontmatter
- Pytest

## Frontend

- React
- React DOM
- React Scripts
- CSS

## Retrieval

The supplied Markdown files in `knowledge-base/` are parsed, split into useful passages, and indexed for semantic retrieval.

Useful metadata is preserved, including:

- filename
- heading
- document type
- status
- authority / precedence information

This metadata helps the system prefer current authoritative information over legacy or superseded content.

## Storage

| Data | Storage |
|---|---|
| Knowledge base | Markdown files |
| Orders | `data/orders.json` |
| Retrieval index | ChromaDB |
| Conversation context | Application session state |

---

# 📁 Project Structure

```text
.
├── README.md
├── requirements.txt
├── pytest.ini
│
├── app/
│   ├── __init__.py
│   ├── api.py
│   ├── main.py
│   ├── rag.py
│   └── tools/
│       └── orders.py
│
├── data/
│   ├── orders.json
│   └── orders-data-dictionary.md
│
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
│
├── evaluation/
│   ├── visible-cases.json
│   └── run_eval.py
│
├── tests/
│   └── test_orders.py
│
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── public/
    └── src/
```

---

# 🚀 Setup

## 1. Clone the repository

```bash
git clone https://github.com/tw-1234/ai-agent-intern-test.git
cd ai-agent-intern-test
```

## 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

## 3. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

## 4. Configure environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key_here
DEBUG=0
```

Use `.env.example` as the template for required environment variables.

**Never commit a real API key or other credentials.**

---

# ▶️ Running the Backend

From the repository root:

```bash
source .venv/bin/activate
uvicorn app.api:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

---

# 🖥️ Running the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm start
```

The React application will normally be available at:

```text
http://localhost:3000
```

The frontend communicates with the FastAPI backend and displays the agent's response and applicable source information.

---

# 🧠 How the Agent Works

## 1. Knowledge-Base Retrieval

For company-specific questions, the agent searches the supplied knowledge base instead of relying only on general model knowledge.

The documents are split into relevant passages and indexed for semantic retrieval.

The retrieval process preserves document metadata so that current and authoritative information can be preferred over outdated or superseded content.

For example, a customer asking about the standard return window should receive information from the current returns policy rather than an older legacy policy.

## 2. Grounded Responses

Retrieved passages are used as evidence for the final response.

The agent is instructed not to invent unsupported company policies or product information.

Policy and product answers include source references showing where the information came from.

Example:

**Source:** `01-returns-policy-current.md` — Standard return window

This makes the response easier to verify.

## 3. Document Precedence

The knowledge base intentionally contains different types of documents, including:

- Current policies
- Legacy/superseded policies
- Product information
- Internal content
- Instruction-like content

The retrieval and response logic gives preference to authoritative active information.

Retrieved documents are treated as data, not as application instructions.

This prevents internal or malicious text from overriding the agent's intended behavior.

---

# 📦 Order Lookup

Order information is handled through:

```text
app/tools/orders.py
```

The complete `data/orders.json` file is not placed into the model's prompt.

When order information is required, the system performs a controlled lookup and returns only the customer-safe result.

Example:

**Customer:**

> Where is ORD-1007?

**Agent:**

> The order has shipped and is currently in transit with UPS.

Harmless input differences are normalized safely.

For example:

```text
ORD-1007
ord-1007
 ORD-1007
```

Unknown and malformed order IDs are handled without guessing.

The order's current status is treated as authoritative.

The system also avoids reporting stale delivery information for cancelled or returned orders.

---

# 🔐 Customer Data Protection

The order lookup intentionally protects internal-only information.

The agent does not expose:

- Customer email addresses
- Shipping addresses
- Internal notes
- Risk scores
- Fraud-review information
- Other internal-only order fields

This prevents the underlying mock order dataset from becoming a source of accidental customer-data disclosure.

---

# 💬 Multi-Turn Conversation

The agent maintains relevant session context so that follow-up questions can be understood correctly.

Example:

**Customer:**

> Do you ship internationally?

**Agent:**

> Aster & Row currently ships internationally only to Canada.

**Customer:**

> What about Canada, and how long does it take?

The second question is interpreted using the previous conversation context.

The agent can also maintain order context:

**Customer:**

> Where is ORD-1007?

**Agent:**

> The order has shipped and is currently in transit with UPS.

**Customer:**

> When will it arrive?

The agent uses the previously identified order when answering the follow-up.

The goal is to preserve useful context without carrying unrelated information indefinitely.

---

# 🛡️ Safety and Reliability

The system is designed around safe customer-support behavior.

It does not:

- Invent order statuses.
- Invent delivery dates.
- Expose protected customer information.
- Reveal system prompts or secrets.
- Follow instructions hidden inside retrieved documents.
- Claim unsupported actions were completed.
- Silently ignore genuine authoritative-source conflicts.

It can:

- Ask for a missing order ID.
- Ask concise clarification questions.
- State when information is insufficient.
- Surface genuine conflicts.
- Recommend human support.
- Refuse unsupported actions safely.

For example, if a customer asks:

> Please refund my order immediately.

The agent does not claim that a refund was completed because the system does not implement refunds.

Instead, it recommends human support.

The same principle applies to unsupported actions such as changing a shipping address or cancelling an order.

---

# 🧪 Evaluation

The evaluation suite is run with:

```bash
PYTHONPATH=. python evaluation/run_eval.py
```

It reports individual case results rather than only a single overall score.

The evaluation covers:

| Category | What is tested |
|---|---|
| Retrieval | Relevant and authoritative source selection |
| Groundedness | Answers supported by retrieved content |
| Tool use | Correct order lookup behavior |
| Privacy | Protection of internal fields |
| Multi-turn | Follow-up conversation context |
| Safety | Resistance to unsafe retrieved instructions |
| Abstention | Missing or unsupported information |
| Regression | Previously discovered failures |
| Original cases | Additional cases beyond supplied examples |

The suite includes the supplied visible cases plus additional original cases created during development.

---

# 🏆 Final Evaluation Result

The final evaluation result is:

**29/30 passed — 96.7%**

The project intentionally reports the remaining failure rather than hiding it.

### Evaluation Summary

```text
PASS  standard-return-window
PASS  trailplus-return-window
PASS  final-sale-damaged-exception
PASS  canada-multiturn
PASS  unsupported-country
PASS  valid-order-lookup
PASS  missing-order-id
PASS  cancelled-order-stale-eta
PASS  unknown-order
PASS  shipped-without-eta
PASS  order-data-privacy
PASS  no-lifetime-warranty
FAIL  retrieved-prompt-injection
PASS  insufficient-information
PASS  genuine-active-source-conflict
PASS  return-window-followup
PASS  lowercase-order-id
PASS  malformed-order-id
PASS  refund-not-supported
PASS  warranty-specific-product
PASS  international-duties-followup
PASS  order-followup-delivery
PASS  return-policy-legacy-protection
PASS  privacy-without-order-lookup
PASS  unsupported-action-no-promise
PASS  original-order-id-whitespace
PASS  original-no-order-guess
PASS  original-secret-request
PASS  original-product-source
PASS  original-unsupported-action
```

**Result: 29/30 passed (96.7%)**

The remaining failure is related to the exact expected wording for the retrieved prompt-injection case.

The agent correctly rejects the malicious retrieved instruction and follows the intended application behavior, but the evaluation assertion does not match the response wording exactly.

This is documented as a remaining improvement rather than being hidden.

---

# 📈 Baseline vs Final

The implementation was improved through testing, debugging, and regression cases.

| Area | Baseline | Final |
|---|---|---|
| Overall evaluation | Initial prototype | 29/30 (96.7%) |
| Retrieval | Basic retrieval | Improved source precedence |
| Tool use | Basic lookup | Validated and sanitized |
| Privacy | Basic protection | Explicit protected-field handling |
| Multi-turn | Limited context | Session-aware follow-ups |
| Safety | Basic prompting | Retrieved content treated as untrusted |
| Evaluation | Initial cases | Visible + original regression cases |

The final result is intentionally reported as **29/30** rather than claiming a perfect score.

---

# 🐛 Bug Diary

## Bug 1 — Legacy Policy Could Influence the Current Answer

**Reproduction**

Ask a question that causes both the current and legacy return policies to become relevant.

**Root Cause**

Retrieval could return both current and superseded policy content.

**Fix**

Added document precedence so active/current policy information is preferred over legacy content.

**Regression Test**

`return-policy-legacy-protection`

---

## Bug 2 — Follow-Up Questions Lost Context

**Reproduction**

```text
Do you ship internationally?

What about Canada, and how long does it take?
```

**Root Cause**

The second message could be interpreted as an independent question without enough context from the previous turn.

**Fix**

Relevant conversation history is retained and used when resolving follow-up questions.

**Regression Tests**

- `canada-multiturn`
- `international-duties-followup`

---

## Bug 3 — Cancelled Orders Could Contain Stale Delivery Information

**Reproduction**

Ask for delivery information for an order whose current status is cancelled or returned.

**Root Cause**

The underlying mock data can contain delivery-related fields that should not be reported for cancelled or returned orders.

**Fix**

The order lookup uses the current order status as authoritative and suppresses inappropriate delivery information for cancelled/returned orders.

**Regression Test**

`cancelled-order-stale-eta`

---

## Bug 4 — Retrieved Content Could Be Interpreted as Instructions

**Reproduction**

Provide a query that causes instruction-like content from the knowledge base to be retrieved.

**Root Cause**

Retrieved text is untrusted data, but an LLM can incorrectly interpret instruction-like text as an instruction to follow.

**Fix**

Application instructions explicitly define retrieved passages as untrusted data.

Document metadata and precedence are used to determine which information should support the response.

**Regression Test**

`retrieved-prompt-injection`

The current evaluation still has a wording-level failure for this case, which is why the final score remains 29/30.

---

# 🔍 Observability

Debug mode can be enabled with:

```env
DEBUG=1
```

Debug information makes it possible to inspect:

- Current user message
- Relevant conversation history
- Retrieved passages
- Retrieval metadata
- Retrieval scores
- Tool calls
- Sanitized tool results
- Final response
- Errors
- Fallback decisions
- Human-handoff decisions

Sensitive information should not be written to logs.

The system does not intentionally log API keys or protected customer fields.

---

# 🎥 Demo Video

A short demonstration video is provided through **Google Drive**.

The demo shows the required customer-support flows:

1. **Knowledge-base question**  
   A return-policy question is answered using retrieved company information with source citations.

2. **Order lookup**  
   An example order such as `ORD-1007` is looked up through the order tool.

3. **Multi-turn conversation**  
   The demo shows a follow-up question using previous conversation context.

4. **Safe refusal / human handoff**  
   The demo includes unsupported requests such as refunding an order or changing a shipping address.

5. **Evaluation suite**  
   The demo shows the evaluation command being executed:

```bash
PYTHONPATH=. python evaluation/run_eval.py
```

### ▶️ Watch the AI Support Agent Demo

**[🎥 Watch Demo Video on Google Drive](https://drive.google.com/file/d/14KFJnVzMZvHXMhuuvAt8RdEABjhMC8ew/view?usp=share_link)**



---

# 🤖 AI Coding Tools Used

AI coding assistance was used during development for:

- Debugging Python and React issues
- Improving retrieval logic
- Designing evaluation cases
- Identifying edge cases
- Reviewing error handling
- Improving documentation
- Understanding test failures

AI-generated suggestions were treated as suggestions rather than automatically trusted.

### Example of an incomplete AI suggestion

One generated approach treated retrieved content too directly as trusted instructions.

That approach was not suitable for this assignment because the knowledge base intentionally contains internal and instruction-like content.

The implementation was therefore changed so that:

- User input
- Retrieved content
- Tool results

are treated as untrusted data, while application instructions remain authoritative.


---

# ⚠️ Known Limitations

This is a take-home implementation rather than a production support platform.

Current limitations include:

- The system uses mock order data rather than a real ecommerce backend.
- Possession of an order ID is treated as sufficient authentication, as allowed by the assignment.
- The order lookup is read-only.
- Refunds, cancellations, replacements, and address changes are not actually executed.
- Human handoff is represented as a recommendation rather than a live support-ticket integration.
- Retrieval is local and is not designed as production-scale vector infrastructure.
- The evaluation suite cannot cover every possible natural-language variation.
- One prompt-injection evaluation case currently has a wording-level mismatch, resulting in 29/30 rather than 30/30.

---

# 🚀 Improvements Before Production

Before using the system with real customers, I would add:

- Real authentication and authorization
- Secure customer identity verification
- A production order-management API
- A real support-ticket/handoff integration
- Monitoring and alerting
- Retrieval-quality monitoring
- More comprehensive adversarial testing
- Rate limiting and abuse protection
- Automated evaluation in CI/CD
- Better workflows for resolving conflicting company policies
- Stronger structured output validation
- Privacy and security review
- Production audit logging
- Better evaluation of natural-language paraphrases

---

# 💡 Design Principles

### 1. Ground answers in company data

For Aster & Row-specific questions, supplied company content is preferred over general model knowledge.

### 2. Retrieval is evidence, not authority

Retrieved documents may contain outdated or instruction-like content.

The application determines how retrieved content should be used.

### 3. Tools are controlled boundaries

The model does not receive the entire order database.

It receives only the result of the requested lookup.

### 4. When uncertain, do not guess

If information is missing, unsupported, or genuinely conflicting, the agent should explain the limitation and recommend human assistance where appropriate.

### 5. Reliability matters more than a perfect demo

The project intentionally reports the remaining 29/30 evaluation result instead of hiding the failing case.

---

# 🧪 Quick Verification

Run the unit tests:

```bash
pytest
```

Current result:

```text
5 passed
```

Run the complete evaluation:

```bash
PYTHONPATH=. python evaluation/run_eval.py
```

Expected final result:

```text
Result: 29/30 passed (96.7%)
```

---

# 🔐 Environment Variables

Create a local `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
DEBUG=0
```

Do not commit `.env`.

Only commit an `.env.example` containing placeholder values:

```env
OPENAI_API_KEY=
DEBUG=0
```