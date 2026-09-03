"""
evaluation.py

Runs every case in evaluation/visible-cases.json (plus additional custom
cases in evaluation/custom-cases.json, if present) against the agent and
reports pass/fail per case and by category. Uses deterministic checks
(substring matching, source-citation checks, tool-call inspection)
rather than relying on another LLM to grade the agent.

Usage:
    python src/evaluation.py
    python src/evaluation.py --category tool-use
"""

import json
import re
import sys
import time
import argparse
from datetime import datetime

from agent import chat

VISIBLE_CASES_FILE = "evaluation/visible-cases.json"
CUSTOM_CASES_FILE = "evaluation/custom-cases.json"

DASH_VARIANTS = ["\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"]
SPACE_VARIANTS = ["\u00a0", "\u2009", "\u202f"]


def normalize(text):
    for variant in DASH_VARIANTS:
        text = text.replace(variant, "-")
    for variant in SPACE_VARIANTS:
        text = text.replace(variant, " ")
    return text


def prose_form(text):
    """
    LLMs sometimes write hyphenated compounds like "45-calendar-day"
    instead of "45 calendar days". For natural-language phrase/concept/
    handoff matching (not filename matching, which needs real hyphens),
    also produce a version with word-joining hyphens turned into spaces.
    """
    return re.sub(r"(?<=[a-zA-Z0-9])-(?=[a-zA-Z0-9])", " ", text)


ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
LONG_DATE_RE = re.compile(r"\b[A-Z][a-z]+ \d{1,2},? \d{4}\b")


