"""LEVEL: System / End-to-End — whole application from the user's perspective.

CLI subprocess journeys + multi-step flows (no browser/Selenium needed for a CLI).
"""
import subprocess
import sys

import pytest

from .conftest import ROOT, chat


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "app.cli", *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=60)


class TestCliJourneys:
    def test_kb_question_with_citations(self):
        p = run_cli("How long does a regular customer have to return an unused backpack?")
        assert p.returncode == 0
        assert "30 calendar days" in p.stdout
        assert "01-returns-policy-current.md" in p.stdout

    def test_order_lookup_journey(self):
        p = run_cli("Where is ORD-1007 and when should it arrive?")
        assert p.returncode == 0
        assert "August 22, 2026" in p.stdout and "UPS" in p.stdout

    def test_refusal_journey(self):
        p = run_cli("Can I put the entire Breeze Tumbler in the dishwasher?")
        assert p.returncode == 0
        assert "conflict" in p.stdout.lower()
        assert "Handoff: Yes" in p.stdout

    def test_trace_flag(self):
        p = run_cli("--trace", "Where is ORD-1007?")
        assert p.returncode == 0
        assert "tool_calls" in p.stderr and "retrieved" in p.stderr

    def test_missing_id_journey(self):
        p = run_cli("Where is my order?")
        assert p.returncode == 0
        assert "order ID" in p.stdout


class TestEndToEndFlows:
    def test_signup_like_flow_policy_then_order_then_followup(self, agent):
        s = agent.new_session()
        r1 = agent.chat(s, "My TrailPlus membership was active when I ordered. What is my return window?")
        assert "45 calendar days" in r1["answer"]
        r2 = agent.chat(s, "Where is ORD-1007?")
        assert "August 22, 2026" in r2["answer"]
        r3 = agent.chat(s, "When will it arrive?")
        assert "August 22, 2026" in r3["answer"]

    def test_policy_then_exception_narrowing(self, agent):
        s = agent.new_session()
        agent.chat(s, "How long do I have to return a backpack?")
        r = agent.chat(s, "What if it was final sale and arrived damaged?")
        assert "7 days" in r["answer"] or "human" in r["answer"].lower()

    def test_every_answer_shows_handoff_line(self, agent):
        for q in ["Where is ORD-1007?", "Do all products have a lifetime warranty?",
                  "Are all fabrics vegan in bags?"]:
            r, _ = chat(agent, agent.new_session(), q)
            assert "Human handoff recommended:" in r["answer"]
