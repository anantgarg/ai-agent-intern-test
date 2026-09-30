"""API + Database/Data + Contract testing (no HTTP/DB servers here).

API = internal call surface (Agent.chat, OrderStore.lookup, Retriever.retrieve).
Database = orders.json + knowledge-base markdown as the data layer.
Contract = agreed schemas between layers.
"""
import json

import pytest

from app.documents import load_knowledge_base
from .conftest import ROOT, chat, load_orders_raw


# ---------- API ----------
class TestInternalApi:
    def test_chat_response_contract(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Where is ORD-1007?")
        assert set(("answer", "sources", "handoff", "handoff_reason",
                    "trace")) <= set(r)
        assert isinstance(r["answer"], str) and isinstance(r["sources"], list)
        assert isinstance(r["handoff"], bool)

    def test_lookup_contract(self, agent):
        res = agent.orders.lookup("ORD-1007")
        assert set(("found", "normalized_id", "record_safe")) <= set(res)

    def test_retrieve_contract(self, agent):
        top = agent.retriever.retrieve("warranty", top_k=3)
        assert len(top) == 3
        for s in top:
            assert hasattr(s.chunk, "filename") and isinstance(s.score, float)

    def test_invalid_api_input_handled(self, agent):
        r = agent.chat(agent.new_session(), "")
        assert r["answer"].strip()


# ---------- data / database ----------
class TestDataLayer:
    def test_orders_count_and_ids(self):
        raw = load_orders_raw()
        assert len(raw["orders"]) == 12
        assert {o["order_id"] for o in raw["orders"]} == {f"ORD-{n}" for n in range(1001, 1013)}

    def test_orders_required_fields(self):
        for o in load_orders_raw()["orders"]:
            for f in ("order_id", "status", "customer_safe_message",
                      "customer", "internal", "items"):
                assert f in o, f"{o['order_id']} missing {f}"
            assert o["customer"]["email"] and o["customer"]["shipping_address"]
            assert "risk_score" in o["internal"]

    def test_snapshot_at_present(self):
        assert load_orders_raw()["snapshot_at"] == "2026-08-15T12:00:00Z"

    def test_status_coverage(self):
        statuses = {o["status"] for o in load_orders_raw()["orders"]}
        assert {"pending", "processing", "shipped", "delivered",
                "cancelled", "returned", "delayed", "exception"} <= statuses

    def test_kb_frontmatter_contract(self):
        chunks = load_knowledge_base(str(ROOT / "knowledge-base"))
        for c in chunks:
            assert "status" in c.metadata and "policy_authority" in c.metadata


# ---------- contract ----------
class TestContracts:
    SAFE = {"order_id", "membership_tier", "items", "placed_at", "status",
            "status_updated_at", "shipped_at", "delivered_at", "carrier",
            "tracking_number", "estimated_delivery", "customer_safe_message"}

    def test_tool_returns_only_safe_fields(self, agent):
        res = agent.orders.lookup("ORD-1007")
        assert set(res["record_safe"]) == self.SAFE

    def test_every_tool_trace_result_honors_contract(self, agent):
        for oid in ("ORD-1001", "ORD-1004", "ORD-1007", "ORD-1011"):
            r, _ = chat(agent, agent.new_session(), f"Status of {oid}?")
            safe = r["trace"]["tool_calls"][0]["result"]["record_safe"]
            assert set(safe) == self.SAFE

    def test_source_format_contract(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Do all products have a lifetime warranty?")
        for s in r["sources"]:
            assert s.endswith(".md")
        assert "Sources:" in r["answer"]
