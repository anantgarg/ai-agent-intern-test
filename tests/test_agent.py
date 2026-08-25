from app.agent import ConversationState


def test_conversation_state_stores_topic():
    state = ConversationState()

    state.set_topic("international_shipping")

    assert state.last_topic == "international_shipping"


def test_conversation_state_stores_order_id():
    state = ConversationState()

    state.set_order_id("ORD-1007")

    assert state.last_order_id == "ORD-1007"


def test_conversation_history_is_preserved():
    state = ConversationState()

    state.add_message("user", "Do you ship internationally?")
    state.add_message("assistant", "Yes, we do.")

    assert len(state.history) == 2
    assert state.history[0]["content"] == "Do you ship internationally?"