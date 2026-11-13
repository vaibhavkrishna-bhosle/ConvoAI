"""Document management API (admin only): upload, add URL, list, status, chunks, re-index, delete, test search."""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from models import database as db
from models.user import admin_required
from rag.loaders import LoaderError, validate_url
from services import ingest

bp = Blueprint("documents", __name__, url_prefix="/api/documents")

PUBLIC_FIELDS = ("id", "collection_id", "collection_name", "collection_icon", "collection_color", "title",
                 "source_type", "status", "progress", "chunk_count", "error", "page_count", "char_count",
                 "size_bytes", "uploaded_by_name", "uploaded_at", "processed_at", "embed_model")


def _doc_json(row) -> dict:
    data = {k: row[k] for k in PUBLIC_FIELDS}
    if row["source_type"] == "url":
        data["url"] = row["path_or_url"]
    return data


def _collection_or_400(raw):
    try:
        collection = db.get_collection(int(raw))
    except (TypeError, ValueError):
        collection = None
    return collection


def _app():
    return current_app._get_current_object()


@bp.get("")
@admin_required
def list_documents():
    collection_id = request.args.get("collection_id", type=int)
    docs = [_doc_json(r) for r in db.list_documents(collection_id)]
    return jsonify(documents=docs, busy=any(d["status"] in ("queued", "processing") for d in docs))


@bp.post("")
@admin_required
def upload():
    collection = _collection_or_400(request.form.get("collection_id"))
    if collection is None:
        return jsonify(error="Choose a collection."), 400
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        return jsonify(error="No files received."), 400

    created, skipped = [], []
    for f in files:
        doc_id, reason = ingest.add_file(_app(), collection, f.filename, f.read(), current_user.id)
        if doc_id is None:
            skipped.append({"file": f.filename, "reason": reason})
            continue
        ingest.enqueue(_app(), doc_id)
        created.append(_doc_json(db.get_document(doc_id)))

    status = 201 if created else 400
    return jsonify(created=created, skipped=skipped), status


@bp.post("/url")
@admin_required
def add_url():
    body = request.get_json(silent=True) or {}
    collection = _collection_or_400(body.get("collection_id"))
    if collection is None:
        return jsonify(error="Choose a collection."), 400
    try:
        url = validate_url(body.get("url") or "")
    except LoaderError as exc:
        return jsonify(error=str(exc)), 400
    if db.find_duplicate_document(collection["id"], url=url):
        return jsonify(error=f"That page is already in {collection['name']}."), 409
    doc_id = db.create_document(collection["id"], url[:200], "url", url, current_user.id)
    ingest.enqueue(_app(), doc_id)
    return jsonify(created=[_doc_json(db.get_document(doc_id))]), 201


def _get_or_404(doc_id: int):
    row = db.get_document(doc_id)
    if row is None:
        return None, (jsonify(error="Document not found."), 404)
    return row, None


@bp.get("/<int:doc_id>")
@admin_required
def get_document(doc_id):
    row, err = _get_or_404(doc_id)
    return err or jsonify(_doc_json(row))


@bp.get("/<int:doc_id>/chunks")
@admin_required
def chunks(doc_id):
    from rag.store import get_store

    row, err = _get_or_404(doc_id)
    if err:
        return err
    hits = get_store(_app()).document_chunks(doc_id)
    return jsonify(document=_doc_json(row), chunks=[
        {"id": h.id, "index": h.chunk_index, "page": h.page, "heading": h.heading,
         "text": h.text, "chars": len(h.text)} for h in hits])


@bp.post("/<int:doc_id>/reindex")
@admin_required
def reindex(doc_id):
    row, err = _get_or_404(doc_id)
    if err:
        return err
    if row["status"] in ("queued", "processing"):
        return jsonify(error="This document is already being processed."), 409
    db.update_document(doc_id, status="queued", progress=0, error=None)
    ingest.enqueue(_app(), doc_id)
    return jsonify(_doc_json(db.get_document(doc_id))), 202


@bp.delete("/<int:doc_id>")
@admin_required
def delete(doc_id):
    from rag.store import get_store

    row, err = _get_or_404(doc_id)
    if err:
        return err
    if row["status"] == "processing":
        return jsonify(error="Wait for processing to finish before deleting."), 409
    ingest.remove_document(_app(), row)
    return jsonify(deleted=doc_id)


@bp.patch("/<int:doc_id>")
@admin_required
def edit(doc_id):
    """Rename a document and/or move it to another collection (its chunks move with it)."""
    from rag.store import get_store

    row, err = _get_or_404(doc_id)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    changes = {}
    if "title" in body:
        title = (body.get("title") or "").strip()
        if not title:
            return jsonify(error="Title is required."), 400
        changes["title"] = title[:200]
    if "collection_id" in body:
        collection = _collection_or_400(body.get("collection_id"))
        if collection is None:
            return jsonify(error="Choose a collection."), 400
        if collection["id"] != row["collection_id"]:
            if row["status"] in ("queued", "processing"):
                return jsonify(error="Wait for processing to finish before moving."), 409
            changes["collection_id"] = collection["id"]
    if changes:
        db.update_document(doc_id, **changes)
        if "collection_id" in changes:
            get_store(_app()).update_document_collection(doc_id, changes["collection_id"])
        if "title" in changes and row["status"] == "ready":
            get_store(_app()).update_document_title(doc_id, changes["title"])
    return jsonify(_doc_json(db.get_document(doc_id)))


@bp.post("/reindex-all")
@admin_required
def reindex_all():
    """Re-index every document, e.g. after changing the embedding model or chunk size."""
    queued = 0
    for row in db.list_documents():
        if row["status"] in ("queued", "processing"):
            continue
        db.update_document(row["id"], status="queued", progress=0, error=None)
        ingest.enqueue(_app(), row["id"])
        queued += 1
    return jsonify(queued=queued), 202


@bp.get("/search")
@admin_required
def test_search():
    """Admin retrieval check: top vector and keyword (BM25) matches for a query."""
    from rag.embeddings import EmbeddingError, get_embedder
    from rag.store import KeywordIndex, get_store

    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify(error="q is required"), 400
    collection_id = request.args.get("collection_id", type=int)
    ids = [collection_id] if collection_id else [c["id"] for c in db.list_collections()]
    k = min(request.args.get("k", 5, type=int), 20)
    store = get_store(_app())

    def as_json(h):
        return {"id": h.id, "doc_id": h.doc_id, "title": h.title, "page": h.page, "heading": h.heading,
                "score": h.score, "text": h.text}

    try:
        vector_hits = store.search(get_embedder(_app()).embed_query(q), ids, k)
    except EmbeddingError as exc:
        return jsonify(error=str(exc)), 503
    keyword_hits = KeywordIndex.for_collections(store, ids).search(q, k)
    return jsonify(query=q, vector=[as_json(h) for h in vector_hits], keyword=[as_json(h) for h in keyword_hits])
