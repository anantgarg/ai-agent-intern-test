"""
logger.py

Structured logging for observability. Every conversation turn is
appended as one JSON line to logs/conversation_log.jsonl, containing:
the user message, the retrieved KB chunks, any tool calls made (name,
arguments, sanitized result), and the final response. This lets a
reviewer trace exactly what the agent saw and did for any turn,
without re-running the conversation.

Usage:
    from logger import log_turn
    log_turn(user_message, debug_info, final_response)
"""

import json
import os
from datetime import datetime, timezone

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "conversation_log.jsonl")


def log_turn(user_message, debug_info, final_response, session_id=None):
    """
    Appends one structured log entry for a single conversation turn.

    debug_info is the dict returned by agent.chat(), containing:
      - "tool_calls": list of {"name", "arguments", "result"}
      - "retrieved_hits": the formatted retrieved-context text block
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "user_message": user_message,
        "retrieved_context": debug_info.get("retrieved_hits", ""),
        "tool_calls": debug_info.get("tool_calls", []),
        "final_response": final_response,
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_log(limit=None):
    """
    Reads back logged entries (most recent last). Useful for a quick
    CLI inspection tool or for including sample logs in the README.
    """
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    if limit:
        return lines[-limit:]
    return lines


if __name__ == "__main__":
    entries = read_log(limit=5)
    print(f"Last {len(entries)} log entries:\n")
    for e in entries:
        print(f"[{e['timestamp']}] USER: {e['user_message'][:80]}")
        print(f"  Tool calls: {[t['name'] for t in e['tool_calls']]}")
        print(f"  Response: {e['final_response'][:100]}...\n")