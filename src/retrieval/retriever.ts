import type { Chunk, RetrievedChunk } from "../types.js";
import { chunkDocuments } from "../ingest/chunk.js";
import { loadKnowledgeBase } from "../ingest/parseDocuments.js";
import { BM25Index, tokenize } from "./bm25.js";
import { metadataWeight } from "./rank.js";
import { config } from "../config.js";

function headingBoost(query: string, chunk: Chunk): number {
  const q = new Set(tokenize(query));
  const headingTokens = tokenize(`${chunk.heading} ${chunk.title}`);
  if (headingTokens.length === 0 || q.size === 0) return 1;

  let overlap = 0;
  for (const t of headingTokens) {
    if (q.has(t)) overlap += 1;
  }
  // Prefer chunks whose heading shares query terms (e.g. "return window").
  return 1 + Math.min(1.5, overlap * 0.45);
}

/**
 * Diversify by filename so multi-source questions (conflict, damaged+final-sale)
 * get more than one document in the top-k window.
 */
function diversify(
  scored: RetrievedChunk[],
  topK: number,
): RetrievedChunk[] {
  const selected: RetrievedChunk[] = [];
  const seenFiles = new Map<string, number>();
  const pool = [...scored];

  while (selected.length < topK && pool.length > 0) {
    let bestIdx = 0;
    let bestScore = -Infinity;
    for (let i = 0; i < pool.length; i++) {
      const c = pool[i]!;
      const fileCount = seenFiles.get(c.filename) ?? 0;
      // Soft penalty for repeating the same file too often.
      const diversityPenalty = fileCount === 0 ? 1 : fileCount === 1 ? 0.85 : 0.55;
      const adjusted = c.finalScore * diversityPenalty;
      if (adjusted > bestScore) {
        bestScore = adjusted;
        bestIdx = i;
      }
    }
    const chosen = pool.splice(bestIdx, 1)[0]!;
    selected.push(chosen);
    seenFiles.set(chosen.filename, (seenFiles.get(chosen.filename) ?? 0) + 1);
  }

  return selected;
}

export class Retriever {
  private readonly chunks: Chunk[];
  private readonly bm25: BM25Index;

  constructor(chunks?: Chunk[]) {
    this.chunks = chunks ?? chunkDocuments(loadKnowledgeBase());
    this.bm25 = new BM25Index(
      this.chunks.map(
        (c) =>
          `${c.title} ${c.heading} ${c.heading} ${c.headingPath.join(" ")} ${c.text} ${c.filename}`,
      ),
    );
  }

  getChunks(): Chunk[] {
    return this.chunks;
  }

  retrieve(query: string, topK: number = config.retrievalTopK): RetrievedChunk[] {
    const ranked = this.bm25.rank(query);
    const scored: RetrievedChunk[] = ranked.map(({ index, score }) => {
      const chunk = this.chunks[index]!;
      const weight = metadataWeight(chunk.metadata);
      const boost = headingBoost(query, chunk);
      return {
        ...chunk,
        bm25Score: score,
        finalScore: score * weight * boost,
      };
    });

    const positive = scored
      .filter((c) => c.bm25Score > 0)
      .sort((a, b) => b.finalScore - a.finalScore);

    // Take a wider pool before diversity selection.
    const pool = positive.slice(0, Math.max(topK * 4, 20));
    return diversify(pool, topK);
  }
}

let singleton: Retriever | null = null;

export function getRetriever(): Retriever {
  if (!singleton) singleton = new Retriever();
  return singleton;
}
