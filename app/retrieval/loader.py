from pathlib import Path
import re
from dataclasses import dataclass

@dataclass
class Document:
    filename: str
    heading: str
    text: str
    metadata: dict


def parse_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}, text
    meta = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, parts[2].lstrip()


def split_markdown(path: Path) -> list[Document]:
    raw = path.read_text(encoding="utf-8")
    metadata, body = parse_front_matter(raw)
    headings = list(re.finditer(r"^(#{1,6})\s+(.+?)\s*$", body, re.MULTILINE))
    if not headings:
        return [Document(path.name, "Document", body.strip(), metadata)]
    sections = []
    for i, match in enumerate(headings):
        start = match.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        section = body[start:end].strip()
        if section:
            sections.append(Document(path.name, match.group(2).strip(), section, metadata.copy()))
    return sections


def load_documents(kb_dir: Path) -> list[Document]:
    docs = []
    for path in sorted(kb_dir.glob("*.md")):
        docs.extend(split_markdown(path))
    return docs
