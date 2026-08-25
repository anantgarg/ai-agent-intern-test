from dataclasses import dataclass, field

@dataclass
class Session:
    messages: list[dict] = field(default_factory=list)
    active_order_id: str | None = None

class SessionStore:
    def __init__(self, max_messages: int = 12):
        self.sessions = {}
        self.max_messages = max_messages

    def get(self, session_id: str) -> Session:
        return self.sessions.setdefault(session_id, Session())

    def add(self, session_id: str, role: str, content: str):
        session = self.get(session_id)
        session.messages.append({"role": role, "content": content})
        session.messages = session.messages[-self.max_messages:]
