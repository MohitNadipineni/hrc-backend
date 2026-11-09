import re

import numpy as np

from app.clients.embeddings import embed_texts
from app.core.config import settings
from app.repositories.chunks import keyword_search, vector_search

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "of", "to", "in", "on",
    "for", "and", "or", "what", "which", "who", "how", "when", "does", "do",
    "did", "our", "we", "us", "it", "its", "this", "that", "with", "by", "as",
    "at", "from", "under", "any", "there", "have", "has", "should", "can",
}


def _terms(question: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", question.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def _rrf(*ranked_lists: list[dict], k: int = 60) -> list[dict]:
    scores, rows = {}, {}
    for ranked in ranked_lists:
        for rank, row in enumerate(ranked, 1):
            cid = row["chunk_id"]
            scores[cid] = scores.get(cid, 0) + 1 / (k + rank)
            rows[cid] = {**rows.get(cid, {}), **row}
    ordered = sorted(scores, key=scores.get, reverse=True)
    return [{**rows[cid], "rrf": scores[cid]} for cid in ordered]


def _overlap(terms: list[str], text: str) -> float:
    if not terms:
        return 0.0
    text = text.lower()
    return sum(1 for t in terms if t in text) / len(terms)


def search(question: str, user_groups: list[str] | None = None, top_k: int = 5) -> list[dict]:
    groups = ["all"] + list(user_groups or [])
    terms = _terms(question)

    keyword_hits = keyword_search(" | ".join(terms), groups, settings.candidate_k) if terms else []
    question_vec = np.array(embed_texts([question])[0], dtype=np.float32)
    vector_hits = vector_search(question_vec, groups, settings.candidate_k)

    merged = _rrf(keyword_hits, vector_hits)

    kept = [r for r in merged
            if r.get("score") is not None
            or r.get("similarity", 0) >= settings.min_similarity]

    for r in kept:
        r["overlap"] = _overlap(terms, r["content"])
    kept.sort(key=lambda r: (r["overlap"], r["rrf"]), reverse=True)

    return kept[:top_k]