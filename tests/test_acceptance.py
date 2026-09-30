"""LEVEL: Acceptance / UAT — does it satisfy the business requirements?

Independent re-check of every visible + extra case (own assertions, not the
eval runner). Reviewers use paraphrases, so wording here is deliberately exact.
"""
import json

import pytest

from .conftest import ROOT


def load_cases():
    vis = json.loads((ROOT / "evaluation" / "visible-cases.json").read_text(encoding="utf-8"))["cases"]
    ext = json.loads((ROOT / "eval" / "extra-cases.json").read_text(encoding="utf-8"))["cases"]
    return vis + ext


def last_answer(agent, messages):
    s = agent.new_session()
    traces = []
    res = None
    for m in messages:
        res = agent.chat(s, m["content"])
        traces.append(res["trace"])
    return res, traces


ALL_CASES = load_cases()
IDS = [c["id"] for c in ALL_CASES]


@pytest.mark.parametrize("case_id", IDS)
def test_acceptance_tool_behavior(agent, case_id):
    case = next(c for c in ALL_CASES if c["id"] == case_id)
    exp = case.get("expect", {})
    res, traces = last_answer(agent, case["messages"])
    calls = [c for t in traces for c in t["tool_calls"]]
    want = exp.get("tool")
    if want == "not_called":
        assert calls == [], f"{case_id}: expected no tool calls"
    elif want == "not_called_without_id":
        assert calls == [], f"{case_id}: expected no call without ID"
    elif want == "order_lookup":
        assert any(c["tool"] == "order_lookup" for c in calls), f"{case_id}: lookup missing"
        if exp.get("tool_arguments", {}).get("order_id"):
            got = [c["args"]["order_id"] for c in calls if c["tool"] == "order_lookup"]
            assert exp["tool_arguments"]["order_id"] in got
    elif want == "optional_sanitized_lookup":
        blob = json.dumps(calls).lower()
        for bad in ("example.test", "risk_score", "warehouse_note", "shipping_address"):
            assert bad not in blob


@pytest.mark.parametrize("case_id", IDS)
def test_acceptance_handoff(agent, case_id):
    case = next(c for c in ALL_CASES if c["id"] == case_id)
    if "handoff" not in case.get("expect", {}):
        pytest.skip("no handoff expectation")
    res, _ = last_answer(agent, case["messages"])
    assert res["handoff"] is bool(case["expect"]["handoff"]), case_id


@pytest.mark.parametrize("case_id", IDS)
def test_acceptance_required_sources(agent, case_id):
    case = next(c for c in ALL_CASES if c["id"] == case_id)
    for src in case.get("expect", {}).get("required_sources", []):
        res, _ = last_answer(agent, case["messages"])
        assert src in res["sources"] or src in res["answer"], f"{case_id}: {src}"
