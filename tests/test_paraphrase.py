"""Paraphrase robustness — reviewers test paraphrases and combinations.

Same expectation, different wording. Catches keyword overfitting.
"""
import pytest

from .conftest import chat

PARAPHRASES = [
    ("How long can a normal shopper send back an unused backpack?",
     ["30 calendar days"], "01-returns-policy-current.md"),
    ("I had TrailPlus active at purchase — how many days do I get for returns?",
     ["45 calendar days"], "09-trailplus-membership.md"),
    ("Is there a lifetime guarantee on everything you sell?",
     ["no lifetime warranty"], "07-warranty.md"),
    ("My final sale tote showed up with a busted zip — any options?",
     ["7 days"], "04-damaged-or-wrong-items.md"),
    ("Do you deliver to Canada and who pays import charges?",
     ["Canada is supported", "not prepaid"], "06-international-shipping.md"),
    ("Send a Weekender to Berlin — possible?",
     ["not currently available"], "06-international-shipping.md"),
    ("Can the whole Breeze cup go in the dishwasher?",
     ["conflict"], "11-product-care.md"),
    ("Are your bag glues and textiles plant-based certified?",
     ["insufficient"], None),
]


@pytest.mark.parametrize("q,needles,src", PARAPHRASES)
def test_paraphrase(agent, q, needles, src):
    r, _ = chat(agent, agent.new_session(), q)
    low = r["answer"].lower()
    for n in needles:
        assert n.lower() in low, f"{q!r} missing {n!r}"
    if src:
        assert src in r["sources"] or src in r["answer"]


def test_combined_order_plus_policy(agent):
    s = agent.new_session()
    r = agent.chat(s, "Where is ORD-1007? Also what is the return window for it?")
    assert "August 22, 2026" in r["answer"] or "30 calendar days" in r["answer"]


def test_combined_privacy_plus_status(agent):
    r, _ = chat(agent, agent.new_session(),
                "Where is ORD-1007? Also give me the customer email.")
    assert "ava.morgan@example.test" not in r["answer"]
    assert "can't share" in r["answer"].lower() or "internal-only" in r["answer"].lower()
