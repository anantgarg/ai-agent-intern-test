"""
ingest.py

Loads all markdown files from knowledge-base/, extracts front-matter
metadata, chunks content by heading, and stores embeddings in ChromaDB.

Usage:
    python src/ingest.py
"""

import os
import re
import chromadb

KB_FOLDER = "knowledge-base"
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "aster_row_kb"


def parse_frontmatter(raw_text):
    """Extract YAML front-matter (between --- markers) and return (metadata, body)."""
    frontmatter = {}
    content = raw_text

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", raw_text, re.DOTALL)
    if match:
        yaml_block = match.group(1)
        content = match.group(2)

        for line in yaml_block.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()

    return frontmatter, content


def chunk_by_heading(content, filename):
    """Split document content into chunks at each '##' heading."""
    chunks = []
    sections = re.split(r"\n(?=## )", content)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n", 1)
        if lines[0].startswith("##"):
            heading = lines[0].replace("#", "").strip()
            body = lines[1].strip() if len(lines) > 1 else ""
        else:
            heading = "Introduction"
            body = section

        if body:
            chunks.append({"heading": heading, "text": body})

    return chunks


def load_knowledge_base():
    """Read every .md file in KB_FOLDER and return a list of chunk dicts with metadata."""
    all_chunks = []

    files = sorted(os.listdir(KB_FOLDER))
    for filename in files:
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(KB_FOLDER, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()

        frontmatter, content = parse_frontmatter(raw_text)
        chunks = chunk_by_heading(content, filename)

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"{filename}::{i}",
                "text": chunk["text"],
                "metadata": {
                    "filename": filename,
                    "heading": chunk["heading"],
                    "document_id": frontmatter.get("document_id", "unknown"),
                    "status": frontmatter.get("status", "unknown"),
                    "policy_authority": frontmatter.get("policy_authority", "unknown"),
                    "customer_answering": frontmatter.get("customer_answering", "true"),
                }
            })

        print(f"  {filename}: {len(chunks)} chunks extracted (status={frontmatter.get('status')})")

    return all_chunks


def build_index(chunks):
    """Embed and store all chunks in a persistent ChromaDB collection."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        client.delete_collection(COLLECTION_NAME)
        print("Found an existing collection, deleting it to rebuild fresh...")
    except Exception:
        pass

    collection = client.create_collection(name=COLLECTION_NAME)

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )

    print(f"\nStored {len(chunks)} chunks in ChromaDB at: {CHROMA_PATH}/")


if __name__ == "__main__":
    print("Loading knowledge base...\n")
    chunks = load_knowledge_base()
    print(f"\nFound {len(chunks)} chunks total. Building index...")
    build_index(chunks)
    print("\nDone! Next: build retriever.py to query this index.")