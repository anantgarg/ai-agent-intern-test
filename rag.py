import os
import re
from pathlib import Path
from typing import Any, Dict, List

# Define path to the mock knowledge base documents
KB_DIR = Path(__file__).parent / "knowledge-base"

# Basic stop words to filter out low-value semantic lexical matches
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
    "of", "with", "is", "are", "was", "were", "it", "this", "that", 
    "how", "what", "when", "where", "who", "why", "can", "do", "does", 
    "have", "has", "my", "your", "i", "am", "about", "you"
}


def tokenize(text: str) -> set:
    """Extracts alphanumeric words, converts to lowercase, and removes stop words."""
    words = re.findall(r'\b[a-z0-9]+\b', text.lower())
    return set(words) - STOP_WORDS


def load_and_chunk_documents() -> List[Dict[str, str]]:
    """Loads markdown files, strips front-matter, and chunks by headings."""
    chunks = []
    if not KB_DIR.exists():
        return chunks

    for filepath in KB_DIR.glob("*.md"):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Strip standard YAML front-matter if present
        content = re.sub(r"^---.*?---", "", content, flags=re.DOTALL | re.MULTILINE).strip()

        # Split content by markdown headings 
        parts = re.split(r"(^#+\s+.*$)", content, flags=re.MULTILINE)
        
        current_heading = "Overview"
        
        # Handle preamble text without a heading
        if parts and not parts[0].startswith("#"):
            text = parts.pop(0).strip()
            if text:
                chunks.append({
                    "filename": filepath.name,
                    "heading": current_heading,
                    "content": f"## {current_heading}\n\n{text}",
                    "citation": f"{filepath.name} # {current_heading}"
                })

        # Process heading-body pairs
        for i in range(0, len(parts), 2):
            heading_raw = parts[i]
            heading_clean = heading_raw.replace("#", "").strip()
            body_text = parts[i+1].strip() if i+1 < len(parts) else ""
            
            if body_text:
                chunks.append({
                    "filename": filepath.name,
                    "heading": heading_clean,
                    "content": f"{heading_raw}\n\n{body_text}",
                    "citation": f"{filepath.name} # {heading_clean}"
                })
                
    return chunks


# Pre-load chunks in memory to act as a mock local Document Store 
CHUNKS = load_and_chunk_documents()


def retrieve_passages(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant document chunks for a given query based on 
    keyword overlap, applying routing weights for Aster & Row business rules.
    """
    query_tokens = tokenize(query)
    query_lower = query.lower()
    
    if not query_tokens:
        return []

    scored_chunks = []

    for chunk in CHUNKS:
        chunk_text = f"{chunk['heading']} {chunk['content']}".lower()
        chunk_tokens = tokenize(chunk_text)
        
        # 1. Base Lexical Similarity Score (Token Intersection)
        overlap = query_tokens.intersection(chunk_tokens)
        score = len(overlap)

        # 2. Globally deprioritize legacy policies and internal migration notes
        if chunk["filename"] in ["02-returns-policy-legacy.md", "14-internal-content-migration-notes.md"]:
            score -= 5

        # 3. Business Logic Retrieval Routing Weights
        
        # Route generic return queries strictly to standard policy
        if "return" in query_tokens or "returned" in query_tokens:
            if "01-returns-policy-current.md" in chunk["filename"]:
                score += 5
            # Prevent TrailPlus policy from overwhelming generic return queries
            if "trailplus" not in query_lower and "09-trailplus-membership.md" in chunk["filename"]:
                score -= 10
                
        # Route TrailPlus explicitly
        if "trailplus" in query_lower and "09-trailplus-membership.md" in chunk["filename"]:
            score += 15
            
        # Route International & Country-specific shipping
        if any(w in query_lower for w in ["canada", "germany", "international", "ship to"]):
            if "06-international-shipping.md" in chunk["filename"]:
                score += 15
                
        # Route final sale exceptions and damage reviews
        if any(w in query_lower for w in ["damage", "broken", "zipper", "defective"]):
            if "04-damaged-or-wrong-items.md" in chunk["filename"]:
                score += 10
        if "final sale" in query_lower and "03-final-sale-and-promotions.md" in chunk["filename"]:
            score += 10
            
        # Route warranty specifics
        if "warranty" in query_tokens and "07-warranty.md" in chunk["filename"]:
            score += 10

        # Route product care and source conflicts
        if "dishwasher" in query_tokens or "wash" in query_tokens:
            if "11-product-care.md" in chunk["filename"] or "12-breeze-tumbler-product-card.md" in chunk["filename"]:
                score += 10

        if score > 0:
            scored_chunks.append((score, chunk))

    # Sort descending by score
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Return top K chunks
    top_chunks = [c[1] for c in scored_chunks[:top_k]]
    
    return top_chunks


def search_knowledge_base(query: str, top_k: int = 3) -> Dict[str, List[str]]:
    """
    Compatibility wrapper function expected by agent.py.
    Maps retrieve_passages output to a dictionary with 'passages' and 'sources'.
    """
    chunks = retrieve_passages(query, top_k=top_k)
    passages = [chunk["content"] for chunk in chunks]
    sources = [chunk["citation"] for chunk in chunks]
    return {
        "passages": passages,
        "sources": sources
    }