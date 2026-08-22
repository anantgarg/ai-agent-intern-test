import type { DocumentFrontMatter } from "../types.js";

/**
 * Higher = more authoritative for customer answers.
 * Superseded/draft/internal/non-official docs are heavily demoted but not deleted,
 * so conflict detection and prompt-injection tests can still see them ranked low.
 */
export function authorityScore(meta: DocumentFrontMatter): number {
  let score = 1;

  const status = String(meta.status ?? "").toLowerCase();
  if (status === "active") score += 3;
  else if (status === "superseded") score -= 4;
  else if (status === "draft") score -= 5;

  const authority = String(meta.policy_authority ?? "").toLowerCase();
  if (authority === "official") score += 2;
  else if (authority === "none") score -= 4;

  const audience = String(meta.audience ?? "").toLowerCase();
  if (audience === "customer") score += 1;
  else if (audience === "internal") score -= 3;

  if (meta.customer_answering === false) score -= 5;

  return score;
}

export function metadataWeight(meta: DocumentFrontMatter): number {
  // Map authority score into a positive multiplier for BM25.
  const raw = authorityScore(meta);
  return Math.max(0.05, 1 + raw * 0.35);
}

export function isAuthoritativeForCustomers(meta: DocumentFrontMatter): boolean {
  return (
    String(meta.status).toLowerCase() === "active" &&
    String(meta.policy_authority).toLowerCase() === "official" &&
    meta.customer_answering !== false &&
    String(meta.audience).toLowerCase() !== "internal"
  );
}
