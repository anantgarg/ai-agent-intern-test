import type { Chunk, DocumentFrontMatter, ParsedDocument } from "../types.js";
import { authorityScore } from "../retrieval/rank.js";

interface HeadingBlock {
  heading: string;
  headingPath: string[];
  text: string;
}

function splitByHeadings(body: string, fallbackTitle: string): HeadingBlock[] {
  const lines = body.split(/\r?\n/);
  const blocks: HeadingBlock[] = [];
  let currentHeading = fallbackTitle;
  let pathStack: Array<{ level: number; text: string }> = [];
  let buffer: string[] = [];

  const flush = () => {
    const text = buffer.join("\n").trim();
    if (!text && blocks.length > 0) return;
    const headingPath = pathStack.map((p) => p.text);
    blocks.push({
      heading: currentHeading,
      headingPath: headingPath.length ? headingPath : [currentHeading],
      text: text || `(See section: ${currentHeading})`,
    });
    buffer = [];
  };

  for (const line of lines) {
    const match = /^(#{1,3})\s+(.+)$/.exec(line);
    if (match) {
      flush();
      const level = match[1].length;
      const text = match[2].trim();
      pathStack = pathStack.filter((p) => p.level < level);
      pathStack.push({ level, text });
      currentHeading = text;
      continue;
    }
    buffer.push(line);
  }
  flush();

  return blocks.length > 0
    ? blocks
    : [{ heading: fallbackTitle, headingPath: [fallbackTitle], text: body }];
}

export function chunkDocuments(docs: ParsedDocument[]): Chunk[] {
  const chunks: Chunk[] = [];

  for (const doc of docs) {
    const title = doc.frontMatter.title ?? doc.filename;
    const blocks = splitByHeadings(doc.body, title);
    const meta = doc.frontMatter;

    blocks.forEach((block, index) => {
      chunks.push({
        id: `${doc.filename}#${index}`,
        filename: doc.filename,
        documentId: String(meta.document_id ?? doc.filename),
        title: String(title),
        heading: block.heading,
        headingPath: block.headingPath,
        text: block.text,
        metadata: meta,
        authorityScore: authorityScore(meta),
      });
    });
  }

  return chunks;
}

export function summarizeMetadata(meta: DocumentFrontMatter): string {
  return [
    `status=${meta.status ?? "unknown"}`,
    `authority=${meta.policy_authority ?? "unknown"}`,
    `audience=${meta.audience ?? "unknown"}`,
    meta.customer_answering === false ? "customer_answering=false" : null,
  ]
    .filter(Boolean)
    .join(", ");
}
