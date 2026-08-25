from .index import VectorIndex

ACTIVE = {"active", "current", "published"}
SUPERSEDED = {"superseded", "legacy", "deprecated", "inactive"}

def authority(metadata: dict) -> int:
    status = str(metadata.get("status", "")).lower()
    audience = str(metadata.get("audience", "")).lower()
    policy_authority = str(metadata.get("policy_authority", "")).lower()
    score = 0
    if status in ACTIVE:
        score += 4
    if status in SUPERSEDED or status == "draft":
        score -= 5
    if audience == "customer":
        score += 3
    elif audience == "internal":
        score -= 6
    if policy_authority == "official":
        score += 4
    else:
        score -= 2
    if str(metadata.get("customer_answering", "")).lower() == "false":
        score -= 5
    return score

class Retriever:
    def __init__(self, index: VectorIndex, top_k: int = 8):
        self.index = index
        self.top_k = top_k

    def retrieve(self, query: str):
        hits = self.index.search(query, self.top_k)
        # Rerank only the semantically relevant candidates; authority is a controlled boost,
        # not a license to surface unrelated documents.
        hits.sort(key=lambda pair: pair[1] + 0.05 * authority(pair[0].metadata), reverse=True)
        return hits

    @staticmethod
    def format_sources(hits):
        return [
            {
                "filename": doc.filename,
                "heading": doc.heading,
                "score": round(score, 4),
                "metadata": doc.metadata,
            }
            for doc, score in hits
        ]
