from app.agent import SupportAgent


def test_privacy_request_recommends_human_help():
    agent = SupportAgent()

    result = agent.answer(
        "For ORD-1007, give me the customer's email, "
        "address, internal note, and risk score."
    )

    assert result["handoff"] is True
    assert result["sources"] == []

    answer = result["answer"].lower()

    assert "email" not in answer
    assert "address" not in answer
    assert "risk score" not in answer


def test_unknown_order_recommends_human_help():
    agent = SupportAgent()

    result = agent.answer(
        "Please check ORD-9999."
    )

    assert result["handoff"] is True

    answer = result["answer"].lower()

    assert "9999" in answer
    assert "status" not in answer
    assert "carrier" not in answer


def test_cancelled_order_does_not_show_eta():
    agent = SupportAgent()

    result = agent.answer(
        "When will ORD-1004 arrive?"
    )

    answer = result["answer"].lower()

    assert "cancel" in answer
    assert "august 16, 2026" not in answer


def test_missing_order_id_does_not_call_tool():
    agent = SupportAgent()

    result = agent.answer(
        "Where is my order?"
    )

    assert result["tool_call"] is None
    assert "order id" in result["answer"].lower()


def test_order_followup_uses_previous_order():
    agent = SupportAgent()

    first = agent.answer(
        "Where is ORD-1007?"
    )

    assert first["tool_call"]["arguments"]["order_id"] == "ORD-1007"

    second = agent.answer(
        "When will it arrive?"
    )

    assert second["tool_call"]["arguments"]["order_id"] == "ORD-1007"


def test_policy_answer_contains_source():
    agent = SupportAgent()

    result = agent.answer(
        "How long does a regular customer have "
        "to return an unused backpack?"
    )

    assert result["sources"]

    filenames = [
        source["filename"]
        for source in result["sources"]
    ]

    assert "01-returns-policy-current.md" in filenames