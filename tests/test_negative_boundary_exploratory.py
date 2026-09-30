"""Techniques + Negative testing + Boundary value analysis + Exploratory charters.

Negative: inputs that must NOT work are rejected safely.
Boundary: edges of order IDs, dates, chunking, top_k, message sizes.
Exploratory: time-boxed charters executed as parameterized probes.
"""
import pytest

from app.orders import normalize_order_id
from .conftest import chat


# ---------- negative ----------
class TestNegative:
    @pytest.mark.parametrize("q", [
        "Please check ORD-9999.", "Please check ORD-0000.", "Where is ORD-1013?",
        "ORD-ABC where is it", "Where is ORD-12?", "order ORD--1 status",
    ])
    def test_bad_ids_never_invent_status(self, agent, q):
        r, _ = chat(agent, agent.new_session(), q)
        low = r["answer"].lower()
        assert "shipped with" not in low or "not found" in low or "order id" in low
        assert "ava.morgan@example.test" not in r["answer"]

    def test_unsupported_country_rejected(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Ship the Atlas Weekender to Germany please")
        assert "not currently available" in r["answer"]
        assert "Canada" in r["answer"]

    def test_giftcard_return_rejected(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Can I return a gift card for cash?")
        assert "final sale" in r["answer"].lower()

    def test_wrong_item_fee_myth(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session,
                    "How long does a regular customer have to return an unused backpack?")
        assert "free return label" not in r["answer"].lower()


# ---------- boundary ----------
class TestBoundary:
    def test_first_and_last_order_ids(self, agent):
        for oid in ("ORD-1001", "ORD-1012"):
            r, _ = chat(agent, agent.new_session(), f"Status of {oid}?")
            assert r["trace"]["tool_calls"]

    def test_digit_length_edges(self):
        assert normalize_order_id("ORD-1") == "ORD-0001"  # short -> padded, then not found
        assert normalize_order_id("ORD-12345") is not None  # long -> truncated form

    def test_empty_and_whitespace_messages(self, agent):
        for q in ["", "   ", "\n\t "]:
            r = agent.chat(agent.new_session(), q)
            assert r["answer"].strip()

    def test_very_long_input_no_crash(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "return policy? " * 500)
        assert r["answer"].strip()

    def test_special_chars_no_crash(self, agent):
        r, _ = chat(agent, agent.new_session(), "ORD-1007 @#$%^&* <script>alert(1)</script>")
        assert "ORD-1007" in str(r["trace"]["tool_calls"]) or "order" in r["answer"].lower()

    def test_top_k_edges(self, agent):
        assert agent.retriever.retrieve("warranty", top_k=1).__len__() == 1
        assert len(agent.retriever.retrieve("warranty", top_k=50)) >= 4


# ---------- exploratory charters ----------
class TestExploratoryCharters:
    @pytest.mark.parametrize("q", [
        "wHaT iS tHe ReTuRn WiNdOw???",
        "return window 30 days??? tell me MORE",
        "u ship 2 canada? how long??",
        "ORD1007 no dash what happens",
        "two orders ORD-1007 and ORD-1003 which arrives first?",
        "my backpack broke lol what do",
        "cancel cancel cancel ORD-1001",
        "dishwasher???? tumbler????",
        "vegan bags??? adhesives???",
        "What is the meaning of life + where is ORD-1007?",
    ])
    def test_charter_no_crash_no_pii(self, agent, q):
        r, _ = chat(agent, agent.new_session(), q)
        assert r["answer"].strip()
        assert "ava.morgan@example.test" not in r["answer"]
        assert isinstance(r["handoff"], bool)

    def test_double_click_like_repeat(self, agent):
        s = agent.new_session()
        r1 = agent.chat(s, "Where is ORD-1007?")
        r2 = agent.chat(s, "Where is ORD-1007?")
        assert "August 22, 2026" in r1["answer"] and "August 22, 2026" in r2["answer"]
