"""Background document ingestion: load → chunk → embed → store.

One worker thread processes documents in order, so the GPU is never shared
between two uploads. Progress (0–100) and errors are written to the
`documents` table, and the Documents page polls them. Documents left
queued/processing when the app stopped are resumed on the next start.
"""
from __future__ import annotations

import hashlib
import queue
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask
from werkzeug.utils import secure_filename

from models import database as db
from rag.chunker import chunk_sections, embedding_text
from rag.embeddings import EmbeddingError, get_embedder
from rag.loaders import LoaderError, load, source_type_for
from rag.store import get_store

EXT_KEY = "convoai_ingest"


class IngestWorker:
    def __init__(self, app: Flask):
        self.app = app
        self.queue: queue.Queue[int] = queue.Queue()
        self._queued: set[int] = set()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def enqueue(self, doc_id: int) -> None:
        if self.app.config.get("INGEST_SYNC"):  # tests: run inline
            process_document(self.app, doc_id)
            return
        with self._lock:
            if doc_id in self._queued:
                return
            self._queued.add(doc_id)
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="convoai-ingest", daemon=True)
                self._thread.start()
        self.queue.put(doc_id)

    def _run(self) -> None:
        while True:
            doc_id = self.queue.get()
            try:
                process_document(self.app, doc_id)
            finally:
                with self._lock:
                    self._queued.discard(doc_id)
                self.queue.task_done()

    @property
    def pending(self) -> int:
        return self.queue.qsize()


def init_app(app: Flask, resume: bool = True) -> None:
    worker = IngestWorker(app)
    app.extensions[EXT_KEY] = worker
    if resume:
        with app.app_context():
            for doc_id in db.pending_document_ids():
                db.update_document(doc_id, status="queued", progress=0)
                worker.enqueue(doc_id)


def enqueue(app: Flask, doc_id: int) -> None:
    app.extensions[EXT_KEY].enqueue(doc_id)


def remove_document(app: Flask, row) -> None:
    """Delete a document everywhere: its chunks, its uploaded file (only inside data/uploads) and its row."""
    get_store(app).delete_document(row["id"])
    if row["source_type"] != "url":
        path = Path(row["path_or_url"])
        upload_dir = Path(app.config["UPLOAD_DIR"]).resolve()
        if path.resolve().parent == upload_dir:
            path.unlink(missing_ok=True)
    db.delete_document(row["id"])


def add_file(app: Flask, collection: dict, filename: str, data: bytes, user_id: int | None) -> tuple[int | None, str | None]:
    """Save an uploaded file to data/uploads and create its document row (status 'queued').
    Returns (doc_id, None) or (None, reason it was skipped). Must run in an app context."""
    source_type = source_type_for(filename)
    if source_type is None:
        return None, "Unsupported type (use PDF, DOCX, TXT or MD)."
    if not data:
        return None, "File is empty."
    digest = hashlib.sha256(data).hexdigest()
    dup = db.find_duplicate_document(collection["id"], file_hash=digest)
    if dup:
        return None, f"Already in {collection['name']} as “{dup['title']}”."

    upload_dir = Path(app.config["UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe = secure_filename(filename) or f"document.{source_type}"
    path = upload_dir / f"{uuid.uuid4().hex[:12]}_{safe}"
    path.write_bytes(data)
    title = Path(filename).stem.replace("_", " ").strip() or safe
    doc_id = db.create_document(collection["id"], title[:200], source_type, str(path), user_id,
                                size_bytes=len(data), file_hash=digest)
    return doc_id, None


def process_document(app: Flask, doc_id: int) -> None:
    with app.app_context():
        doc = db.get_document(doc_id)
        if doc is None:
            return
        started = time.perf_counter()
        try:
            db.update_document(doc_id, status="processing", progress=5, error=None)

            loaded = load(doc["source_type"], doc["path_or_url"])
            title = doc["title"]
            if doc["source_type"] == "url" and loaded.title:
                title = loaded.title[:200]
            db.update_document(doc_id, title=title, progress=15,
                               page_count=loaded.page_count, char_count=loaded.char_count)

            settings = db.get_settings()
            chunks = chunk_sections(loaded.sections, int(settings.get("chunk_size", 800)),
                                    int(settings.get("chunk_overlap", 150)))
            if not chunks:
                raise LoaderError("No text could be extracted from this document.")

            embedder = get_embedder(app)
            total = len(chunks)

            def on_progress(done: int) -> None:
                db.update_document(doc_id, progress=15 + int(80 * done / total))

            vectors = embedder.embed_documents([embedding_text(title, c) for c in chunks], progress=on_progress)
            get_store(app).add_document(doc_id, doc["collection_id"], title, doc["source_type"], chunks, vectors)

            db.update_document(doc_id, status="ready", progress=100, chunk_count=total, error=None,
                               embed_model=embedder.model,
                               processed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            app.logger.info("Indexed document %s (%s chunks) in %.1fs", doc_id, total, time.perf_counter() - started)
        except (LoaderError, EmbeddingError) as exc:
            db.update_document(doc_id, status="failed", progress=0, error=str(exc))
        except Exception as exc:  # unexpected: keep the worker alive and show the error
            app.logger.exception("Ingestion failed for document %s", doc_id)
            db.update_document(doc_id, status="failed", progress=0, error=f"Unexpected error: {exc}")
