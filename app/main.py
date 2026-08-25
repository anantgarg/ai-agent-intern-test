import sys
from app.agent import SupportAgent


def main():
    print("=" * 60)
    print(" Aster & Row AI Support Agent - Interactive CLI")
    print(" Type 'exit' or 'quit' to end session.")
    print("=" * 60)

    agent = SupportAgent()

    while True:
        try:
            user_input = input("\nUser > ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            result = agent.answer(user_input)

            print("\nAssistant >", result["answer"])

            if result.get("sources"):
                print("\n[Sources]")
                for src in result["sources"]:
                    print(f" - {src['filename']} ({src.get('heading', 'Document')})")

            if result.get("tool_call"):
                tool = result["tool_call"]
                print(f"\n[Tool Execution]: {tool['name']}({tool['arguments']})")

            print(f"[Human Handoff]: {result['handoff']}")

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()
