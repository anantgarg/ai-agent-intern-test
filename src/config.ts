import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const ROOT_DIR = path.resolve(__dirname, "..");

export const config = {
  openRouterApiKey: process.env.OPENROUTER_API_KEY ?? "",
  model: process.env.OPENROUTER_MODEL ?? "openai/gpt-4o-mini",
  openRouterBaseUrl:
    process.env.OPENROUTER_BASE_URL ?? "https://openrouter.ai/api/v1",
  openRouterReferer: process.env.OPENROUTER_HTTP_REFERER ?? "http://localhost",
  openRouterTitle:
    process.env.OPENROUTER_APP_TITLE ?? "Aster & Row Support Agent",
  debug: process.env.DEBUG === "1" || process.argv.includes("--debug"),
  maxHistoryTurns: Number(process.env.MAX_HISTORY_TURNS ?? 8),
  retrievalTopK: Number(process.env.RETRIEVAL_TOP_K ?? 6),
  knowledgeBaseDir: path.join(ROOT_DIR, "knowledge-base"),
  ordersPath: path.join(ROOT_DIR, "data", "orders.json"),
  visibleCasesPath: path.join(ROOT_DIR, "evaluation", "visible-cases.json"),
  customCasesPath: path.join(ROOT_DIR, "evaluation", "custom-cases.json"),
  tracesDir: path.join(ROOT_DIR, "traces"),
  maxToolRounds: 4,
};

export function requireApiKey(): string {
  if (
    !config.openRouterApiKey ||
    config.openRouterApiKey.includes("your-key")
  ) {
    throw new Error(
      "Missing OPENROUTER_API_KEY. Copy .env.example to .env and set your OpenRouter key.",
    );
  }
  return config.openRouterApiKey;
}
