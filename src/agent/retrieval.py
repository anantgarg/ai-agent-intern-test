from __future__ import annotations

import re
from pathlib import Path

from .schemas import Passage


ROOT = Path(__file__).resolve().parents[2]
KB_DIR = ROOT / "knowledge-base"


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "have", "how", "i", "in", "is", "it", "me", "my", "of",
    "on", "or", "the", "to", "what", "when", "where", "with", "you", "your",
}


def _parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw
    _, rest = raw.split("---", 1)
    meta_raw, body = rest.split("---", 1)
    metadata: dict[str, str] = {}
    for line in meta_raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata, body.strip()


def load_passages(kb_dir: Path = KB_DIR) -> list[Passage]:
    passages: list[Passage] = []
    for path in sorted(kb_dir.glob("*.md")):
        metadata, body = _parse_front_matter(path.read_text(encoding="utf-8"))
        title = metadata.get("title", path.stem)
        current_heading = title
        chunk: list[str] = []

        def flush() -> None:
            if chunk:
                text = "\n".join(chunk).strip()
                if text:
                    passages.append(
                        Passage(
                            filename=path.name,
                            title=title,
                            heading=current_heading,
                            text=text,
                            metadata=metadata,
                        )
                    )

        for line in body.splitlines():
            if line.startswith("#"):
                flush()
                current_heading = line.lstrip("#").strip()
                chunk = []
            else:
                chunk.append(line)
        flush()
    return passages


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in STOPWORDS and len(token) > 1
    }


class Retriever:
    def __init__(self, passages: list[Passage] | None = None):
        self.passages = passages or load_passages()

    def search(self, query: str, limit: int = 5) -> list[Passage]:
        q = tokenize(query)
        scored: list[Passage] = []
        for passage in self.passages:
            haystack = f"{passage.title} {passage.heading} {passage.text}"
            tokens = tokenize(haystack)
            overlap = len(q & tokens)
            if overlap == 0:
                continue
            score = float(overlap)
            meta = passage.metadata
            if meta.get("status") == "active":
                score += 2.5
            if meta.get("policy_authority") == "official":
                score += 1.5
            if meta.get("status") in {"superseded", "draft"}:
                score -= 5.0
            if meta.get("audience") == "internal":
                score -= 2.0
            p = Passage(
                filename=passage.filename,
                title=passage.title,
                heading=passage.heading,
                text=passage.text,
                metadata=passage.metadata,
                score=score,
            )
            scored.append(p)
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:limit]

