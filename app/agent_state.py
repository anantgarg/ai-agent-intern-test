from dataclasses import dataclass, field


@dataclass
class ConversationState:
    """
    Stores relevant conversation context for one session.
    """

    history: list[dict] = field(default_factory=list)
    last_topic: str | None = None
    last_order_id: str | None = None

    def add_message(self, role: str, content: str) -> None:
        self.history.append(
            {
                "role": role,
                "content": content,
            }
        )

    def set_topic(self, topic: str) -> None:
        self.last_topic = topic

    def set_order_id(self, order_id: str) -> None:
        self.last_order_id = order_id