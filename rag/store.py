"""Chunk storage: ChromaDB for vectors, BM25 (rank_bm25) for keywords.

All chunks live in one Chroma collection per embedding model, so changing the
embedding model in Settings starts a fresh index (vectors from different models
aren't comparable). Department access is enforced with a `collection_id`
metadata filter on every query.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi

from nlp.preprocess import preprocess_tokens

_clients: dict[str, chromadb.ClientAPI] = {}
_lock = threading.RLock()


@dataclass
class Hit:
    id: str
    text: str
    score: float
    doc_id: int
    collection_id: int
    title: str
    page: int | None
    heading: str | None
    chunk_index: int
    extra: dict = field(default_factory=dict)


def _client(path: Path) -> chromadb.ClientAPI:
    key = str(path)
    with _lock:
        if key not in _clients:
            path.mkdir(parents=True, exist_ok=True)
            _clients[key] = chromadb.PersistentClient(path=key, settings=ChromaSettings(anonymized_telemetry=False))
        return _clients[key]


def collection_name(model: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_").lower() or "default"
    return f"chunks_{slug}"[:60]


def _hit(cid: str, text: str, meta: dict, score: float) -> Hit:
    return Hit(
        id=cid, text=text, score=round(float(score), 4),
        doc_id=int(meta["doc_id"]), collection_id=int(meta["collection_id"]),
        title=meta.get("title", ""), page=(meta.get("page") if meta.get("page", -1) >= 0 else None),
        heading=(meta.get("heading") or None), chunk_index=int(meta.get("chunk_index", 0)),
    )


class VectorStore:
    def __init__(self, path: Path, model: str):
        self.model = model
        self.collection = _client(Path(path)).get_or_create_collection(
            collection_name(model),
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"embed_model": model},
            embedding_function=None,
        )

    # ------------------------------------------------------------------ writes
    def add_document(self, doc_id: int, collection_id: int, title: str, source_type: str,
                     chunks, embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        with _lock:
            self.delete_document(doc_id)
            batch = 500
            for start in range(0, len(chunks), batch):
                part = chunks[start:start + batch]
                self.collection.add(
                    ids=[f"{doc_id}:{c.index}" for c in part],
                    embeddings=embeddings[start:start + batch],
                    documents=[c.text for c in part],
                    metadatas=[{
                        "doc_id": doc_id, "collection_id": collection_id, "title": title,
                        "source_type": source_type, "chunk_index": c.index,
                        "page": c.page if c.page is not None else -1, "heading": c.heading or "",
                    } for c in part],
                )
        KeywordIndex.invalidate()

    def delete_document(self, doc_id: int) -> None:
        with _lock:
            self.collection.delete(where={"doc_id": doc_id})
        KeywordIndex.invalidate()

    def _update_metadata(self, doc_id: int, **changes) -> None:
        with _lock:
            got = self.collection.get(where={"doc_id": doc_id}, include=["metadatas"])
            if got["ids"]:
                self.collection.update(ids=got["ids"], metadatas=[{**m, **changes} for m in got["metadatas"]])
        KeywordIndex.invalidate()

    def update_document_collection(self, doc_id: int, collection_id: int) -> None:
        """Moving a document only changes the filter metadata; vectors stay as they are."""
        self._update_metadata(doc_id, collection_id=collection_id)

    def update_document_title(self, doc_id: int, title: str) -> None:
        """Citations show the new name. (The title is also part of the embedded text, so a re-index
        refreshes retrieval too; citations are correct without one.)"""
        self._update_metadata(doc_id, title=title)

    # ------------------------------------------------------------------ reads
    def count(self) -> int:
        return self.collection.count()

    def document_chunks(self, doc_id: int) -> list[Hit]:
        got = self.collection.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
        hits = [_hit(i, d, m, 1.0) for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])]
        return sorted(hits, key=lambda h: h.chunk_index)

    def chunks_by_ids(self, ids: list[str]) -> list[Hit]:
        if not ids:
            return []
        got = self.collection.get(ids=list(ids), include=["documents", "metadatas"])
        by_id = {i: _hit(i, d, m, 0.0) for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])}
        return [by_id[i] for i in ids if i in by_id]

    def chunks_for_collections(self, collection_ids: list[int]) -> list[Hit]:
        if not collection_ids:
            return []
        got = self.collection.get(where={"collection_id": {"$in": list(collection_ids)}},
                                  include=["documents", "metadatas"])
        return [_hit(i, d, m, 0.0) for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])]

    def search(self, embedding: list[float], collection_ids: list[int], k: int = 20) -> list[Hit]:
        """Cosine similarity search restricted to the given collections (score = 1 − distance)."""
        if not collection_ids or self.count() == 0:
            return []
        res = self.collection.query(query_embeddings=[embedding], n_results=k,
                                    where={"collection_id": {"$in": list(collection_ids)}},
                                    include=["documents", "metadatas", "distances"])
        return [_hit(i, d, m, 1.0 - dist) for i, d, m, dist in
                zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])]


class KeywordIndex:
    """BM25 over the same chunks, built lazily per set of collections and cached until data changes."""

    _version = 0
    _cache: dict[tuple, tuple[int, "KeywordIndex"]] = {}

    def __init__(self, hits: list[Hit]):
        self.hits = hits
        corpus = [preprocess_tokens(f"{h.title} {h.heading or ''} {h.text}") for h in hits]
        self.bm25 = BM25Okapi(corpus) if corpus else None

    @classmethod
    def invalidate(cls) -> None:
        with _lock:
            cls._version += 1
            cls._cache.clear()

    @classmethod
    def for_collections(cls, store: VectorStore, collection_ids: list[int]) -> "KeywordIndex":
        key = (store.model, tuple(sorted(collection_ids)))
        with _lock:
            cached = cls._cache.get(key)
            if cached and cached[0] == cls._version:
                return cached[1]
            index = cls(store.chunks_for_collections(collection_ids))
            cls._cache[key] = (cls._version, index)
            return index

    def search(self, query: str, k: int = 20) -> list[Hit]:
        if not self.bm25:
            return []
        tokens = preprocess_tokens(query)
        scores = self.bm25.get_scores(tokens)
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        top = scores[order[0]] if order else 0
        out = []
        for i in order:
            if scores[i] <= 0:
                break
            h = self.hits[i]
            out.append(Hit(**{**h.__dict__, "score": round(float(scores[i] / top), 4) if top else 0.0}))
        return out


def get_store(app) -> VectorStore:
    from rag.embeddings import get_embedder

    return VectorStore(Path(app.config["CHROMA_DIR"]), get_embedder(app).model)
