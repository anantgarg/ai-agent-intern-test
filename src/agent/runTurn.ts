import type OpenAI from "openai";
import chalk from "chalk";
import { config } from "../config.js";
import { getOpenRouterClient, getModel } from "./openRouterClient.js";
import { SYSTEM_PROMPT, buildUserTurnPrompt } from "./prompts.js";
import { getRetriever } from "../retrieval/retriever.js";
import {
  LOOKUP_ORDER_TOOL,
  lookupOrder,
} from "../tools/lookupOrder.js";
import type {
  AgentTurnResult,
  ChatMessage,
  RetrievedChunk,
  SourceRef,
  ToolCallRecord,
} from "../types.js";

type ChatMessageParam = OpenAI.Chat.ChatCompletionMessageParam;

function parseMeta(raw: string): {
  answer: string;
  sources: SourceRef[];
  handoff: boolean;
  abstained: boolean;
} {
  const metaMatch = raw.match(
    /---META---([\s\S]*?)---END---/i,
  );
  let answer = raw;
  let sources: SourceRef[] = [];
  let handoff = false;
  let abstained = false;

  if (metaMatch) {
    answer = raw.slice(0, metaMatch.index).trim();
    const block = metaMatch[1] ?? "";
    const sourcesLine = /SOURCES:\s*(.+)/i.exec(block)?.[1]?.trim() ?? "none";
    if (!/^none$/i.test(sourcesLine)) {
      sources = sourcesLine
        .split("|")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((part) => {
          const [filename, ...rest] = part.split("#");
          return {
            filename: (filename ?? "").trim(),
            heading: rest.join("#").trim() || "(document)",
          };
        });
    }
    handoff = /HANDOFF:\s*yes/i.test(block);
    abstained = /ABSTAIN:\s*yes/i.test(block);
  }

  // Fallback heuristics if model omitted META
  if (!metaMatch) {
    handoff =
      /\b(human|support team|contact support|escalate|cannot (confirm|approve)|insufficient)\b/i.test(
        answer,
      );
    abstained =
      /\b(insufficient|do not have (enough|that) information|cannot (determine|confirm))\b/i.test(
        answer,
      );
  }

  return { answer, sources, handoff, abstained };
}

export async function runTurn(options: {
  userMessage: string;
  history?: ChatMessage[];
  sessionId?: string;
  retriever?: ReturnType<typeof getRetriever>;
}): Promise<AgentTurnResult> {
  const history = options.history ?? [];
  const retriever = options.retriever ?? getRetriever();
  const client = getOpenRouterClient();

  // Expand retrieval query with recent user context for multi-turn follow-ups.
  const priorUser = history
    .filter((m) => m.role === "user")
    .slice(-2)
    .map((m) => m.content)
    .join(" ");
  const retrievalQuery = priorUser
    ? `${priorUser}\n${options.userMessage}`
    : options.userMessage;

  const retrieved: RetrievedChunk[] = retriever.retrieve(retrievalQuery);

  const messages: ChatMessageParam[] = [
    { role: "system", content: SYSTEM_PROMPT },
    ...history.map((m) => ({
      role: m.role as "user" | "assistant",
      content: m.content,
    })),
    {
      role: "user",
      content: buildUserTurnPrompt(options.userMessage, retrieved),
    },
  ];

  const toolCalls: ToolCallRecord[] = [];
  let finalText = "";

  for (let round = 0; round < config.maxToolRounds; round++) {
    const response = await client.chat.completions.create({
      model: getModel(),
      max_tokens: 1600,
      messages,
      tools: [LOOKUP_ORDER_TOOL],
      tool_choice: "auto",
    });

    const choice = response.choices[0];
    const message = choice?.message;
    if (!message) {
      break;
    }

    const pendingTools = message.tool_calls ?? [];
    if (pendingTools.length === 0 || choice.finish_reason === "stop") {
      finalText = (message.content ?? "").trim();
      break;
    }

    messages.push({
      role: "assistant",
      content: message.content,
      tool_calls: pendingTools,
    });

    for (const toolCall of pendingTools) {
      if (toolCall.type !== "function") continue;

      if (toolCall.function.name === "lookup_order") {
        let orderId = "";
        try {
          const parsed = JSON.parse(toolCall.function.arguments || "{}") as {
            order_id?: string;
          };
          orderId = String(parsed.order_id ?? "");
        } catch {
          orderId = "";
        }
        const result = lookupOrder(orderId);
        toolCalls.push({
          name: "lookup_order",
          arguments: { order_id: orderId },
          result,
        });
        messages.push({
          role: "tool",
          tool_call_id: toolCall.id,
          content: JSON.stringify(result),
        });
      } else {
        messages.push({
          role: "tool",
          tool_call_id: toolCall.id,
          content: JSON.stringify({ error: "Unknown tool" }),
        });
      }
    }

    if (round === config.maxToolRounds - 1) {
      const last = await client.chat.completions.create({
        model: getModel(),
        max_tokens: 1600,
        messages,
      });
      finalText = (last.choices[0]?.message?.content ?? "").trim();
    }
  }

  const parsed = parseMeta(finalText);

  // If model forgot sources but we have authoritative retrieval, attach top hits.
  if (parsed.sources.length === 0 && retrieved.length > 0) {
    const authoritative = retrieved.filter(
      (c) =>
        String(c.metadata.status).toLowerCase() === "active" &&
        String(c.metadata.policy_authority).toLowerCase() === "official" &&
        c.metadata.customer_answering !== false,
    );
    const pick = (authoritative.length ? authoritative : retrieved).slice(0, 3);
    // Only auto-fill when the answer looks policy-like (not a pure clarify ask).
    if (!/order id|could you (share|provide)|please (share|provide)/i.test(parsed.answer)) {
      parsed.sources = pick.map((c) => ({
        filename: c.filename,
        heading: c.heading,
      }));
    }
  }

  return {
    answer: parsed.answer || finalText,
    sources: parsed.sources,
    handoff: parsed.handoff,
    toolCalls,
    retrieved,
    abstained: parsed.abstained,
  };
}

export function formatCustomerResponse(result: AgentTurnResult): string {
  const lines = [result.answer.trim(), ""];
  if (result.sources.length > 0) {
    lines.push(chalk.dim("Sources:"));
    for (const s of result.sources) {
      lines.push(
        chalk.dim("  · ") +
          chalk.cyan(s.filename) +
          chalk.dim(" — ") +
          chalk.white(s.heading),
      );
    }
    lines.push("");
  }
  if (result.handoff) {
    lines.push(chalk.yellow("⚠ Human handoff recommended"));
  }
  return lines.join("\n").trim();
}

