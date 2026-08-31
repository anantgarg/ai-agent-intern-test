from pathlib import Path
import frontmatter
import chromadb


KB_DIR = Path(__file__).resolve().parents[1] / "knowledge-base"


def get_priority(filename):
    if "internal" in filename:
        return 0
    if "legacy" in filename:
        return 1
    return 3


def build_index():
    client = chromadb.PersistentClient(path=".chroma")

    try:
        client.delete_collection("knowledge_base")
    except Exception:
        pass

    collection = client.create_collection("knowledge_base")

    documents = []
    ids = []
    metadatas = []

    for file_path in sorted(KB_DIR.glob("*.md")):
        post = frontmatter.load(file_path)
        content = post.content.strip()

        if not content:
            continue

        lines = content.splitlines()
        current_heading = "General"
        section_lines = []

        for line in lines:
            if line.startswith("## "):
                if section_lines:
                    section_text = "\n".join(section_lines).strip()

                    if section_text:
                        chunk_id = f"{file_path.name}::{current_heading}"

                        documents.append(section_text)
                        ids.append(chunk_id)

                        metadatas.append({
                            "filename": file_path.name,
                            "title": post.metadata.get(
                                "title",
                                file_path.stem
                            ),
                            "heading": current_heading,
                            "priority": get_priority(file_path.name),
                        })

                current_heading = line[3:].strip()
                section_lines = []
            else:
                section_lines.append(line)

        if section_lines:
            section_text = "\n".join(section_lines).strip()

            if section_text:
                chunk_id = f"{file_path.name}::{current_heading}"

                documents.append(section_text)
                ids.append(chunk_id)

                metadatas.append({
                    "filename": file_path.name,
                    "title": post.metadata.get(
                        "title",
                        file_path.stem
                    ),
                    "heading": current_heading,
                    "priority": get_priority(file_path.name),
                })

    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas,
    )

    return collection


def search(query: str, n_results: int = 5):
    collection = build_index()

    results = collection.query(
        query_texts=[query],
        n_results=10,
    )

    if not results["ids"] or not results["ids"][0]:
        return results

    combined = list(zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ))

    query_words = set(query.lower().split())

    # Important terms that should strongly influence retrieval.
    important_terms = {
        "international",
        "canada",
        "shipping",
        "delivery",
        "duties",
        "taxes",
        "return",
        "returns",
        "trailplus",
        "warranty",
        "dishwasher",
        "vegan",
        "damaged",
        "final-sale",
        "final",
        "sale",
    }

    def score(item):
        filename = item[2]["filename"].lower()
        heading = item[2]["heading"].lower()
        document = item[1].lower()

        keyword_matches = 0

        for word in query_words:
            word = word.strip(".,?!():;")
            if len(word) > 3 and word in document:
                keyword_matches += 1

        important_matches = sum(
            1
            for term in important_terms
            if term in query.lower() and (
                term in document
                or term in heading
                or term in filename
            )
        )

        # Prefer exact topic/section matches.
        heading_matches = sum(
            1
            for word in query_words
            if len(word) > 3 and word in heading
        )

        priority = item[2]["priority"]
        distance = item[3]

        return (
            keyword_matches * 5
            + important_matches * 8
            + heading_matches * 6
            + priority * 2
            - distance
        )

    combined.sort(key=score, reverse=True)
    combined = combined[:n_results]

    results["ids"][0] = [item[0] for item in combined]
    results["documents"][0] = [item[1] for item in combined]
    results["metadatas"][0] = [item[2] for item in combined]
    results["distances"][0] = [item[3] for item in combined]

    return results