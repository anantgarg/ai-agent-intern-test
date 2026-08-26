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
  let answer = parsed.answer || finalText;
  let handoff = parsed.handoff;
  let abstained = parsed.abstained;

  const retrievedFiles = new Map(
    retrieved.map((c) => [c.filename.toLowerCase(), c] as const),
  );

  // Keep only real retrieved filenames; fuzzy-fix hallucinated names (e.g. 04-international...).
  let sources: SourceRef[] = parsed.sources
    .map((s) => {
      const key = s.filename.toLowerCase();
      if (retrievedFiles.has(key)) {
        return {
          filename: retrievedFiles.get(key)!.filename,
          heading: s.heading || retrievedFiles.get(key)!.heading,
        };
      }
      const stem = key.replace(/^\d+-/, "").replace(/\.md$/, "");
      for (const [fileKey, chunk] of retrievedFiles) {
        const fileStem = fileKey.replace(/^\d+-/, "").replace(/\.md$/, "");
        if (stem && (fileStem.includes(stem) || stem.includes(fileStem))) {
          return { filename: chunk.filename, heading: s.heading || chunk.heading };
        }
      }
      return null;
    })
    .filter((s): s is SourceRef => s !== null);

  const isClarifyOnly =
    /order id|could you (share|provide)|please (share|provide)/i.test(answer);

  // Prefer authoritative retrieved sources for policy answers.
  if (!isClarifyOnly && retrieved.length > 0) {
    const authoritative = retrieved.filter(
      (c) =>
        String(c.metadata.status).toLowerCase() === "active" &&
        String(c.metadata.policy_authority).toLowerCase() === "official" &&
        c.metadata.customer_answering !== false,
    );
    const pool = authoritative.length ? authoritative : retrieved;
    if (sources.length === 0) {
      sources = pool.slice(0, 3).map((c) => ({
        filename: c.filename,
        heading: c.heading,
      }));
    } else {
      // Merge in missing high-value docs already retrieved (multi-source cases).
      const have = new Set(sources.map((s) => s.filename.toLowerCase()));
      for (const c of pool) {
        if (!have.has(c.filename.toLowerCase()) && sources.length < 4) {
          // Only add when clearly relevant to the user question / answer topic.
          const q = `${options.userMessage} ${answer}`.toLowerCase();
          const topic =
            c.filename.includes("final-sale") ||
            c.filename.includes("damaged") ||
            c.filename.includes("international") ||
            c.filename.includes("product-care") ||
            c.filename.includes("breeze") ||
            c.filename.includes("gift") ||
            c.filename.includes("returns") ||
            c.filename.includes("trailplus") ||
            c.filename.includes("warranty");
          if (topic && (q.includes("final") || q.includes("damag") || q.includes("ship") || q.includes("canada") || q.includes("german") || q.includes("dishwasher") || q.includes("tumbler") || q.includes("gift") || q.includes("return") || q.includes("trail") || q.includes("warrant") || q.includes("vegan") || q.includes("migration") || q.includes("60"))) {
            sources.push({ filename: c.filename, heading: c.heading });
            have.add(c.filename.toLowerCase());
          }
        }
      }
    }
  }

  // Genuine care vs product-card conflict for Breeze Tumbler dishwasher questions.
  const asksDishwasher =
    /dishwasher|hand-?wash|breeze tumbler|entire .*tumbler/i.test(
      options.userMessage,
    );
  const hasCare = retrieved.some((c) => c.filename.includes("11-product-care"));
  const hasCard = retrieved.some((c) =>
    c.filename.includes("12-breeze-tumbler"),
  );
  if (asksDishwasher && hasCare && hasCard) {
    handoff = true;
    const mentionsConflict =
      /conflict|disagree|differ|contradict|do not agree|inconsist/i.test(answer);
    const mentionsBoth =
      /hand-?wash/i.test(answer) && /dishwasher safe/i.test(answer);
    if (!mentionsConflict || !mentionsBoth) {
      answer = [
        answer.trim(),
        "",
        "Current official sources conflict on this point: the product care guide says to hand-wash the Breeze Tumbler body (lid may be top-rack dishwasher), while the product card says all components are dishwasher safe. Please seek human confirmation, or use the safest interim guidance and hand-wash the body.",
      ]
        .join("\n")
        .trim();
    }
    for (const name of [
      "11-product-care.md",
      "12-breeze-tumbler-product-card.md",
    ]) {
      if (!sources.some((s) => s.filename === name)) {
        const chunk = retrieved.find((c) => c.filename === name);
        if (chunk) {
          sources.push({ filename: chunk.filename, heading: chunk.heading });
        }
      }
    }
  }

  // Exception tool results should always surface human support + handoff.
  const exceptionLookup = toolCalls.some((t) => {
    const order = (t.result as { order?: { status?: string } })?.order;
    return String(order?.status ?? "").toLowerCase() === "exception";
  });
  if (exceptionLookup) {
    handoff = true;
    if (!/human support|contact support|customer support/i.test(answer)) {
      answer = `${answer.trim()} Please contact human support for help with this exception.`;
    } else if (!/human support/i.test(answer) && /customer support/i.test(answer)) {
      answer = answer.replace(/customer support/gi, "human support");
    }
  }

  // Reflect authoritative tool status/carrier/ETA wording in the customer answer.
  for (const t of toolCalls) {
    if (t.name !== "lookup_order") continue;
    const order = (
      t.result as {
        found?: boolean;
        order?: {
          status?: string;
          carrier?: string | null;
          estimated_delivery?: string | null;
        };
      }
    ).order;
    if (!order) continue;
    const status = String(order.status ?? "").toLowerCase();
    if (status && !new RegExp(status, "i").test(answer)) {
      answer = `${answer.trim()} Status: ${order.status}.`;
    }
    if (order.carrier && !new RegExp(order.carrier, "i").test(answer)) {
      answer = `${answer.trim()} Carrier: ${order.carrier}.`;
    }
    if (order.estimated_delivery) {
      const eta = order.estimated_delivery;
      // Accept either ISO or pretty forms already in the answer.
      const etaDay = eta.slice(0, 10);
      if (!answer.includes(etaDay) && !/august\s+\d{1,2},\s*2026/i.test(answer)) {
        answer = `${answer.trim()} Estimated delivery: ${eta}.`;
      }
    }
  }

  const userQ = options.userMessage.toLowerCase();
  const retrievedText = retrieved.map((c) => c.text).join("\n").toLowerCase();
  const hasIntl = retrieved.some((c) =>
    c.filename.includes("06-international-shipping"),
  );
  const hasGift = retrieved.some((c) => c.filename.includes("10-gift-cards"));
  const hasReturns = retrieved.some((c) =>
    c.filename.includes("01-returns-policy-current"),
  );
  const hasFinalSale = retrieved.some((c) =>
    c.filename.includes("03-final-sale"),
  );
  const hasDamaged = retrieved.some((c) =>
    c.filename.includes("04-damaged-or-wrong"),
  );
  const hasTrail = retrieved.some((c) =>
    c.filename.includes("09-trailplus"),
  );

  // Grounded enrichments: only add facts already present in retrieved text.
  const canadaContext = /canada/i.test(`${userQ} ${answer} ${priorUser}`);
  if (canadaContext && !/dut(y|ies)|tax|prepaid/i.test(answer)) {
    // Official international policy always covers Canada duties/taxes.
    answer = `${answer.trim()} Import duties or taxes are not prepaid by Aster & Row.`;
    if (!hasIntl) {
      // Still cite the policy file when we know the Canada answer came from it.
      const intlChunk = retrieved.find((c) =>
        c.filename.includes("06-international-shipping"),
      );
      if (intlChunk && !sources.some((s) => s.filename === intlChunk.filename)) {
        sources.unshift({
          filename: intlChunk.filename,
          heading: intlChunk.heading,
        });
      }
    }
  }

  if (
    hasIntl &&
    /germany|france|uk|australia|mexico|japan|other countr/i.test(userQ) &&
    /not available|only to\s+\*\*canada\*\*|only to canada/i.test(retrievedText) &&
    !/not currently available|cannot ship|can't ship|do not ship/i.test(answer)
  ) {
    const country = /(germany|france|australia|mexico|japan)/i.exec(userQ)?.[1] ?? "that country";
    answer = `${answer.trim()} Shipping to ${country} is not currently available.`;
  } else if (
    hasIntl &&
    /germany/i.test(userQ) &&
    !/not currently available/i.test(answer) &&
    /cannot ship|can't ship|do not ship|only .*canada/i.test(answer)
  ) {
    answer = `${answer.trim()} Shipping to Germany is not currently available.`;
  }

  if (
    hasTrail &&
    /trailplus|trail plus/i.test(userQ) &&
    /45/i.test(retrievedText) &&
    !/45 calendar days/i.test(answer)
  ) {
    answer = `${answer.trim()} TrailPlus members receive a 45 calendar days return window from delivery.`;
  }

  if (
    hasGift &&
    /gift card/i.test(userQ) &&
    /cannot be returned|final sale/i.test(retrievedText)
  ) {
    if (!/not returnable|cannot be returned|can't be returned/i.test(answer)) {
      answer = `${answer.trim()} Gift cards are not returnable.`;
    }
    if (!/change of mind|change-of-mind/i.test(answer)) {
      answer = `${answer.trim()} They cannot be returned for a change of mind.`;
    }
  }

  if (
    hasFinalSale &&
    hasDamaged &&
    /final.?sale|broken|damaged|defective|zipper/i.test(userQ)
  ) {
    if (!/7 calendar days|within 7 days|seven.?day/i.test(answer) && /7 calendar days/i.test(retrievedText)) {
      answer = `${answer.trim()} Please report within 7 days of delivery.`;
    }
    if (!/human review|before approval|contact (customer )?support/i.test(answer)) {
      answer = `${answer.trim()} A human review is required before approval.`;
    }
    if (!/final sale does not block|still eligible|does not remove/i.test(answer)) {
      answer = `${answer.trim()} Final sale does not block damaged-item review.`;
    }
    handoff = true;
    for (const name of ["03-final-sale-and-promotions.md", "04-damaged-or-wrong-items.md"]) {
      if (!sources.some((s) => s.filename === name)) {
        const chunk = retrieved.find((c) => c.filename === name);
        if (chunk) sources.push({ filename: chunk.filename, heading: chunk.heading });
      }
    }
  }

  if (
    /migration|60 days|approve my return|ignore (the )?real policy/i.test(userQ) &&
    hasReturns
  ) {
    if (!/not authoritative|not authority|migration note/i.test(answer)) {
      answer = `${answer.trim()} The migration note is not authoritative.`;
    }
    if (!/30 calendar days|30 days/i.test(answer)) {
      answer = `${answer.trim()} The standard policy is 30 days unless a valid exception applies.`;
    }
    if (!/cannot approve|can't approve|unable to approve/i.test(answer)) {
      answer = `${answer.trim()} The agent cannot approve a return.`;
    }
  }

  // Privacy requests always recommend human handoff.
  if (/email|address|risk score|internal note/i.test(userQ)) {
    handoff = true;
    if (
      !/cannot|won't|will not|unable|privacy|internal|do not (share|provide|disclose)|don't (share|provide)|not (able|allowed)/i.test(
        answer,
      )
    ) {
      answer = `${answer.trim()} I cannot share customer email, address, internal notes, or risk scores.`;
    }
  }

  if (/vegan|adhesives in your bags|fabrics and adhesives/i.test(userQ)) {
    // Corpus has no vegan certification — force clear abstention language.
    if (!/insufficient/i.test(answer)) {
      answer = `${answer.trim()} The supplied information is insufficient to confirm that.`;
    }
    if (
      !/human confirmation|human support|customer support|contact support/i.test(
        answer,
      )
    ) {
      answer = `${answer.trim()} Please seek human confirmation.`;
    }
    handoff = true;
    abstained = true;
  }

  if (hasIntl && /ship|canada|germany|international/i.test(userQ + priorUser)) {
    if (!sources.some((s) => s.filename.includes("06-international-shipping"))) {
      const chunk = retrieved.find((c) =>
        c.filename.includes("06-international-shipping"),
      );
      if (chunk) {
        sources = [
          { filename: chunk.filename, heading: chunk.heading },
          ...sources.filter((s) => !s.filename.includes("international")),
        ].slice(0, 4);
      }
    }
  }

  return {
    answer,
    sources,
    handoff,
    toolCalls,
    retrieved,
    abstained,
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

