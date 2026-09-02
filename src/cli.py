"""
cli.py

Simple interactive command-line interface for the Aster & Row support
agent. Maintains conversation history across turns within one session,
and logs every turn to logs/conversation_log.jsonl for observability.

Usage:
    python src/cli.py

Type 'exit' or 'quit' to end the session.
Type 'debug' to toggle showing retrieved context and tool calls inline.
"""

import uuid
from agent import chat, format_retrieved_context
from logger import log_turn

DEBUG = False


def main():
    global DEBUG
    history = []
    session_id = str(uuid.uuid4())[:8]

    print("=" * 60)
    print("Aster & Row Support Agent (type 'exit' to quit, 'debug' to toggle debug mode)")
    print(f"Session ID: {session_id} -- logging to logs/conversation_log.jsonl")
    print("=" * 60)

    while True:
        user_input = input("\nYou: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Session ended.")
            break

        if user_input.lower() == "debug":
            DEBUG = not DEBUG
            print(f"[Debug mode {'ON' if DEBUG else 'OFF'}]")
            continue

        if DEBUG:
            print("\n--- Retrieved context ---")
            print(format_retrieved_context(user_input))
            print("--- End retrieved context ---\n")

        reply, history, debug_info = chat(user_input, history)
        print(f"\nAgent: {reply}")

        log_turn(user_input, debug_info, reply, session_id=session_id)


if __name__ == "__main__":
    main()