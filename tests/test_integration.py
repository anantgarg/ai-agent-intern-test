"""LEVEL: Integration testing — components working together.

KB -> retriever -> agent routing -> order tool -> response+trace.
"""
import pytest

from .conftest import chat


class TestRetrieverAgentIntegration:
    def test_policy_answer_cites_retrieved_doc(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session,
                    "How long does a regular customer have to return an unused backpack?")
        retrieved_files = {t["filename"] for t in r["trace"]["retrieved"]}
        assert "01-returns-policy-current.md" in retrieved_files
        assert "01-returns-policy-current.md" in r["sources"]

    def test_authoritative_source_preferred_over_superseded(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "What is the standard return window?")
        assert "01-returns-policy-current.md" in r["sources"]
        assert "02-returns-policy-legacy.md" not in r["sources"]

    def test_draft_never_cited_as_authority(self, agent, fresh_session):
        for q in ["What is the return window?",
                  "Tell me about the migration note policy"]:
            r, _ = chat(agent, agent.new_session(), q)
            assert "14-internal-content-migration-notes.md" not in r["sources"]

    def test_order_tool_feeds_response(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Where is ORD-1003?")
        calls = r["trace"]["tool_calls"]
        assert len(calls) == 1 and calls[0]["tool"] == "order_lookup"
        assert calls[0]["args"]["order_id"] == "ORD-1003"
        assert "USPS" in r["answer"] or "shipped" in r["answer"].lower()

    def test_trace_retrieved_plus_tool_present_together(self, agent):
        s = agent.new_session()
        r = agent.chat(s, "I placed ORD-1001, can I cancel it?")
        assert len(r["trace"]["retrieved"]) > 0
        assert len(r["trace"]["tool_calls"]) == 1  # cancellation with ID uses tool


class TestSessionIntegration:
    def test_history_grows_two_entries_per_turn(self, agent):
        s = agent.new_session()
        agent.chat(s, "Do you ship internationally?")
        assert len(s.history) == 2
        agent.chat(s, "What about Canada?")
        assert len(s.history) == 4

    def test_last_order_id_updates(self, agent):
        s = agent.new_session()
        agent.chat(s, "Where is ORD-1007?")
        assert s.last_order_id == "ORD-1007"
        agent.chat(s, "Where is ORD-1003?")
        assert s.last_order_id == "ORD-1003"

    def test_last_topic_updates(self, agent):
        s = agent.new_session()
        agent.chat(s, "Do you ship internationally?")
        assert s.last_topic == "international_shipping"

    def test_sessions_isolated(self, agent):
        s1, s2 = agent.new_session(), agent.new_session()
        agent.chat(s1, "Where is ORD-1007?")
        assert s2.last_order_id is None
        assert s2.history == []
