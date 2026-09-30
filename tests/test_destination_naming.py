"""Destination naming — unsupported-country answers name the actual country.

Generalizes the old Germany-hardcoded branch: any detected non-Canada
destination is named; domestic/Canada questions are never mislabeled.
"""
import pytest

from .conftest import chat


@pytest.mark.parametrize("q,country", [
    ("Can you ship an Atlas Weekender to Germany?", "Germany"),
    ("Send a Weekender to Berlin — possible?", "Germany"),
    ("Ship a Weekender to France please", "France"),
    ("Do you deliver to Paris?", "France"),
    ("Can you send a bag to Tokyo?", "Japan"),
    ("Ship to Sydney?", "Australia"),
])
def test_names_actual_country(agent, q, country):
    r, _ = chat(agent, agent.new_session(), q)
    assert f"Shipping to {country} is not currently available." in r["answer"]
    assert "06-international-shipping.md" in r["sources"]
    assert r["handoff"] is False


def test_germany_exact_visible_phrase(agent, fresh_session):
    r, _ = chat(agent, fresh_session, "Can you ship an Atlas Weekender to Germany?")
    assert "shipping to germany is not currently available" in r["answer"].lower()


def test_canada_weekender_not_unsupported(agent):
    r, _ = chat(agent, agent.new_session(), "Can you ship a Weekender to Canada?")
    assert "not currently available" not in r["answer"].lower()
    assert "Canada is supported" in r["answer"]


def test_texas_weekender_not_unsupported(agent):
    r, _ = chat(agent, agent.new_session(), "Ship my Weekender to Texas")
    assert "not currently available" not in r["answer"].lower()


def test_earliest_mention_wins(agent):
    assert agent._detect_destination("germany or france?") == "Germany"
    assert agent._detect_destination("france or germany?") == "France"


def test_no_destination_detected(agent):
    assert agent._detect_destination("how long does shipping take") is None


def test_retrieval_recalls_intl_doc(agent):
    top = agent.retriever.retrieve("Ship a Weekender to France please", top_k=4)
    assert "06-international-shipping.md" in {s.chunk.filename for s in top}
