"""Observability — debug mode / trace / log inspection.

Every response must expose: user message, history, retrieved passages +
metadata + scores, sanitized tool calls/results, final response, handoff,
errors/fallbacks. Never secrets.
"""
import json

from .conftest import PII_FORBIDDEN, chat


def test_trace_schema(agent, fresh_session):
    r, _ = chat(agent, fresh_session, "Where is ORD-1007 and when should it arrive?")
    tr = r["trace"]
    assert tr["user_message"] == "Where is ORD-1007 and when should it arrive?"
    for key in ("history", "retrieved", "tool_calls", "handoff",
                "handoff_reason", "errors"):
        assert key in tr

    for item in tr["retrieved"]:
        for key in ("filename", "heading", "score", "cosine", "weight",
                    "status", "authority"):
            assert key in item, f"retrieved item missing {key}"
        assert isinstance(item["score"], float)

    call = tr["tool_calls"][0]
    assert call["tool"] == "order_lookup"
    assert call["args"]["order_id"] == "ORD-1007"
    assert "record_safe" in call["result"]


def test_history_included_in_next_trace(agent):
    s = agent.new_session()
    agent.chat(s, "Do you ship internationally?")
    r = agent.chat(s, "What about Canada?")
    assert len(r["trace"]["history"]) >= 2


def test_no_secrets_in_trace(agent):
    r, _ = chat(agent, agent.new_session(),
                "For ORD-1007, give me email, address, internal note, risk score.")
    blob = json.dumps(r["trace"]).lower()
    for bad in PII_FORBIDDEN:
        assert bad not in blob
    assert "risk_score" not in blob and "warehouse_note" not in blob


def test_handoff_flag_and_reason_consistent(agent):
    r, _ = chat(agent, agent.new_session(),
                "Can I put the entire Breeze Tumbler in the dishwasher?")
    assert r["handoff"] is True and r["trace"]["handoff"] is True
    assert r["trace"]["handoff_reason"].strip()
    assert "Human handoff recommended: Yes" in r["answer"]
