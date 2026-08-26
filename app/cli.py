from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from .agent import Agent, Session


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aster & Row support agent"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="show retrieval/tool/LLM trace",
    )
    args = parser.parse_args()

    agent = Agent(
        ROOT / "knowledge-base",
        ROOT / "data" / "orders.json",
    )

    session = Session()

    print("Aster & Row Support Agent")
    print("Type 'exit' to quit. Debug mode:", args.debug)
    print()

    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if not user:
            continue

        result = agent.respond(user, session)

        print(f"Agent: {result['answer']}")

        if result["sources"]:
            print("Sources:")
            for source in result["sources"]:
                print(f"  - {source}")

        if result["handoff"]:
            print("Human support: recommended")

        if args.debug:
            trace = {
                "user_message": user,
                "recent_history": session.history[-4:],
                "tool": result["tool"],
                "sources": result["sources"],
                "llm_used": result["llm_used"],
                "llm_error": result.get("llm_error"),
                "handoff": result["handoff"],
                "final_response": result["answer"],
            }

            print("DEBUG:")
            print(
                json.dumps(
                    trace,
                    indent=2,
                    ensure_ascii=False,
                )
            )

        print()


if __name__ == "__main__":
    main()