"""Document parsing for Aster & Row knowledge base.

Splits Markdown files by headings, preserves front-matter metadata.
Does not modify source files; builds an in-memory derived index.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Chunk:
    chunk_id: str
    filename: str
    title: str
    heading: str
    text: str
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return f"{self.title}\n{self.heading}\n{self.text}".strip()


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    fm_raw, body = m.group(1), m.group(2)
    meta: dict = {}
    for line in fm_raw.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta, body


def split_markdown(filename: str, meta: dict, body: str) -> list[Chunk]:
    title = meta.get("title", filename)
    chunks: list[Chunk] = []
    current_heading = "(intro)"
    current_lines: list[str] = []
    h1_title = ""

    def flush():
        text = "\n".join(current_lines).strip()
        if text:
            cid = f"{filename}#{current_heading}"
            # make unique if repeated
            suffix = sum(1 for c in chunks if c.filename == filename and c.heading == current_heading)
            if suffix:
                cid = f"{cid}::{suffix+1}"
            chunks.append(Chunk(
                chunk_id=cid,
                filename=filename,
                title=title,
                heading=current_heading,
                text=text,
                metadata=dict(meta),
            ))

    for line in body.splitlines():
        hm = HEADING_RE.match(line.strip())
        if hm:
            level = len(hm.group(1))
            htext = hm.group(2).strip()
            if level == 1 and not h1_title:
                h1_title = htext
                # H1 becomes context, not a separate chunk break necessarily,
                # but start a new section.
                flush()
                current_lines = []
                current_heading = htext
                continue
            if level >= 2:
                flush()
                current_lines = []
                current_heading = htext
                continue
        current_lines.append(line)
    flush()
    # Drop empty chunks
    chunks = [c for c in chunks if c.text.strip()]
    return chunks


def load_knowledge_base(kb_dir: str | Path) -> list[Chunk]:
    kb = Path(kb_dir)
    if not kb.is_dir():
        raise FileNotFoundError(f"knowledge-base directory not found: {kb_dir}")
    all_chunks: list[Chunk] = []
    for md in sorted(kb.glob("*.md")):
        raw = md.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        chunks = split_markdown(md.name, meta, body)
        all_chunks.extend(chunks)
    if not all_chunks:
        raise FileNotFoundError(f"no Markdown documents found in: {kb_dir}")
    return all_chunks
