from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent.app import Session, SupportAgent  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    files = [ROOT / "evaluation" / "visible-cases.json", ROOT / "evals" / "extra-cases.json"]
    cases: list[dict[str, Any]] = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        cases.extend(data["cases"])
    return cases


def contains_all(text: str, needles: list[str]) -> list[str]:
    hay = text.lower()
    return [needle for needle in needles if needle.lower() not in hay]


def check_case(case: dict[str, Any], agent: SupportAgent) -> tuple[bool, list[str], str]:
    session = Session()
    final = None
    for message in case["messages"]:
        final = agent.respond(message["content"], session=session, debug=True)
    assert final is not None
    text = final.answer
    combined = text + "\n" + "\n".join(final.sources)
    expect = case.get("expect", {})
    failures: list[str] = []

    for key in ("must_include", "must_ask_for", "must_refuse_to_disclose", "must_include_concepts"):
        failures.extend([f"missing {item!r}" for item in contains_all(combined, expect.get(key, []))])
    for key in ("must_not_include", "must_not_invent", "must_not_follow"):
        forbidden = [item for item in expect.get(key, []) if item.lower() in combined.lower()]
        failures.extend([f"forbidden text present {item!r}" for item in forbidden])
    for source in expect.get("required_sources", []):
        if source not in "\n".join(final.sources):
            failures.append(f"required source missing {source}")
    for source in expect.get("forbidden_sources_as_authority", []):
        if source in "\n".join(final.sources):
            failures.append(f"forbidden source cited {source}")

    expected_tool = expect.get("tool")
    tool_names = [call.name for call in final.tool_calls]
    if expected_tool == "not_called" and tool_names:
        failures.append(f"unexpected tool call {tool_names}")
    elif expected_tool == "not_called_without_id" and tool_names:
        failures.append(f"tool called without id {tool_names}")
    elif expected_tool in {"order_lookup", "optional_sanitized_lookup"}:
        if expected_tool == "order_lookup" and "order_lookup" not in tool_names:
            failures.append("order_lookup not called")
        if "tool_arguments" in expect and final.tool_calls:
            got = final.tool_calls[-1].arguments
            for key, value in expect["tool_arguments"].items():
                if got.get(key) != value:
                    failures.append(f"tool arg {key} expected {value} got {got.get(key)}")
    if "handoff" in expect and final.handoff != expect["handoff"]:
        failures.append(f"handoff expected {expect['handoff']} got {final.handoff}")
    return not failures, failures, text


def main() -> int:
    agent = SupportAgent()
    cases = load_cases()
    by_category: dict[str, list[bool]] = defaultdict(list)
    failures = []
    for case in cases:
        passed, errors, answer = check_case(case, agent)
        by_category[case["category"]].append(passed)
        print(f"{'PASS' if passed else 'FAIL'} {case['id']} [{case['category']}]")
        if not passed:
            for error in errors:
                print(f"  - {error}")
            print(f"  answer: {answer}")
            failures.append(case["id"])
    print("\nCategory results")
    for category in sorted(by_category):
        values = by_category[category]
        print(f"- {category}: {sum(values)}/{len(values)}")
    total = sum(sum(values) for values in by_category.values())
    count = sum(len(values) for values in by_category.values())
    print(f"\nOverall: {total}/{count}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

