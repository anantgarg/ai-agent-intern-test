"""Minimal CLI: ask questions, see answer + sources + handoff + optional trace."""
from __future__ import annotations

import argparse
import json
import sys

from .agent import Agent


def main() -> None:
    ap = argparse.ArgumentParser(description="Aster & Row support agent (local, deterministic)")
    ap.add_argument("--kb", default="knowledge-base")
    ap.add_argument("--orders", default="data/orders.json")
    ap.add_argument("--trace", action="store_true", help="print structured trace JSON to stderr")
    ap.add_argument("question", nargs="*", help="single question (otherwise interactive)")
    args = ap.parse_args()

    agent = Agent(kb_dir=args.kb, orders_path=args.orders)
    session = agent.new_session()

    def ask(q: str):
        res = agent.chat(session, q)
        print("\nAnswer:\n" + res["answer"])
        if res.get("sources"):
            print("\nSources: " + ", ".join(res["sources"]))
        print(f"\nHandoff: {'Yes' if res['handoff'] else 'No'}"
              + (f" — {res['handoff_reason']}" if res.get("handoff_reason") else ""))
        if args.trace:
            print("\n--- TRACE ---", file=sys.stderr)
            print(json.dumps(res["trace"], indent=2)[:6000], file=sys.stderr)

    if args.question:
        ask(" ".join(args.question))
        return
    print("Aster & Row support agent. Type 'quit' to exit.")
    while True:
        try:
            q = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("quit", "exit"):
            break
        if not q:
            continue
        ask(q)


if __name__ == "__main__":
    main()
