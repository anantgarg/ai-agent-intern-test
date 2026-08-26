import OpenAI from "openai";
import { config, requireApiKey } from "../config.js";

let client: OpenAI | null = null;

export function getOpenRouterClient(): OpenAI {
  if (!client) {
    client = new OpenAI({
      apiKey: requireApiKey(),
      baseURL: config.openRouterBaseUrl,
      defaultHeaders: {
        "HTTP-Referer": config.openRouterReferer,
        "X-Title": config.openRouterTitle,
      },
    });
  }
  return client;
}

export function getModel(): string {
  return config.model;
}
