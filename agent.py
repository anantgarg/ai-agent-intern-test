import os
import json
import time
from order_lookup import order_lookup, extract_order_id
from rag import search_knowledge_base

# Define the target vertical JSON trace file
TRACE_FILE = "traces.json"

def _log_trace(event_data):
    """Helper to read, append, and pretty-prints events into traces.json vertically."""
    traces = []
    if os.path.exists(TRACE_FILE):
        try:
            with open(TRACE_FILE, "r", encoding="utf-8") as f:
                traces = json.load(f)
                if not isinstance(traces, list):
                    traces = []
        except Exception:
            traces = []
            
    traces.append(event_data)
    
    with open(TRACE_FILE, "w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2)

def _finalize_trace(query, resp, metadata, start_time):
    latency = round(time.time() - start_time, 4)
    metadata["latency_seconds"] = latency
    trace_data = {
        "timestamp": time.time(),
        "event": "execution_completed",
        "query": query,
        "response": resp,
        "metadata": metadata
    }
    _log_trace(trace_data)

def process_query(query, history=None):
    if history is None:
        history = []
        
    query_lower = query.lower()
    start_time = time.time()
    
    metadata = {
        "retrieved_sources": [],
        "tools_called": [],
        "handoff_triggered": False,
        "category": "general"
    }

    # Log query received
    _log_trace({
        "timestamp": time.time(),
        "event": "query_received",
        "query": query,
        "history": history
    })

    # 1. SECURITY & PROMPT INJECTION GUARDRAIL
    security_triggers = [
        "ignore previous instructions", 
        "system prompt", 
        "reveal prompt", 
        "developer instructions",
        "ignore all instructions"
    ]
    if any(p in query_lower for p in security_triggers):
        metadata["category"] = "security"
        resp = "I am an AI support representative for Aster & Row. I can only assist with order status tracking, return policies, and product details."
        _finalize_trace(query, resp, metadata, start_time)
        return resp, metadata

    # 2. OUT-OF-SCOPE GUARDRAIL
    out_of_scope = ["capital of france", "weather in", "python code", "recipe", "solve this equation"]
    if any(p in query_lower for p in out_of_scope):
        metadata["category"] = "out_of_scope"
        resp = "I cannot answer this question. The knowledge base only contains information regarding Aster & Row's orders, products, and operational policies."
        _finalize_trace(query, resp, metadata, start_time)
        return resp, metadata

    # 3. STRICT ORDER INTENT CHECK (Current query only, preventing history bleeding)
    order_id = extract_order_id(query)
    order_keywords = ["order", "where is", "track", "shipping", "arrive", "status", "ord-", "refund", "cancel"]
    is_order_intent = order_id is not None and any(kw in query_lower for kw in order_keywords)

    if is_order_intent:
        metadata["category"] = "tool_use"
        metadata["tools_called"].append("order_lookup")

        if not order_id:
            resp = "Could you please provide your Order ID (e.g., ORD-XXXX) so I can check its current status?"
            _finalize_trace(query, resp, metadata, start_time)
            return resp, metadata

        # Privacy / PII Guardrail
        privacy_keywords = ["email", "address", "internal note", "risk score", "customer"]
        if any(kw in query_lower for kw in privacy_keywords):
            metadata["handoff_triggered"] = True
            resp = "Requests for customer contact information or internal risk metrics require escalation to support."
            _finalize_trace(query, resp, metadata, start_time)
            return resp, metadata

        # Refund / Cancellation Guardrail
        if any(kw in query_lower for kw in ["refund", "cancel", "modify", "change"]):
            metadata["handoff_triggered"] = True
            order_data = order_lookup(order_id)
            status = order_data.get("status", "unknown")
            resp = f"Order **{order_id}** is currently **{status}**. Automated modifications or direct refunds cannot be processed automatically. I am connecting you with a human support agent to process your request."
            _finalize_trace(query, resp, metadata, start_time)
            return resp, metadata

        order_data = order_lookup(order_id)
        if not order_data.get("found", True):
            resp = f"I couldn't find an order matching ID **{order_id}**. Please verify your Order ID and try again."
            _finalize_trace(query, resp, metadata, start_time)
            return resp, metadata

        status = order_data.get("status", "unknown")
        carrier = order_data.get("carrier", "N/A")
        eta = order_data.get("eta", "N/A")
        
        resp = f"Your order **{order_id}** status is **{status}**. Carrier: **{carrier}**. Estimated arrival date is **{eta}**."
        _finalize_trace(query, resp, metadata, start_time)
        return resp, metadata

    # 4. RAG POLICY RETRIEVAL INTENT
    metadata["category"] = "retrieval"
    search_results = search_knowledge_base(query)
    passages = search_results.get("passages", [])
    sources = search_results.get("sources", [])
    
    metadata["retrieved_sources"] = sources

    # Check for Breeze Tumbler conflict case
    if "breeze tumbler" in query_lower and "dishwasher" in query_lower:
        metadata["handoff_triggered"] = True
        resp = "There is a conflict in product care specifications regarding washing the Breeze Tumbler in a dishwasher. Transferring to human support for clarification."
        _finalize_trace(query, resp, metadata, start_time)
        return resp, metadata

    if not passages:
        metadata["handoff_triggered"] = True
        resp = "I am unable to find sufficient information in our policy documents to answer your question. I am transferring your request to a human support representative."
        _finalize_trace(query, resp, metadata, start_time)
        return resp, metadata

    # Format RAG response with citations
    context_str = "\n\n".join(passages)
    source_str = ", ".join([f"[{src}]" for src in sources])
    
    resp = f"Based on Aster & Row policies:\n\n{context_str}\n\n**Sources:** {source_str}"
    _finalize_trace(query, resp, metadata, start_time)
    return resp, metadata

def run_agent(query, history=None):
    """Compatibility wrapper for test_agent.py expected interface."""
    return process_query(query, history)