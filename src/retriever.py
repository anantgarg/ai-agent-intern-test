"""
retriever.py

Queries the ChromaDB index built by ingest.py and returns relevant chunks.
Applies precedence rules discovered from the knowledge-base front-matter:

  - Chunks with customer_answering = false (the migration scratchpad) are
    never treated as authoritative for answering. They are only surfaced
    when the retriever needs to explicitly flag that a document is not
    authoritative (e.g. prompt-injection test case).
  - Chunks with status = superseded are kept as background only, not as
    the primary source, when an active document on the same topic exists.
  - If two chunks with status = active and policy_authority = official
    disagree on the same topic, that is a genuine conflict and must be
    surfaced rather than silently resolved.

Usage (standalone test):
    python src/retriever.py
"""

import chromadb

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "aster_row_kb"
TOP_K = 5


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(COLLECTION_NAME)


def retrieve(query, top_k=TOP_K):
    """
    Runs a similarity search against the KB collection and returns a list
    of result dicts: {text, filename, heading, status, policy_authority,
    customer_answering, distance}.
    """
    collection = get_collection()

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    hits = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        hits.append({
            "text": doc,
            "filename": meta.get("filename"),
            "heading": meta.get("heading"),
            "status": meta.get("status"),
            "policy_authority": meta.get("policy_authority"),
            "customer_answering": meta.get("customer_answering"),
            "distance": dist,
        })

    return hits


def apply_precedence(hits):
    """
    Splits retrieved hits into three buckets so the agent layer can decide
    how to use them:

      - authoritative: status=active, policy_authority=official,
        customer_answering != "false". Safe to answer from directly.
      - background: status=superseded. Useful for context only, never
        cited as the answer unless nothing authoritative was found.
      - non_authoritative: customer_answering=false or
        policy_authority=none (e.g. the migration scratchpad). Never used
        to answer; only referenced to explicitly say "this is not
        authoritative" if the user brings it up.
    """
    authoritative = []
    background = []
    non_authoritative = []

    for hit in hits:
        if hit["customer_answering"] == "false" or hit["policy_authority"] == "none":
            non_authoritative.append(hit)
        elif hit["status"] == "superseded":
            background.append(hit)
        elif hit["status"] == "active" and hit["policy_authority"] == "official":
            authoritative.append(hit)
        else:
            background.append(hit)

    return {
        "authoritative": authoritative,
        "background": background,
        "non_authoritative": non_authoritative,
    }


def detect_conflict(authoritative_hits):
    """
    A simple heuristic: if two authoritative hits come from different
    source files, that's a signal for the agent layer to inspect whether
    they genuinely disagree on the same topic (real conflict) or are just
    complementary information. This function does not decide truth -- it
    only flags "more than one authoritative source responded".
    """
    distinct_files = set(hit["filename"] for hit in authoritative_hits)
    return len(distinct_files) > 1


if __name__ == "__main__":
    test_query = "Can I put the Breeze Tumbler in the dishwasher?"
    print(f"Query: {test_query}\n")

    hits = retrieve(test_query)
    buckets = apply_precedence(hits)

    print("Authoritative hits:")
    for h in buckets["authoritative"]:
        print(f"  [{h['filename']} | {h['heading']}] (distance={h['distance']:.3f})")

    print("\nBackground (superseded) hits:")
    for h in buckets["background"]:
        print(f"  [{h['filename']} | {h['heading']}]")

    print("\nNon-authoritative hits:")
    for h in buckets["non_authoritative"]:
        print(f"  [{h['filename']} | {h['heading']}]")

    print(f"\nMultiple authoritative sources involved: {detect_conflict(buckets['authoritative'])}")