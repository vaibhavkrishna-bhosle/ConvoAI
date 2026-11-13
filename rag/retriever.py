"""Hybrid retrieval: vector (meaning) + BM25 (keywords), fused with Reciprocal Rank Fusion.

RRF score(chunk) = Σ over result lists of 1 / (K + rank). It needs no score
normalisation, so a chunk ranked well by both searches rises to the top.
Whether anything relevant was found at all is judged on the best *vector*
similarity (cosine, comparable across queries); BM25 scores are not.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from rag.store import Hit, KeywordIndex, VectorStore

RRF_K = 60
CANDIDATES = 20


@dataclass
class Retrieval:
    query: str
    hits: list[Hit]                       # fused, best first, at most top_k
    best_vector: float                    # highest cosine similarity among vector hits
    relevant: bool                        # passed the relevance gate (see retrieve())
    threshold: float
    mode: str = "hybrid"
    timings_ms: dict = field(default_factory=dict)
    keyword_agrees: bool = False          # BM25's best chunk is among the top-3 vector chunks


def rrf_fuse(result_lists: list[list[Hit]], k: int = RRF_K) -> list[Hit]:
    scores: dict[str, float] = {}
    by_id: dict[str, Hit] = {}
    for hits in result_lists:
        for rank, hit in enumerate(hits, start=1):
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (k + rank)
            by_id.setdefault(hit.id, hit)
    fused = sorted(scores, key=scores.get, reverse=True)
    return [Hit(**{**by_id[i].__dict__, "score": round(scores[i], 5)}) for i in fused]


def _dedupe(hits: list[Hit]) -> list[Hit]:
    """Drop chunks whose text is (almost) identical to a higher-ranked one, e.g. the same policy in two documents."""
    seen, out = [], []
    for h in hits:
        sig = " ".join(h.text.lower().split())[:300]
        if any(sig == s for s in seen):
            continue
        seen.append(sig)
        out.append(h)
    return out


def expand_with_neighbors(store: VectorStore, hits: list[Hit], top_n: int = 2, max_total: int = 9) -> list[Hit]:
    """Add the chunk before and after each of the top `top_n` hits (same document).

    A fact is often split across neighbouring chunks or defined in the section next door
    (e.g. which cities count as "metro" sits beside the per-diem table). Neighbours are
    appended after the ranked hits, so the best matches keep the lowest source numbers.
    """
    have = {h.id for h in hits}
    wanted = []
    for h in hits[:top_n]:
        for idx in (h.chunk_index - 1, h.chunk_index + 1):
            cid = f"{h.doc_id}:{idx}"
            if idx >= 0 and cid not in have and cid not in wanted:
                wanted.append(cid)
    extra = [n for n in store.chunks_by_ids(wanted)]
    return (hits + extra)[:max(max_total, len(hits))]


def retrieve(store: VectorStore, query_vector: list[float] | None, query: str, collection_ids: list[int],
             top_k: int = 5, threshold: float = 0.5, mode: str = "hybrid", floor: float | None = None) -> Retrieval:
    """mode: 'hybrid' | 'vector' | 'keyword' (the last two exist for evaluation).

    Relevance gate: relevant when the best vector similarity ≥ `threshold`, or when it is in the
    grey zone [`floor`, `threshold`) AND the keyword search independently agrees (its best chunk is
    one of the top-3 vector chunks). Follow-up rewrites like "Can I carry forward the casual
    leaves?" score just under the threshold but find the right passage with both methods;
    off-topic questions rarely get that agreement (measured in Phase 9).
    """
    timings = {}
    t = time.perf_counter()
    vector_hits = store.search(query_vector, collection_ids, CANDIDATES) if query_vector is not None and mode != "keyword" else []
    timings["vector"] = round((time.perf_counter() - t) * 1000, 1)

    t = time.perf_counter()
    keyword_hits = KeywordIndex.for_collections(store, collection_ids).search(query, CANDIDATES) if mode != "vector" else []
    timings["keyword"] = round((time.perf_counter() - t) * 1000, 1)

    if mode == "vector":
        ranked = vector_hits
    elif mode == "keyword":
        ranked = keyword_hits
    else:
        ranked = rrf_fuse([vector_hits, keyword_hits])

    best_vector = max((h.score for h in vector_hits), default=0.0)
    agrees = bool(keyword_hits) and keyword_hits[0].id in {h.id for h in vector_hits[:3]}
    if mode == "keyword":
        relevant = bool(keyword_hits)
    else:
        relevant = best_vector >= threshold or (floor is not None and best_vector >= floor and agrees)
    return Retrieval(query=query, hits=_dedupe(ranked)[:top_k], best_vector=round(best_vector, 4),
                     relevant=relevant, threshold=threshold, mode=mode, timings_ms=timings, keyword_agrees=agrees)
