import type { ChatMessage } from "../types.js";
import { config } from "../config.js";

export class SessionStore {
  private readonly sessions = new Map<string, ChatMessage[]>();

  get(sessionId: string): ChatMessage[] {
    return [...(this.sessions.get(sessionId) ?? [])];
  }

  append(sessionId: string, user: string, assistant: string): void {
    const history = this.get(sessionId);
    history.push({ role: "user", content: user });
    history.push({ role: "assistant", content: assistant });

    // Keep last N turns (each turn = user + assistant).
    const maxMessages = config.maxHistoryTurns * 2;
    const trimmed =
      history.length > maxMessages
        ? history.slice(history.length - maxMessages)
        : history;
    this.sessions.set(sessionId, trimmed);
  }

  clear(sessionId: string): void {
    this.sessions.delete(sessionId);
  }
}

export const sessions = new SessionStore();
