"""Shared pytest fixtures/helpers for the Aster & Row agent test matrix.

Stdlib + pytest only. Read-only against app/data (never modifies source).
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent import Agent  # noqa: E402

PII_FORBIDDEN = [
    "ava.morgan@example.test",
    "maya.reed@example.test",
    "noah.kim@example.test",
    "olivia.chen@example.test",
    "ethan.brooks@example.test",
    "sofia.patel@example.test",
    "liam.jones@example.test",
    "lucas.green@example.test",
    "isabella.stone@example.test",
    "henry.diaz@example.test",
    "emma.wilson@example.test",
    "james.taylor@example.test",
    "220 king street",
    "fraud review",
]

ALL_ORDER_IDS = [f"ORD-{n:04d}" for n in range(1001, 1013)]


@pytest.fixture(scope="session")
def agent():
    return Agent(kb_dir=str(ROOT / "knowledge-base"),
                 orders_path=str(ROOT / "data" / "orders.json"))


@pytest.fixture()
def fresh_session(agent):
    return agent.new_session()


def chat(agent, session, *messages):
    """Send messages in one session; return (last_result, all_results)."""
    results = []
    for m in messages:
        results.append(agent.chat(session, m))
    return results[-1], results


def load_orders_raw():
    return json.loads((ROOT / "data" / "orders.json").read_text(encoding="utf-8"))
