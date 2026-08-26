from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import Agent
from app.llm import GeminiGenerator

ROOT = Path(__file__).resolve().parents[1]


class FakeLLM:
    configured = True

    def __init__(self):
        self.calls = []

    def generate(self, system, prompt):
        self.calls.append((system, prompt))
        return "Grounded answer. Sources: 01-returns-policy-current.md — Standard return window"


def test_agent_invokes_llm_for_grounded_kb_answer():
    fake = FakeLLM()
    agent = Agent(ROOT / "knowledge-base", ROOT / "data/orders.json", llm=fake)
    result = agent.respond("How long does a regular customer have to return an unused backpack?")
    assert result["llm_used"] is True
    assert len(fake.calls) == 1
    assert "30 calendar days" in result["answer"]  # failed contract triggers safe fallback


def test_order_tool_result_is_available_to_llm_but_internal_fields_are_not():
    fake = FakeLLM()
    agent = Agent(ROOT / "knowledge-base", ROOT / "data/orders.json", llm=fake)
    agent.respond("Where is ORD-1007 and when should it arrive?")
    assert len(fake.calls) == 1
    prompt = fake.calls[0][1]
    assert "ORD-1007" in prompt
    assert "customer_safe_message" in prompt
    assert "ava.morgan@example.test" not in prompt
    assert "risk_score" not in prompt
