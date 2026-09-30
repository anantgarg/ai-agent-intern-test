"""Local TF-IDF retrieval with authority weighting.

Stdlib only. No external embeddings, no network calls.
Prefers active + official documents; down-ranks superseded / draft / non-authority.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .documents import Chunk

TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "with", "by", "as", "at", "from", "that", "this",
    "it", "its", "you", "your", "we", "our", "they", "their", "what", "how",
    "does", "do", "can", "i", "my", "me", "about", "have", "has", "will",
    "when", "where", "which", "who", "all", "any", "not", "no", "if", "so",
}


# Destination normalization shared by agent routing and retrieval recall.
# Alias (country or major city, matched on word boundaries) -> country name.
# Canada is intentionally absent: it is the one supported destination and is
# handled as its own answer path, not as an "unsupported destination".
DESTINATION_ALIASES = {
    "germany": "Germany", "german": "Germany",
    "berlin": "Germany", "munich": "Germany", "hamburg": "Germany",
    "frankfurt": "Germany",
    "france": "France", "paris": "France", "lyon": "France",
    "united kingdom": "United Kingdom", "london": "United Kingdom",
    "manchester": "United Kingdom",
    "uk": "United Kingdom",
    "ireland": "Ireland", "dublin": "Ireland",
    "spain": "Spain", "madrid": "Spain", "barcelona": "Spain",
    "italy": "Italy", "rome": "Italy", "milan": "Italy",
    "netherlands": "Netherlands", "amsterdam": "Netherlands",
    "holland": "Netherlands",
    "belgium": "Belgium", "brussels": "Belgium",
    "switzerland": "Switzerland", "zurich": "Switzerland",
    "austria": "Austria", "vienna": "Austria",
    "sweden": "Sweden", "stockholm": "Sweden",
    "norway": "Norway", "oslo": "Norway",
    "denmark": "Denmark", "copenhagen": "Denmark",
    "poland": "Poland", "warsaw": "Poland",
    "portugal": "Portugal", "lisbon": "Portugal",
    "greece": "Greece", "athens": "Greece",
    "australia": "Australia", "sydney": "Australia", "melbourne": "Australia",
    "new zealand": "New Zealand", "auckland": "New Zealand",
    "japan": "Japan", "tokyo": "Japan", "osaka": "Japan",
    "china": "China", "beijing": "China", "shanghai": "China",
    "india": "India", "mumbai": "India", "delhi": "India",
    "mexico": "Mexico", "brazil": "Brazil", "argentina": "Argentina",
    "chile": "Chile",
    "south africa": "South Africa", "egypt": "Egypt", "cairo": "Egypt",
    "united arab emirates": "United Arab Emirates",
    "uae": "United Arab Emirates", "dubai": "United Arab Emirates",
    "singapore": "Singapore", "south korea": "South Korea",
    "seoul": "South Korea", "thailand": "Thailand", "vietnam": "Vietnam",
}


def mentions_destination(query_lower: str) -> bool:
    """True when the (already lowercased) query names a known destination."""
    return any(re.search(r"\b" + re.escape(a) + r"\b", query_lower)
               for a in DESTINATION_ALIASES)


def tokenize(text: str) -> list[str]:
    toks = TOKEN_RE.findall(text.lower())
    return [t for t in toks if t not in STOPWORDS and len(t) > 1]


def authority_weight(chunk: Chunk) -> float:
    meta = chunk.metadata
    status = (meta.get("status", "") or "").lower()
    authority = (meta.get("policy_authority", "") or "").lower()
    audience = (meta.get("audience", "") or "").lower()
    fname = chunk.filename

    # Draft / non-authority scratchpad is never authoritative.
    if fname == "14-internal-content-migration-notes.md":
        return 0.12
    if authority == "none":
        return 0.15
    if status == "superseded":
        return 0.35
    if status == "draft":
        return 0.15
    if status == "active" and authority == "official" and audience == "customer":
        return 1.0
    if status == "active" and authority == "official" and audience == "internal":
        # e.g. support-escalation rules: useful for behavior, not customer citation
        return 0.6
    if status == "active":
        return 0.85
    return 0.5


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float
    cosine: float
    weight: float


class Retriever:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.N = len(chunks)
        self.doc_tokens: list[list[str]] = [tokenize(c.full_text) for c in chunks]
        self.doc_tf: list[Counter] = [Counter(t) for t in self.doc_tokens]
        df: Counter = Counter()
        for toks in self.doc_tokens:
            for t in set(toks):
                df[t] += 1
        self.df = df
        self.idf: dict[str, float] = {
            t: math.log((self.N + 1) / (freq + 1)) + 1.0 for t, freq in df.items()
        }
        # Precompute doc norms
        self.doc_vecs: list[dict[str, float]] = []
        self.doc_norms: list[float] = []
        for tf in self.doc_tf:
            total = sum(tf.values()) or 1
            vec = {t: (c / total) * self.idf.get(t, 1.0) for t, c in tf.items()}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self.doc_vecs.append(vec)
            self.doc_norms.append(norm)

    def score_query(self, query: str) -> list[ScoredChunk]:
        qtoks = tokenize(query)
        if not qtoks:
            qtoks = tokenize(query.lower())
        qtf = Counter(qtoks)
        total = sum(qtf.values()) or 1
        # Use corpus IDF; unseen terms get max IDF
        max_idf = math.log(self.N + 1) + 1.0
        qvec = {t: (c / total) * self.idf.get(t, max_idf) for t, c in qtf.items()}
        qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
        out: list[ScoredChunk] = []
        for i, chunk in enumerate(self.chunks):
            dvec = self.doc_vecs[i]
            dot = 0.0
            # iterate over smaller (query)
            for t, qv in qvec.items():
                dv = dvec.get(t)
                if dv:
                    dot += qv * dv
            cosine = dot / (qnorm * self.doc_norms[i]) if dot else 0.0
            # Small exact-title/filename boost is NOT applied here; authority only.
            w = authority_weight(chunk)
            out.append(ScoredChunk(chunk=chunk, score=cosine * w, cosine=cosine, weight=w))
        out.sort(key=lambda s: s.score, reverse=True)
        return out

    def retrieve(self, query: str, top_k: int = 4) -> list[ScoredChunk]:
        scored = self.score_query(query)
        top = scored[:top_k]
        # Ensure multi-source grounding for known conflict / multi-doc topics
        # without hardcoding answers: if query is about dishwasher/tumbler cleaning,
        # guarantee at least one chunk from each active official source on that topic.
        ql = query.lower()
        if any(k in ql for k in ("dishwash", "tumbler", "breeze", "clean", "wash")):
            have = {s.chunk.filename for s in top}
            needed = {"11-product-care.md", "12-breeze-tumbler-product-card.md"}
            for need in needed:
                if need not in have:
                    for s in scored:
                        if s.chunk.filename == need:
                            top = top + [s]
                            break
        if any(k in ql for k in ("final-sale", "final sale", "broken zipper", "damaged", "defect")) and \
           any(k in ql for k in ("final", "luck", "broken", "damag", "sale")):
            have = {s.chunk.filename for s in top}
            for need in ("03-final-sale-and-promotions.md", "04-damaged-or-wrong-items.md"):
                if need not in have:
                    for s in scored:
                        if s.chunk.filename == need:
                            top = top + [s]
                            break
        if mentions_destination(ql) or \
           any(k in ql for k in ("canada", "international",
                                 "duties", "duty", "customs")):
            if "06-international-shipping.md" not in {s.chunk.filename for s in top}:
                for s in scored:
                    if s.chunk.filename == "06-international-shipping.md":
                        top = top + [s]
                        break
        return top
