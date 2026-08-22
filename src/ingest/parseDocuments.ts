import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import type { DocumentFrontMatter, ParsedDocument } from "../types.js";
import { config } from "../config.js";

export function loadKnowledgeBase(
  dir: string = config.knowledgeBaseDir,
): ParsedDocument[] {
  const files = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .sort();

  return files.map((filename) => {
    const filepath = path.join(dir, filename);
    const raw = fs.readFileSync(filepath, "utf8");
    const parsed = matter(raw);
    return {
      filename,
      filepath,
      frontMatter: parsed.data as DocumentFrontMatter,
      body: parsed.content.trim(),
    };
  });
}