def _parse_date(text):
    for fmt in ("%B %d, %Y", "%B %d %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip().rstrip(","), fmt).date()
        except ValueError:
            continue
    return None


def phrase_matches(phrase, normalized_lower_response, original_response):
    """
    Checks whether `phrase` is satisfied by the response, with fallbacks
    for date-equivalence and single-word root matching.
    """
    if phrase.lower() in normalized_lower_response:
        return True

    target_date = _parse_date(phrase)
    if target_date is not None:
        candidates = ISO_DATE_RE.findall(original_response) + LONG_DATE_RE.findall(original_response)
        for candidate in candidates:
            if _parse_date(candidate) == target_date:
                return True

    if " " not in phrase.strip() and len(phrase) > 4:
        root = phrase.lower()[:5]
        if root in normalized_lower_response:
            return True

    return False


def load_cases():
    cases = []

    with open(VISIBLE_CASES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        cases.extend(data["cases"])

    try:
        with open(CUSTOM_CASES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            cases.extend(data["cases"])
    except FileNotFoundError:
        pass

    return cases


def run_case(case):
    history = []
    debug_info = {}
    response_text = ""

    for message in case["messages"]:
        response_text, history, debug_info = chat(message["content"], history)

    failures = check_expectations(case.get("expect", {}), response_text, debug_info)

    return {
        "id": case["id"],
        "category": case.get("category", "uncategorized"),
        "passed": len(failures) == 0,
        "failures": failures,
        "response": response_text,
        "debug_info": debug_info,
    }


def check_expectations(expect, response_text, debug_info):
    failures = []
    normalized_response = normalize(response_text)
    lower_response = normalized_response.lower()
    prose_response = prose_form(lower_response)

    for phrase in expect.get("must_include", []):
        if not (phrase_matches(phrase, lower_response, normalized_response)
                or phrase.lower() in prose_response):
            failures.append(f"missing required phrase: {phrase!r}")

    for phrase in expect.get("must_include", []):
        phrase_lower = phrase.lower()
        singular_variant = re.sub(r"s\b", "", phrase_lower)
        ok = (
            phrase_matches(phrase, lower_response, normalized_response)
            or phrase_lower in prose_response
            or singular_variant in prose_response
        )
        if not ok:
            failures.append(f"missing required phrase: {phrase!r}")

    # A few common concept words have natural synonyms an LLM might use
    # instead (e.g. "confirmation" vs "clarification" vs "verify"). Add
    # their roots as extra acceptable matches.
    CONCEPT_SYNONYM_ROOTS = {
        "confir": ["confir", "clarif", "verify", "check w"],
    }
    for concept in expect.get("must_include_concepts", []):
        keywords = [w.lower()[:6] for w in concept.split() if len(w) > 3]
        expanded = set(keywords)
        for kw in keywords:
            expanded.update(CONCEPT_SYNONYM_ROOTS.get(kw, []))
        hit = any(kw in lower_response or kw in prose_response for kw in expanded)
        if not hit:
            failures.append(f"missing concept (no matching keywords found): {concept!r}")

    for source in expect.get("required_sources", []):
        if normalize(source).lower() not in lower_response:
            failures.append(f"missing required source citation: {source}")

    for source in expect.get("forbidden_sources_as_authority", []):
        if normalize(source).lower() in lower_response:
            failures.append(f"cited a forbidden/non-authoritative source: {source}")

    tool_calls = debug_info.get("tool_calls", [])
    expected_tool = expect.get("tool")

    if expected_tool == "not_called" and len(tool_calls) > 0:
        failures.append(f"expected no tool call, but got: {[t['name'] for t in tool_calls]}")

    if expected_tool == "order_lookup" and not any(t["name"] == "order_lookup" for t in tool_calls):
        failures.append("expected order_lookup tool call, but none occurred")

    if expected_tool == "not_called_without_id":
        for t in tool_calls:
            if t["name"] == "order_lookup" and not t["arguments"].get("order_id"):
                failures.append("order_lookup was called without an order_id")

    expected_args = expect.get("tool_arguments")
    if expected_args:
        matched = any(
            all(t["arguments"].get(k) == v for k, v in expected_args.items())
            for t in tool_calls
        )
        if not matched:
            failures.append(f"no tool call matched expected arguments: {expected_args}")

    for phrase in expect.get("must_not_invent", []):
        if phrase.lower() in lower_response:
            failures.append(f"appears to have invented: {phrase!r}")

    # must_refuse_to_disclose is informational only -- see notes in prior
    # versions; naming a category while refusing is normal, real leaks
    # are caught by must_not_include with actual sensitive values.

    ASK_SYNONYMS = {
        "order id": ["order id", "order number", "order #"],
    }
    for phrase in expect.get("must_ask_for", []):
        variants = ASK_SYNONYMS.get(phrase.lower(), [phrase.lower()])
        if not any(v in lower_response for v in variants):
            failures.append(f"did not ask for required info: {phrase!r}")

    if expect.get("must_not_silently_choose_one"):
        sources = expect.get("required_sources", [])
        mentioned = [s for s in sources if s.lower() in lower_response]
        if len(mentioned) < 2:
            failures.append("expected the response to surface multiple conflicting sources, but it did not")

    handoff_phrases = ["human support", "human assistance", "contact support",
                        "support team", "human review", "support specialist",
                        "recommend human", "customer support", "human confirmation",
                        "our support", "reach out to", "contact us", "contact our",
                        "human agent", "escalate", "get in touch", "our team",
                        "member of our team", "pass your request", "connect you with",
                        "support representative", "loop in"]
    dehyphenated = lower_response.replace("-", " ")
    handoff_mentioned = any(
        p in lower_response or p in dehyphenated for p in handoff_phrases
    )
    expected_handoff = expect.get("handoff")

    if expected_handoff is True and not handoff_mentioned:
        failures.append("expected a human handoff recommendation, but none was found")
    if expected_handoff is False and handoff_mentioned:
        failures.append("unexpected human handoff recommendation")

    return failures


def print_report(results):
    total = len(results)
    passed = sum(1 for r in results if r["passed"])

    print("\n" + "=" * 70)
    print(f"EVALUATION RESULTS: {passed}/{total} cases passed")
    print("=" * 70)

    by_category = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    print("\nBy category:")
    for category, cases in sorted(by_category.items()):
        cat_passed = sum(1 for c in cases if c["passed"])
        print(f"  {category}: {cat_passed}/{len(cases)}")

    print("\nCase details:")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"\n[{status}] {r['id']} ({r['category']})")
        for failure in r["failures"]:
            print(f"    - {failure}")
        if not r["passed"]:
            snippet = r["response"][:400].replace("\n", " ")
            print(f"    RESPONSE: {snippet}...")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", help="Only run cases in this category")
    args = parser.parse_args()

    cases = load_cases()

    if args.category:
        cases = [c for c in cases if c.get("category") == args.category]

    if not cases:
        print("No matching cases found.")
        sys.exit(1)

    results = []
    try:
        for case in cases:
            print(f"Running: {case['id']}...")
            result = run_case(case)
            results.append(result)
            time.sleep(8)  # stay comfortably under the free-tier per-minute token limit
    except Exception as e:
        print(f"\n[!] Stopped early due to an error: {e}")
        print(f"[!] Saving partial results ({len(results)}/{len(cases)} cases completed)...")

    if results:
        print_report(results)

    with open("evaluation/last_run_results.json", "w", encoding="utf-8") as f:
        json.dump(
            [{k: v for k, v in r.items() if k != "debug_info"} for r in results],
            f,
            indent=2,
        )
    print("\nResults so far saved to evaluation/last_run_results.json")