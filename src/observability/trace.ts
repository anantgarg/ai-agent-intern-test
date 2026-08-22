import fs from "node:fs";
import path from "node:path";
import chalk from "chalk";
import { config } from "../config.js";
import type { TraceEvent } from "../types.js";

export function ensureTracesDir(): string {
  if (!fs.existsSync(config.tracesDir)) {
    fs.mkdirSync(config.tracesDir, { recursive: true });
  }
  return config.tracesDir;
}

export function writeTrace(event: TraceEvent): string | null {
  if (!config.debug) return null;
  ensureTracesDir();
  const file = path.join(
    config.tracesDir,
    `${event.sessionId}-${Date.now()}.jsonl`,
  );
  fs.appendFileSync(file, `${JSON.stringify(event)}\n`, "utf8");
  return file;
}

export function buildTraceEvent(
  partial: Omit<TraceEvent, "timestamp">,
): TraceEvent {
  return {
    timestamp: new Date().toISOString(),
    ...partial,
  };
}

export function printDebugSummary(event: TraceEvent): void {
  if (!config.debug) return;
  console.error(chalk.magenta("\n── DEBUG TRACE ──"));
  console.error(chalk.dim("user: ") + event.userMessage);
  console.error(chalk.dim(`retrieved (${event.retrieved.length}):`));
  for (const r of event.retrieved) {
    console.error(
      chalk.dim("  · ") +
        chalk.cyan(`${r.filename}#${r.heading}`) +
        chalk.dim(
          `  score=${r.finalScore.toFixed(3)}  [${r.status}/${r.policy_authority}]`,
        ),
    );
  }
  if (event.toolCalls.length) {
    console.error(chalk.dim("tools:"));
    for (const t of event.toolCalls) {
      console.error(
        chalk.dim("  · ") +
          chalk.yellow(t.name) +
          chalk.dim(`(${JSON.stringify(t.arguments)})`),
      );
    }
  }
  console.error(
    chalk.dim("handoff=") +
      (event.handoff ? chalk.yellow("yes") : chalk.green("no")),
  );
  console.error(chalk.magenta("── END DEBUG ──\n"));
}
