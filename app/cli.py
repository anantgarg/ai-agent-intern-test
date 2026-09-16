from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from .agent import SupportAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Aster & Row Support Agent")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    agent = SupportAgent(args.repo, debug=args.debug)
    print("Aster & Row Support Agent. Type 'exit' to quit.")
    while True:
        msg = input("You: ").strip()
        if msg.lower() in {"exit", "quit"}:
            break
        result = agent.answer(msg)
        print(f"\nAgent: {result.answer}")
        if result.sources:
            print("Sources:")
            for s in result.sources:
                print(f"- {s}")
        print(f"Handoff: {'yes' if result.handoff else 'no'}\n")


if __name__ == "__main__":
    main()
