#!/usr/bin/env node
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { randomUUID } from "node:crypto";
import chalk from "chalk";
import { config } from "./config.js";
import { formatCustomerResponse, runTurn } from "./agent/runTurn.js";
import { sessions } from "./session/store.js";
import {
  buildTraceEvent,
  printDebugSummary,
  writeTrace,
} from "./observability/trace.js";
import { getRetriever } from "./retrieval/retriever.js";

function printBanner(sessionId: string, chunkCount: number): void {
  console.log("");
  console.log(chalk.bold.green("  Aster & Row") + chalk.dim("  ·  Support Agent"));
  console.log(chalk.dim("  ─────────────────────────────────────"));
  console.log(
    chalk.dim("  session ") +
      chalk.cyan(sessionId) +
      chalk.dim("  ·  ") +
      chalk.dim(`${chunkCount} chunks`) +
      chalk.dim("  ·  ") +
      chalk.dim(config.model),
  );
  console.log(
    chalk.dim("  commands ") +
      chalk.white("/reset") +
      chalk.dim("  ") +
      chalk.white("/debug") +
      chalk.dim("  ") +
      chalk.white("/quit"),
  );
  console.log("");
}

async function main(): Promise<void> {
  const retriever = getRetriever();
  const chunkCount = retriever.getChunks().length;
  const sessionId = randomUUID().slice(0, 8);

  printBanner(sessionId, chunkCount);

  const rl = readline.createInterface({ input, output });

  while (true) {
    let line: string;
    try {
      line = (await rl.question(chalk.bold.cyan("You") + chalk.dim(": "))).trim();
    } catch {
      break;
    }

    if (!line) continue;
    if (line === "/quit" || line === "/exit") break;
    if (line === "/reset") {
      sessions.clear(sessionId);
      console.log(chalk.dim("  (session cleared)\n"));
      continue;
    }
    if (line === "/debug") {
      config.debug = !config.debug;
      console.log(
        chalk.dim("  (debug ") +
          (config.debug ? chalk.green("on") : chalk.yellow("off")) +
          chalk.dim(")\n"),
      );
      continue;
    }

    try {
      process.stdout.write(chalk.dim("  …thinking\n"));
      const history = sessions.get(sessionId);
      const result = await runTurn({
        userMessage: line,
        history,
        sessionId,
        retriever,
      });

      console.log("");
      console.log(chalk.bold.green("Agent") + chalk.dim(":"));
      console.log(formatCustomerResponse(result));
      console.log("");

      const trace = buildTraceEvent({
        sessionId,
        userMessage: line,
        history,
        retrieved: result.retrieved.map((c) => ({
          filename: c.filename,
          heading: c.heading,
          documentId: c.documentId,
          status: c.metadata.status as string | undefined,
          policy_authority: c.metadata.policy_authority as string | undefined,
          audience: c.metadata.audience as string | undefined,
          bm25Score: c.bm25Score,
          finalScore: c.finalScore,
          preview: c.text.slice(0, 180),
        })),
        toolCalls: result.toolCalls,
        finalResponse: result.answer,
        sources: result.sources,
        handoff: result.handoff,
      });
      printDebugSummary(trace);
      writeTrace(trace);

      sessions.append(sessionId, line, result.answer);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error("\n" + chalk.bold.red("Error") + chalk.dim(": ") + chalk.red(message) + "\n");
    }
  }

  rl.close();
  console.log(chalk.dim("\nGoodbye.\n"));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
