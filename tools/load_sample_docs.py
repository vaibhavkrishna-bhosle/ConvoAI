"""Load the sample company documents into ConvoAI.

    .venv\\Scripts\\python tools/load_sample_docs.py

Every file in data/sample_docs/<Collection name>/ is added to that collection
and indexed right away (Ollama must be running). Files already loaded are skipped.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    from app import create_app
    from models import database as db
    from services.ingest import add_file, process_document

    app = create_app(background=False)
    with app.app_context():
        admin = db.get_db().execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
        collections = {c["name"].lower(): dict(c) for c in db.list_collections()}
        for folder in sorted((ROOT / "data" / "sample_docs").iterdir()):
            if not folder.is_dir():
                continue
            collection = collections.get(folder.name.lower())
            if collection is None:
                print(f"! No collection named '{folder.name}', skipping folder")
                continue
            for path in sorted(folder.iterdir()):
                doc_id, reason = add_file(app, collection, path.name, path.read_bytes(), admin["id"] if admin else None)
                if doc_id is None:
                    print(f"  skip  {folder.name}/{path.name}: {reason}")
                    continue
                start = time.perf_counter()
                process_document(app, doc_id)
                doc = db.get_document(doc_id)
                if doc["status"] == "ready":
                    print(f"  ok    {folder.name}/{path.name}: {doc['chunk_count']} chunks in {time.perf_counter() - start:.1f}s")
                else:
                    print(f"  FAIL  {folder.name}/{path.name}: {doc['error']}")


if __name__ == "__main__":
    main()
