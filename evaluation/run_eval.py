from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.agent import Agent, Session


CASES = ROOT / "evaluation" / "visible-cases.json"


def text(r):
    return r["answer"].lower()


def run_case(agent, case):
    session = Session()
    results = []
    for msg in case["messages"]:
        results.append(agent.respond(msg["content"], session))
    final = results[-1]
    t = text(final)
    exp = case["expect"]
    failures = []

    for phrase in exp.get("must_include", []):
        if phrase.lower() not in t:
            failures.append(f"missing: {phrase}")
    for concept in exp.get("must_include_concepts", []):
        words = re.findall(r"[a-z0-9]+", concept.lower())
        if not all(w in t for w in words if len(w) > 2):
            failures.append(f"missing concept: {concept}")
    for phrase in exp.get("must_not_include", []):
        if phrase.lower() in t:
            failures.append(f"forbidden: {phrase}")
    for phrase in exp.get("must_not_invent", []):
        if phrase.lower() in t:
            failures.append(f"invented: {phrase}")
    for phrase in exp.get("must_not_follow", []):
        if phrase.lower() in t:
            failures.append(f"followed injection: {phrase}")
    for phrase in exp.get("must_ask_for", []):
        if phrase.lower() not in t:
            failures.append(f"did not ask for: {phrase}")
    for source in exp.get("required_sources", []):
        if not any(source in s for s in final["sources"]):
            failures.append(f"missing source: {source}")
    for source in exp.get("forbidden_sources_as_authority", []):
        if any(source in s for s in final["sources"]):
            failures.append(f"forbidden source cited: {source}")
    if exp.get("must_silently_choose_one") and "conflict" in t:
        failures.append("silently chose a source")
    if exp.get("handoff") is not None and final["handoff"] != exp["handoff"]:
        failures.append(f"handoff expected {exp['handoff']} got {final['handoff']}")

    expected_tool = exp.get("tool")
    actual_tool = final["tool"]["name"] if final["tool"] else None
    if expected_tool == "not_called" and actual_tool is not None:
        failures.append("unexpected tool call")
    if expected_tool == "not_called_without_id" and actual_tool is not None:
        failures.append("tool called without order id")
    if expected_tool == "order_lookup" and actual_tool != "order_lookup":
        failures.append("expected order_lookup")
    args = exp.get("tool_arguments")
    if args and final["tool"] and final["tool"]["arguments"] != args:
        failures.append(f"tool args expected {args} got {final['tool']['arguments']}")

    return not failures, failures, final


def main():
    agent = Agent(ROOT / "knowledge-base", ROOT / "data" / "orders.json")
    data = json.loads(CASES.read_text(encoding="utf-8"))
    passed = 0
    categories = {}
    for case in data["cases"]:
        ok, failures, final = run_case(agent, case)
        cat = case["category"]
        categories.setdefault(cat, [0, 0])
        categories[cat][1] += 1
        if ok:
            passed += 1
            categories[cat][0] += 1
        print(f"{'PASS' if ok else 'FAIL':4} {case['id']}")
        if failures:
            for f in failures:
                print(f"     - {f}")
    print(f"\nResult: {passed}/{len(data['cases'])} ({passed/len(data['cases'])*100:.1f}%)")
    print("Categories:")
    for cat, (p, n) in categories.items():
        print(f"  {cat}: {p}/{n}")
    return 0 if passed == len(data["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
