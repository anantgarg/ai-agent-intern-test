from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


KNOWLEDGE_BASE_DIR = (
    Path(__file__).resolve().parent.parent / "knowledge-base"
)


def parse_front_matter(text: str) -> tuple[dict, str]:
    """
    Extract YAML-like front matter from a Markdown document.

    Example:

    ---
    document_id: RET-2026-01
    title: Returns Policy
    status: active
    ---

    Returns policy content...
    """

    text = text.lstrip("\ufeff")

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)

    if len(parts) != 3:
        return {}, text

    metadata_text = parts[1].strip()
    content = parts[2].strip()

    metadata = {}

    for line in metadata_text.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip()
        value = value.strip()

        metadata[key] = value

    return metadata, content


def load_documents() -> list[dict]:
    """
    Load all Markdown files from the knowledge base.
    """

    documents = []

    for file_path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        text = file_path.read_text(encoding="utf-8")

        metadata, content = parse_front_matter(text)

        documents.append(
            {
                "filename": file_path.name,
                "metadata": metadata,
                "content": content,
            }
        )

    return documents


def split_into_chunks(document: dict) -> list[dict]:
    """
    Split a Markdown document into sections based on headings.

    Each chunk keeps:
    - filename
    - heading
    - metadata
    - text
    """

    content = document["content"]

    lines = content.splitlines()

    chunks = []
    current_heading = "Document"
    current_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#"):
            if current_lines:
                text = "\n".join(current_lines).strip()

                if text:
                    chunks.append(
                        {
                            "filename": document["filename"],
                            "heading": current_heading,
                            "metadata": document["metadata"].copy(),
                            "text": text,
                        }
                    )

            current_heading = stripped.lstrip("#").strip()
            current_lines = []

        else:
            current_lines.append(line)

    # Add the final section.
    if current_lines:
        text = "\n".join(current_lines).strip()

        if text:
            chunks.append(
                {
                    "filename": document["filename"],
                    "heading": current_heading,
                    "metadata": document["metadata"].copy(),
                    "text": text,
                }
            )

    return chunks

 


import re


def stemming_analyzer(doc: str) -> list[str]:
    words = re.findall(r"\b\w+\b", doc.lower())
    stop_words = {
        "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
        "which", "this", "that", "these", "those", "then", "just", "so", "than",
        "such", "both", "through", "about", "for", "is", "of", "to", "in", "i",
        "you", "he", "she", "it", "we", "they", "my", "your", "his", "her", "its",
        "our", "their", "do", "does", "did", "can", "could", "would", "should",
        "have", "has", "had", "be", "been", "being", "are", "was", "were"
    }
    stemmed = []
    for w in words:
        if w in stop_words:
            continue
        if len(w) > 3:
            w = re.sub(r"(ing|s|ed|es|ies)$", "", w)
        stemmed.append(w)
    return stemmed


def build_search_index() -> tuple[TfidfVectorizer, list[dict], object]:
    """
    Build a TF-IDF search index from all knowledge-base chunks.
    """

    documents = load_documents()

    all_chunks = []

    for document in documents:
        chunks = split_into_chunks(document)
        all_chunks.extend(chunks)

    texts = [chunk["text"] for chunk in all_chunks]

    vectorizer = TfidfVectorizer(
        analyzer=stemming_analyzer,
    )

    matrix = vectorizer.fit_transform(texts)

    return vectorizer, all_chunks, matrix


def search_knowledge_base(
    query: str,
    vectorizer: TfidfVectorizer,
    chunks: list[dict],
    matrix,
    top_k: int = 5,
) -> list[dict]:
    """
    Search the knowledge base and return the most relevant chunks.
    """

    query_vector = vectorizer.transform([query])

    scores = cosine_similarity(
        query_vector,
        matrix,
    )[0]

    ranked_indexes = scores.argsort()[::-1]

    results = []

    for index in ranked_indexes[:top_k]:
        chunk = chunks[index].copy()

        chunk["score"] = float(scores[index])

        results.append(chunk)

    return results

def authority_score(chunk: dict) -> float:
    """
    Give higher scores to authoritative, active customer-facing content.
    """

    metadata = chunk.get("metadata", {})

    score = 0.0

    status = metadata.get("status", "").lower()
    authority = metadata.get("policy_authority", "").lower()
    audience = metadata.get("audience", "").lower()

    if status == "active":
        score += 3.0
    elif status == "superseded":
        score -= 3.0
    elif status == "draft":
        score -= 2.0

    if authority == "official":
        score += 2.0
    elif authority == "internal":
        score -= 2.0

    if audience == "customer":
        score += 1.0

    return score


def rank_results(results: list[dict]) -> list[dict]:
    """
    Combine semantic relevance with document authority.
    """

    for result in results:
        result["authority_score"] = authority_score(result)

        result["final_score"] = (
            result["score"] + result["authority_score"]
        )

    return sorted(
        results,
        key=lambda result: result["final_score"],
        reverse=True,
    )

def detect_conflict(results: list[dict]) -> bool:
    """
    Detect genuine conflicts between current authoritative sources.

    Multiple active official sources are not automatically conflicting.
    Conflicts are detected only when different authoritative sources contain
    contradictory claims.
    """

    authoritative_results = []

    for result in results:
        metadata = result.get("metadata", {})

        status = metadata.get("status", "").lower()
        authority = metadata.get(
            "policy_authority",
            "",
        ).lower()

        if (
            status == "active"
            and authority == "official"
        ):
            authoritative_results.append(result)

    if len(authoritative_results) < 2:
        return False

    # Conflicts require at least two distinct active official files
    filenames = {
        result.get("filename")
        for result in authoritative_results
        if result.get("filename")
    }

    if len(filenames) < 2:
        return False

    import re

    # ---------------------------------------------------------
    # 1. Return-window conflicts
    # ---------------------------------------------------------

    return_windows = []

    for result in authoritative_results:
        text = result.get("text", "").lower()
        matches = re.findall(
            r"return window is\s+(\d+)\s+days",
            text,
        )

        for match in matches:
            return_windows.append(int(match))

    if len(set(return_windows)) > 1:
        return True

    # ---------------------------------------------------------
    # 2. Dishwasher-care conflicts
    # ---------------------------------------------------------

    has_dishwasher_claim = any(
        (
            "dishwasher safe" in result.get("text", "").lower()
            or "dishwasher-safe" in result.get("text", "").lower()
        )
        and "not dishwasher safe" not in result.get("text", "").lower()
        for result in authoritative_results
    )

    has_handwash_claim = any(
        "hand-wash" in result.get("text", "").lower()
        or "hand wash" in result.get("text", "").lower()
        or "not dishwasher safe" in result.get("text", "").lower()
        for result in authoritative_results
    )

    if has_dishwasher_claim and has_handwash_claim:
        return True

    return False