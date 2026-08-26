import json
import re
from typing import Any
import pytest
from agent import run_agent


def load_eval_cases(filepath: str = "eval_cases.json"):
    with open(filepath, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return data.get("cases", [])


CASES = load_eval_cases()


def normalize_text(text: str) -> str:
    """Removes punctuation and normalizes 'days' to 'day' while preserving spaces."""
    text = text.lower().replace('-', ' ')
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip().replace('days', 'day')


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_evaluation_case(case: Any):
    messages = case["messages"]
    expect = case["expect"]

    # Extract the user's query string and any preceding history
    query = messages[-1]["content"]
    history = messages[:-1]

   
    response_text, state = run_agent(query, history=history)

    expected_tool = expect.get("tool")
    tools_called = state.get("tools_called", [])
    actual_tool = state.get("tool_called") or (
        tools_called[0] if tools_called else None
    )

    if expected_tool == "not_called":
        assert (
            not tools_called and actual_tool is None
        ), f"Expected no tool call, but got '{tools_called or actual_tool}'"
    elif expected_tool and expected_tool not in [
        "not_called_without_id",
        "optional_sanitized_lookup",
    ]:
        assert (
            expected_tool in tools_called or actual_tool == expected_tool
        ), f"Expected tool '{expected_tool}', got '{tools_called or actual_tool}'"

    expected_handoff = expect.get("handoff", False)
    actual_handoff = state.get("handoff_triggered", False)
    assert (
        actual_handoff == expected_handoff
    ), f"Expected handoff {expected_handoff}, got {actual_handoff}"

    norm_resp = normalize_text(response_text)

    for phrase in expect.get("must_include", []):
        assert (
            normalize_text(phrase) in norm_resp
        ), f"Missing required phrase: '{phrase}'"

    for phrase in expect.get("must_not_include", []):
        pattern = r'\b' + re.escape(normalize_text(phrase)) + r'\b'
        assert not re.search(pattern, norm_resp), f"Contains forbidden phrase: '{phrase}'"

   