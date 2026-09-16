from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Passage:
    filename: str
    title: str
    heading: str
    text: str
    metadata: dict[str, str]
    score: float = 0.0

    @property
    def source(self) -> str:
        return f"{self.filename} > {self.heading}"


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


@dataclass
class AgentResponse:
    answer: str
    sources: list[str] = field(default_factory=list)
    handoff: bool = False
    tool_calls: list[ToolCall] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)

