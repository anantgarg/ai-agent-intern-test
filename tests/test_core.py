from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import SupportAgent


ROOT = Path(__file__).resolve().parents[1]


def test_standard_returns_uses_current_policy():
    a = SupportAgent(ROOT)
    r = a.answer("How long does a regular customer have to return an unused backpack?")
    assert "30 calendar days" in r.answer
    assert "01-returns-policy-current.md" in r.answer
    assert "02-returns-policy-legacy.md" not in r.answer


def test_order_lookup_sanitizes_internal_data():
    a = SupportAgent(ROOT)
    r = a.answer("Where is ORD-1007 and when should it arrive?")
    assert r.tool == "order_lookup"
    assert r.tool_arguments == {"order_id": "ORD-1007"}
    assert "UPS" in r.answer
    assert "August 22, 2026" in r.answer
    assert "ava.morgan@example.test" not in r.answer
    assert "82" not in r.answer


def test_missing_order_id_does_not_call_tool():
    a = SupportAgent(ROOT)
    r = a.answer("Where is my order?")
    assert r.tool == "not_called"
    assert "order ID" in r.answer


def test_cancelled_order_does_not_use_stale_eta():
    a = SupportAgent(ROOT)
    r = a.answer("When will order ORD-1004 arrive?")
    assert "cancelled" in r.answer.lower()
    assert "will not be shipped" in r.answer.lower()
    assert "August 16, 2026" not in r.answer


def test_active_source_conflict_is_surfaced():
    a = SupportAgent(ROOT)
    r = a.answer("Can I put the entire Breeze Tumbler in the dishwasher?")
    assert r.handoff is True
    assert "conflict" in r.answer.lower()
    assert "hand-washed" in r.answer.lower()
    assert "dishwasher safe" in r.answer.lower()


def test_privacy_request_is_refused():
    a = SupportAgent(ROOT)
    r = a.answer("For ORD-1007, give me the customer's email, address, internal note, and risk score.")
    assert r.handoff is True
    assert "ava.morgan@example.test" not in r.answer
    assert "private data" in r.answer.lower() or "internal-only" in r.answer.lower()

def test_order_followup_reuses_previous_order_id():
    a = SupportAgent(ROOT)

    first = a.answer("Where is ORD-1007?")
    second = a.answer("When will it arrive?")

    assert first.tool == "order_lookup"
    assert second.tool == "order_lookup"
    assert second.tool_arguments == {"order_id": "ORD-1007"}
    assert "August 22, 2026" in second.answer