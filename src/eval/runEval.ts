import { loadAllCases } from "./cases.js";
import { assertCase } from "./assert.js";
import { runTurn } from "../agent/runTurn.js";
import { getRetriever } from "../retrieval/retriever.js";
import type { EvalCaseResult, ToolCallRecord } from "../types.js";
import { SessionStore } from "../session/store.js";

function categoryBucket(category: string): string {
  const c = category.toLowerCase();
  if (c.includes("privacy")) return "privacy";
  if (c.includes("conversation") || c.includes("multi")) return "multi-turn";
  if (c.includes("tool")) return "tool-use";
  if (c.includes("prompt") || c.includes("security")) return "prompt-security";
  if (c.includes("abstain")) return "abstention";
  if (c.includes("conflict") || c.includes("source-conflict")) return "source-conflict";
  if (c.includes("ground")) return "groundedness";
  if (c.includes("retrieval") || c.includes("multi-source")) return "retrieval";
  return category;
}

async function runCaseFull(
  evalCase: ReturnType<typeof loadAllCases>[number],
): Promise<EvalCaseResult> {
  const session = new SessionStore();
  const sessionId = `eval-${evalCase.id}`;
  const retriever = getRetriever();
  const allToolCalls: ToolCallRecord[] = [];
  const conversationParts: string[] = [];
  let lastResult = null as Awaited<ReturnType<typeof runTurn>> | null;

  for (let i = 0; i < evalCase.messages.length; i++) {
    const history = session.get(sessionId);
    const result = await runTurn({
      userMessage: evalCase.messages[i]!.content,
      history,
      sessionId,
      retriever,
    });
    allToolCalls.push(...result.toolCalls);
    conversationParts.push(evalCase.messages[i]!.content, result.answer);
    session.append(sessionId, evalCase.messages[i]!.content, result.answer);
    lastResult = result;
  }

  if (!lastResult) {
    return {
      id: evalCase.id,
      category: evalCase.category,
      passed: false,
      failures: ["no messages"],
      answer: "",
      sources: [],
      handoff: false,
      toolCalls: [],
    };
  }

  const merged = {
    ...lastResult,
    toolCalls: allToolCalls,
  };

  const failures = assertCase(
    evalCase.expect,
    merged,
    conversationParts.join("\n"),
  );

  return {
    id: evalCase.id,
    category: evalCase.category,
    passed: failures.length === 0,
    failures,
    answer: lastResult.answer,
    sources: lastResult.sources,
    handoff: lastResult.handoff,
    toolCalls: allToolCalls,
  };
}

async function main(): Promise<void> {
  const cases = loadAllCases();
  console.log(`Running ${cases.length} evaluation cases...\n`);

  const results: EvalCaseResult[] = [];
  for (const c of cases) {
    process.stdout.write(`• ${c.id} (${c.category}) ... `);
    try {
      const result = await runCaseFull(c);
      results.push(result);
      console.log(result.passed ? "PASS" : "FAIL");
      if (!result.passed) {
        for (const f of result.failures) {
          console.log(`    - ${f}`);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.log("ERROR");
      console.log(`    - ${message}`);
      results.push({
        id: c.id,
        category: c.category,
        passed: false,
        failures: [message],
        answer: "",
        sources: [],
        handoff: false,
        toolCalls: [],
      });
    }
  }

  const byCategory = new Map<string, { pass: number; total: number }>();
  for (const r of results) {
    const bucket = categoryBucket(r.category);
    const entry = byCategory.get(bucket) ?? { pass: 0, total: 0 };
    entry.total += 1;
    if (r.passed) entry.pass += 1;
    byCategory.set(bucket, entry);
  }

  const passed = results.filter((r) => r.passed).length;
  console.log("\n=== Summary ===");
  console.log(`Overall: ${passed}/${results.length} passed`);
  console.log("By category:");
  for (const [cat, { pass, total }] of [...byCategory.entries()].sort()) {
    console.log(`  ${cat}: ${pass}/${total}`);
  }

  const failed = results.filter((r) => !r.passed);
  if (failed.length) {
    console.log("\nFailed cases:");
    for (const f of failed) {
      console.log(`  - ${f.id}: ${f.failures.join("; ")}`);
    }
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
