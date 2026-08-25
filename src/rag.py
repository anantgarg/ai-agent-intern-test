from pathlib import Path
import re
from typing import List, Dict, Any
import chromadb

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge-base"
CHROMA_PATH = Path(__file__).resolve().parent.parent / "chroma_db"

def parse_frontmatter(content: str) -> tuple[Dict[str, str], str]:
    metadata = {}
    body = content
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if match:
        raw_meta, body = match.groups()
        for line in raw_meta.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip()] = v.strip().strip('"').strip("'")
    return metadata, body

def get_or_build_vectorstore():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(name="kb_docs")
    
    if collection.count() == 0 and KB_DIR.exists():
        documents = []
        metadatas = []
        ids = []
        
        for file_path in sorted(KB_DIR.glob("*.md")):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            meta, body = parse_frontmatter(content)
            sections = re.split(r"\n(?=#{1,3}\s)", body)
            
            for idx, section in enumerate(sections):
                cleaned = section.strip()
                if not cleaned:
                    continue
                
                heading_match = re.search(r"^#{1,3}\s+(.+)$", cleaned, re.MULTILINE)
                heading = heading_match.group(1).strip() if heading_match else meta.get("title", file_path.name)
                
                doc_meta = {
                    "source_file": file_path.name,
                    "heading": heading,
                    "status": meta.get("status", "active"),
                    "category": meta.get("category", "general"),
                }
                
                documents.append(cleaned)
                metadatas.append(doc_meta)
                ids.append(f"{file_path.stem}_chunk_{idx}")
                
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
    
    return collection

def retrieve_relevant_docs(query: str, n_results: int = 4) -> List[Dict[str, Any]]:
    collection = get_or_build_vectorstore()
    
    # Return empty list if collection has no docs indexed yet
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query], 
        n_results=min(n_results, collection.count()),
        where={"status": "active"}
    )
    
    passages = []
    if results and "documents" in results and results["documents"]:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            passages.append({
                "content": doc,
                "source": f"{meta.get('source_file')} > {meta.get('heading')}",
                "file": meta.get("source_file"),
                "heading": meta.get("heading")
            })
    return passages