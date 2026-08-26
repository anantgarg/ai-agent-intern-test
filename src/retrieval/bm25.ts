/**
 * Minimal BM25 (Okapi BM25) over an in-memory corpus of text chunks.
 */

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, " ")
    .split(/\s+/)
    .filter((t) => t.length > 1);
}

export class BM25Index {
  private readonly docs: string[][];
  private readonly docFreq = new Map<string, number>();
  private readonly avgDl: number;
  private readonly k1: number;
  private readonly b: number;

  constructor(documents: string[], k1 = 1.5, b = 0.75) {
    this.k1 = k1;
    this.b = b;
    this.docs = documents.map(tokenize);
    const totalLen = this.docs.reduce((sum, d) => sum + d.length, 0);
    this.avgDl = this.docs.length ? totalLen / this.docs.length : 0;

    for (const doc of this.docs) {
      const unique = new Set(doc);
      for (const term of unique) {
        this.docFreq.set(term, (this.docFreq.get(term) ?? 0) + 1);
      }
    }
  }

  score(query: string, docIndex: number): number {
    const qTerms = tokenize(query);
    const doc = this.docs[docIndex] ?? [];
    const dl = doc.length || 1;
    const tfMap = new Map<string, number>();
    for (const t of doc) tfMap.set(t, (tfMap.get(t) ?? 0) + 1);

    let score = 0;
    const N = this.docs.length || 1;
    for (const term of qTerms) {
      const tf = tfMap.get(term) ?? 0;
      if (tf === 0) continue;
      const df = this.docFreq.get(term) ?? 0;
      const idf = Math.log(1 + (N - df + 0.5) / (df + 0.5));
      const denom =
        tf + this.k1 * (1 - this.b + (this.b * dl) / (this.avgDl || 1));
      score += idf * ((tf * (this.k1 + 1)) / denom);
    }
    return score;
  }

  rank(query: string): Array<{ index: number; score: number }> {
    return this.docs
      .map((_, index) => ({ index, score: this.score(query, index) }))
      .sort((a, b) => b.score - a.score);
  }
}
