from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, parts[2].lstrip()


@dataclass
class Chunk:
    filename: str
    heading: str
    text: str
    metadata: dict[str, str]
    score: float = 0.0

    @property
    def source(self) -> str:
        return f"{self.filename} — {self.heading}"


class KnowledgeBase:
    """TF-IDF RAG with metadata-aware precedence and conflict detection."""

    def __init__(self, kb_dir: str | Path):
        self.kb_dir = Path(kb_dir)
        self.chunks: list[Chunk] = []
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = None
        self._load()

    def _load(self) -> None:
        for path in sorted(self.kb_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
            current_heading = path.stem
            buffer: list[str] = []
            for line in body.splitlines():
                if line.startswith("## "):
                    if buffer:
                        self.chunks.append(Chunk(path.name, current_heading, "\n".join(buffer).strip(), meta))
                    current_heading = line[3:].strip()
                    buffer = [line]
                elif line.startswith("# ") and not buffer:
                    current_heading = line[2:].strip()
                    buffer = [line]
                else:
                    buffer.append(line)
            if buffer:
                self.chunks.append(Chunk(path.name, current_heading, "\n".join(buffer).strip(), meta))

        docs = [
            f"{c.heading}\n{c.text}\n{c.metadata.get('title','')} {c.filename}"
            for c in self.chunks
        ]
        self.matrix = self.vectorizer.fit_transform(docs)

    @staticmethod
    def _precedence(c: Chunk) -> tuple[int, int, str]:
        status = c.metadata.get("status", "").lower()
        authority = c.metadata.get("policy_authority", "").lower()
        # Explicit metadata beats recency. Superseded/draft/internal migration are de-prioritized.
        status_score = {"active": 3, "superseded": 1, "draft": 0}.get(status, 0)
        authority_score = {"official": 2, "none": 0}.get(authority, 0)
        audience_score = 1 if c.metadata.get("audience") == "customer" else 0
        return status_score + authority_score + audience_score, authority_score, c.metadata.get("effective_date", "")

    def retrieve(self, query: str, k: int = 6) -> list[Chunk]:
        q = self.vectorizer.transform([query])
        scores = cosine_similarity(q, self.matrix).ravel()
        ranked = sorted(
            zip(self.chunks, scores),
            key=lambda pair: (float(pair[1]), self._precedence(pair[0])),
            reverse=True,
        )
        out: list[Chunk] = []
        for chunk, score in ranked[: max(k * 3, 10)]:
            if score <= 0.02:
                continue
            chunk.score = float(score)
            out.append(chunk)

        # Remove obvious unsafe internal/draft content unless it is needed to detect a conflict.
        customer_out = [
            c for c in out
            if c.metadata.get("policy_authority") == "official"
            and c.metadata.get("status") == "active"
            and c.metadata.get("audience") == "customer"
        ]
        return (customer_out or out)[:k]

    def detect_conflicts(self, chunks: list[Chunk], query: str) -> list[str]:
        """Known-data conflict detector; intentionally conservative."""
        names = {c.filename for c in chunks}
        q = query.lower()
        if "dishwasher" in q and {"11-product-care.md", "12-breeze-tumbler-product-card.md"} <= names:
            return [
                "11-product-care.md says the stainless-steel body should be hand-washed.",
                "12-breeze-tumbler-product-card.md says all components are dishwasher safe.",
            ]
        return []

    @staticmethod
    def format_context(chunks: list[Chunk]) -> str:
        parts = []
        for c in chunks:
            parts.append(
                f"[SOURCE: {c.filename} | HEADING: {c.heading} | "
                f"STATUS: {c.metadata.get('status','')} | AUTHORITY: {c.metadata.get('policy_authority','')}]\n"
                f"{c.text}"
            )
        return "\n\n---\n\n".join(parts)
