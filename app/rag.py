from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math
import re
from collections import Counter


@dataclass
class Chunk:
    text: str
    filename: str
    heading: str
    metadata: dict[str, str] = field(default_factory=dict)
    score: float = 0.0


STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "is", "are",
    "do", "does", "can", "i", "my", "me", "it", "this", "that", "what", "how",
    "when", "where", "will", "be", "you", "your", "we", "our", "they", "their",
}


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    raw, body = match.groups()
    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, body


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", text.lower()) if t not in STOPWORDS]


def split_markdown(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    metadata, body = parse_front_matter(raw)
    lines = body.splitlines()
    heading = metadata.get("title", path.stem)
    buffer: list[str] = []
    chunks: list[Chunk] = []

    def flush() -> None:
        nonlocal buffer
        text = "\n".join(buffer).strip()
        if text:
            chunks.append(Chunk(text=text, filename=path.name, heading=heading, metadata=dict(metadata)))
        buffer = []

    for line in lines:
        if re.match(r"^#{1,3}\s+", line):
            flush()
            heading = re.sub(r"^#{1,3}\s+", "", line).strip()
        elif line.strip():
            buffer.append(line)
        elif buffer and buffer[-1] != "":
            buffer.append("")
    flush()
    return chunks


class Retriever:
    """Small local TF-IDF retriever with explicit authority-aware reranking.

    No external embedding service is needed, which makes indexing deterministic and
    keeps customer documents local. Metadata is never discarded.
    """

    def __init__(self, kb_dir: str | Path):
        self.kb_dir = Path(kb_dir)
        self.chunks: list[Chunk] = []
        for path in sorted(self.kb_dir.glob("*.md")):
            self.chunks.extend(split_markdown(path))
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []
        self._fit()

    def _fit(self) -> None:
        token_sets = [set(_tokens(c.text + " " + c.heading + " " + c.filename)) for c in self.chunks]
        n = max(1, len(token_sets))
        df = Counter(token for tokens in token_sets for token in tokens)
        self._idf = {token: math.log((n + 1) / (count + 1)) + 1.0 for token, count in df.items()}
        self._vectors = []
        for chunk in self.chunks:
            counts = Counter(_tokens(chunk.text + " " + chunk.heading + " " + chunk.filename))
            weighted = {t: counts[t] * self._idf.get(t, 1.0) for t in counts}
            norm = math.sqrt(sum(v * v for v in weighted.values())) or 1.0
            self._vectors.append({t: v / norm for t, v in weighted.items()})

    def _query_vector(self, query: str) -> dict[str, float]:
        counts = Counter(_tokens(query))
        weighted = {t: counts[t] * self._idf.get(t, 1.0) for t in counts}
        norm = math.sqrt(sum(v * v for v in weighted.values())) or 1.0
        return {t: v / norm for t, v in weighted.items()}

    @staticmethod
    def _authority_bonus(meta: dict[str, str]) -> float:
        status = meta.get("status", "active").lower()
        audience = meta.get("audience", "customer").lower()
        authority = meta.get("policy_authority", "none").lower()
        if status == "active" and audience == "customer" and authority == "official":
            return 0.12
        if status == "active" and authority == "official":
            return 0.05
        if status == "superseded":
            return -0.12
        if status in {"draft", "inactive"}:
            return -0.15
        if audience == "internal":
            return -0.10
        return 0.0

    def retrieve(self, query: str, k: int = 6) -> list[Chunk]:
        qv = self._query_vector(query)
        scored: list[Chunk] = []
        for chunk, vector in zip(self.chunks, self._vectors):
            lexical = sum(qv.get(token, 0.0) * value for token, value in vector.items())
            score = lexical + self._authority_bonus(chunk.metadata)
            scored.append(Chunk(chunk.text, chunk.filename, chunk.heading, dict(chunk.metadata), score))
        scored.sort(key=lambda c: c.score, reverse=True)
        return [c for c in scored[:k] if c.score > 0.02]

    @staticmethod
    def format_source(chunk: Chunk) -> str:
        return f"{chunk.filename} — {chunk.heading}"

    @classmethod
    def format_context(cls, chunks: list[Chunk]) -> str:
        blocks = []
        for i, chunk in enumerate(chunks, 1):
            blocks.append(
                f"[SOURCE {i}] {cls.format_source(chunk)}\n"
                f"metadata={chunk.metadata}\n"
                f"retrieval_score={chunk.score:.4f}\n"
                f"content:\n{chunk.text}"
            )
        return "\n\n".join(blocks)
