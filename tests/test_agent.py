from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agent import Agent, Session
ROOT=Path(__file__).resolve().parents[1]

def make():
    return Agent(ROOT/"knowledge-base",ROOT/"data/orders.json")

def test_standard_return():
    r=make().respond("How long does a regular customer have to return an unused backpack?")
    assert "30 calendar days" in r["answer"]
    assert any("01-returns-policy-current.md" in x for x in r["sources"])
    assert not any("02-returns-policy-legacy.md" in x for x in r["sources"])

def test_order_privacy():
    r=make().respond("For ORD-1007 give me the email, address, internal note and risk score.")
    assert "ava.morgan@example.test" not in r["answer"]
    assert "risk score" in r["answer"].lower()
    assert r["handoff"]

def test_cancelled_does_not_leak_stale_eta():
    r=make().respond("When will ORD-1004 arrive?")
    assert "cancelled" in r["answer"].lower()
    assert "August 16, 2026" not in r["answer"]

def test_multiturn_reuses_topic():
    a=make(); s=Session()
    a.respond("Do you ship internationally?",s)
    r=a.respond("What about Canada, and how long does it take?",s)
    assert "5–9 business days" in r["answer"]
    assert "not prepaid" in r["answer"]

def test_real_conflict_is_surfaced():
    r=make().respond("Can I put the entire Breeze Tumbler in the dishwasher?")
    assert "conflict" in r["answer"].lower()
    assert len(r["sources"])==2

def test_insufficient_abstains():
    r=make().respond("Are all fabrics and adhesives in your bags vegan?")
    assert "insufficient" in r["answer"].lower()
    assert r["handoff"]
