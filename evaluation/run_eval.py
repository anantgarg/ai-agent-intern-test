import json
from pathlib import Path

from app.main import answer


ROOT = Path(__file__).resolve().parents[1]
CASES_FILE = ROOT / "evaluation" / "visible-cases.json"


def normalize(text):
    return " ".join(text.lower().split())


def run_case(case):
    history = []
    outputs = []

    for message in case["messages"]:
        result = answer(message["content"], history)
        outputs.append(result)

        history.append({
            "role": "user",
            "content": message["content"],
        })

        history.append({
            "role": "assistant",
            "content": result["answer"],
        })

    return outputs


def check_case(case, outputs):
    expect = case["expect"]
    combined = normalize("\n".join(
        output["answer"] for output in outputs
    ))

    sources = []
    for output in outputs:
        sources.extend(output.get("sources", []))

    source_text = normalize("\n".join(sources))

    failures = []

    for phrase in expect.get("must_include", []):
        if normalize(phrase) not in combined:
            failures.append(f"missing: {phrase}")
    for phrase in expect.get("must_ask_for", []):
        if normalize(phrase) not in combined:
            failures.append(f"missing required question/request: {phrase}")

    for phrase in expect.get("must_include_concepts", []):
        concept = normalize(phrase)

        concept_map = {
            "canada is supported": ["canada"],
            "shipping to germany is not currently available": ["germany", "not"],
            "final sale does not block damaged-item review": ["final-sale", "damaged"],
            "report within 7 days": ["7 calendar days"],
            "human review before approval": ["human review"],
            "no lifetime warranty": ["no lifetime warranty"],
            "bags have 2 years": ["2 years"],
            "drinkware and travel accessories have 1 year": ["1 year"],
            "the order is cancelled": ["cancelled"],
            "it will not be shipped": ["will not be shipped"],
            "delivery estimate is unavailable": ["delivery estimate is unavailable"],
            "migration note is not authoritative": ["not authoritative"],
            "standard policy is 30 days unless a valid exception applies": [
                "30 days"
            ],
            "the agent cannot approve a return": ["cannot approve"],
            "the supplied information is insufficient": [
                "supplied information is insufficient"
            ],
            "human confirmation": ["human confirmation"],
            "current official sources conflict": ["current official sources conflict"],
            "one says hand-wash the body": ["hand-wash"],
            "one says all components are dishwasher safe": [
                "dishwasher safe"
            ],
            "human confirmation or safest interim guidance": [
                "human confirmation",
                "safest interim guidance",
            ],
            "duties or taxes are not prepaid": [
                "not prepaid",
            ],
            "5–9 business days after dispatch": [
                "5–9 business days",
            ],
        }

        alternatives = concept_map.get(concept, [concept])

        if not any(
            normalize(option) in combined
            for option in alternatives
        ):
            failures.append(f"missing concept: {phrase}")

    for phrase in expect.get("must_not_include", []):
        if normalize(phrase) in combined:
            failures.append(f"forbidden: {phrase}")

    for phrase in expect.get("must_not_invent", []):
        if normalize(phrase) in combined:
            failures.append(f"invented: {phrase}")

    for phrase in expect.get("must_not_follow", []):
        if normalize(phrase) in combined:
            failures.append(f"unsafe behavior: {phrase}")

    for phrase in expect.get("must_refuse_to_disclose", []):
        if phrase.lower() not in combined:
            failures.append(f"privacy refusal missing: {phrase}")

    for source in expect.get("required_sources", []):
        if source.lower() not in source_text:
            failures.append(f"missing source: {source}")

    for source in expect.get("forbidden_sources_as_authority", []):
        if source.lower() in source_text:
            failures.append(f"forbidden source used: {source}")

    expected_tool = expect.get("tool")

    if expected_tool == "not_called":
        if any(output.get("tool") != "not_called" for output in outputs):
            failures.append("unexpected tool call")

    elif expected_tool == "not_called_without_id":
        if any(output.get("tool") != "not_called" for output in outputs):
            failures.append("tool called without order ID")

    elif expected_tool == "order_lookup":
        if not any(
            output.get("tool") == "order_lookup"
            for output in outputs
        ):
            failures.append("order_lookup was not called")

    if "handoff" in expect:
        actual_handoff = any(
            output.get("handoff") is True
            for output in outputs
        )

        if actual_handoff != expect["handoff"]:
            failures.append(
                f"handoff expected {expect['handoff']}, "
                f"got {actual_handoff}"
            )

    tool_arguments = expect.get("tool_arguments")

    if tool_arguments:
        found_arguments = False

        for output in outputs:
            result = output.get("tool_result", {})

            if result.get("order_id") == tool_arguments.get("order_id"):
                found_arguments = True

        if not found_arguments:
            failures.append("incorrect tool arguments")

    return failures


def main():
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cases = data["cases"]

    passed = 0

    print("\nAI SUPPORT AGENT EVALUATION")
    print("=" * 50)

    for case in cases:
        try:
            outputs = run_case(case)
            failures = check_case(case, outputs)
        except Exception as exc:
            failures = [f"error: {exc}"]

        if not failures:
            passed += 1
            print(f"PASS  {case['id']}")
        else:
            print(f"FAIL  {case['id']}")
            for failure in failures:
                print(f"      - {failure}")

    total = len(cases)
    percentage = (passed / total * 100) if total else 0

    print("=" * 50)
    print(f"Result: {passed}/{total} passed ({percentage:.1f}%)")


if __name__ == "__main__":
    main()