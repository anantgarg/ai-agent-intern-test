from app.agent import SupportAgent


def test_canada_multiturn():
    agent = SupportAgent()

    first = agent.answer(
        "Do you ship internationally?"
    )

    assert first["sources"]

    second = agent.answer(
        "What about Canada, and how long does it take?"
    )

    answer = second["answer"].lower()

    assert "canada" in answer
    assert "5–9 business days" in second["answer"]
    assert "duties" in answer
    assert "taxes" in answer

    filenames = [
        source["filename"]
        for source in second["sources"]
    ]

    assert "06-international-shipping.md" in filenames
    assert second["handoff"] is False