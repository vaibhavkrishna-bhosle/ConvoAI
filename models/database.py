"""SQLite access layer: connection handling, schema init, seeding and CRUD helpers."""
from __future__ import annotations

import json
import secrets
import sqlite3
from pathlib import Path

from flask import Flask, current_app, g
from werkzeug.security import generate_password_hash

SCHEMA_FILE = Path(__file__).with_name("schema.sql")

DEFAULT_COLLECTIONS = [
    ("General", "Company-wide information, policies and announcements", "domain", "#006A6A"),
    ("HR", "Leave, payroll, benefits, onboarding and HR policies", "groups", "#7A5900"),
    ("IT Support", "Accounts, devices, VPN, software and security", "computer", "#3F5F90"),
    ("Sales", "Products, pricing, discounts and sales processes", "trending_up", "#8F4C38"),
]


# --------------------------------------------------------------------------- connection
def connect(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app: Flask) -> None:
    """Create folders + schema, seed defaults, register teardown."""
    for key in ("DATA_DIR", "UPLOAD_DIR", "CHROMA_DIR", "MODEL_DIR"):
        Path(app.config[key]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DB_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    conn = connect(app.config["DB_PATH"])
    try:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        _migrate(conn)
        _seed(conn, app)
        conn.commit()
    finally:
        conn.close()
    app.teardown_appcontext(close_db)


# Columns added after a table was first created: (table, column, type)
_ADDED_COLUMNS = [
    ("model_runs", "test_accuracy", "REAL"),
    ("model_runs", "test_f1", "REAL"),
    ("model_runs", "n_samples", "INTEGER"),
    ("model_runs", "n_intents", "INTEGER"),
    ("model_runs", "params", "TEXT"),
    ("model_runs", "details", "TEXT"),
    ("documents", "progress", "INTEGER NOT NULL DEFAULT 0"),
    ("documents", "page_count", "INTEGER"),
    ("documents", "char_count", "INTEGER"),
    ("documents", "size_bytes", "INTEGER"),
    ("documents", "file_hash", "TEXT"),
    ("documents", "embed_model", "TEXT"),
    ("documents", "processed_at", "TEXT"),
    ("message_sources", "rank", "INTEGER"),
    ("message_sources", "cited", "INTEGER NOT NULL DEFAULT 0"),
    ("message_sources", "title", "TEXT"),
    ("message_sources", "heading", "TEXT"),
    ("message_sources", "excerpt", "TEXT"),
    ("messages", "rewritten_query", "TEXT"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns that older databases are missing (SQLite has no ADD COLUMN IF NOT EXISTS)."""
    for table, column, col_type in _ADDED_COLUMNS:
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def _seed(conn: sqlite3.Connection, app: Flask) -> None:
    # Intents knowledge base from data/intents.json, only when the table is empty
    intents_file = Path(app.config["INTENTS_FILE"])
    if intents_file.exists() and conn.execute("SELECT COUNT(*) FROM intents").fetchone()[0] == 0:
        import_intents(conn, json.loads(intents_file.read_text(encoding="utf-8"))["intents"])

    # Default settings (never overwrite admin changes)
    for key, value in app.config["DEFAULT_SETTINGS"].items():
        conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (key, value))

    # Default collections, only on a brand-new database
    if conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO collections(name, description, icon, color) VALUES (?, ?, ?, ?)",
            DEFAULT_COLLECTIONS,
        )

    # First admin account
    if conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0] == 0:
        password = app.config.get("ADMIN_PASSWORD")
        generated = not password
        if generated:
            password = secrets.token_urlsafe(12)
        conn.execute(
            "INSERT INTO users(name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (app.config["ADMIN_NAME"], app.config["ADMIN_EMAIL"], generate_password_hash(password)),
        )
        if generated and app.config.get("LOGIN_REQUIRED") and not app.config.get("TESTING"):
            cred_file = Path(app.config["DATA_DIR"]) / "admin_credentials.txt"
            cred_file.write_text(
                "ConvoAI first-run admin account\n"
                f"email: {app.config['ADMIN_EMAIL']}\npassword: {password}\n"
                "Change this password after logging in, then delete this file.\n",
                encoding="utf-8",
            )
            app.logger.warning("Created admin account. Credentials written to %s", cred_file)


# --------------------------------------------------------------------------- users
def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_email(email: str) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email.strip(),)).fetchone()


def touch_last_login(user_id: int) -> None:
    db = get_db()
    db.execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (user_id,))
    db.commit()


def set_user_theme(user_id: int, theme: str) -> None:
    db = get_db()
    db.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, user_id))
    db.commit()


# --------------------------------------------------------------------------- collections
def list_collections() -> list[sqlite3.Row]:
    return get_db().execute(
        """SELECT c.*, (SELECT COUNT(*) FROM documents d WHERE d.collection_id = c.id) AS doc_count
           FROM collections c ORDER BY c.id"""
    ).fetchall()


def collections_for_user(user_id: int, is_admin: bool) -> list[sqlite3.Row]:
    """Admins see every collection; users see the ones they've been granted."""
    if is_admin:
        return list_collections()
    return get_db().execute(
        """SELECT c.*, (SELECT COUNT(*) FROM documents d WHERE d.collection_id = c.id) AS doc_count
           FROM collections c JOIN user_collections uc ON uc.collection_id = c.id
           WHERE uc.user_id = ? ORDER BY c.id""",
        (user_id,),
    ).fetchall()


def get_collection(collection_id: int) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM collections WHERE id = ?", (collection_id,)).fetchone()


# --------------------------------------------------------------------------- documents
_DOC_SELECT = """SELECT d.*, c.name AS collection_name, c.icon AS collection_icon, c.color AS collection_color,
                        u.name AS uploaded_by_name
                 FROM documents d
                 JOIN collections c ON c.id = d.collection_id
                 LEFT JOIN users u ON u.id = d.uploaded_by"""
DOC_FIELDS = {"title", "status", "progress", "chunk_count", "error", "page_count", "char_count",
              "embed_model", "processed_at", "collection_id"}


def create_document(collection_id: int, title: str, source_type: str, path_or_url: str,
                    uploaded_by: int | None, size_bytes: int | None = None, file_hash: str | None = None) -> int:
    db = get_db()
    cur = db.execute(
        """INSERT INTO documents(collection_id, title, source_type, path_or_url, uploaded_by, size_bytes, file_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (collection_id, title, source_type, path_or_url, uploaded_by, size_bytes, file_hash),
    )
    db.commit()
    return cur.lastrowid


def get_document(doc_id: int) -> sqlite3.Row | None:
    return get_db().execute(f"{_DOC_SELECT} WHERE d.id = ?", (doc_id,)).fetchone()


def list_documents(collection_id: int | None = None) -> list[sqlite3.Row]:
    if collection_id:
        return get_db().execute(f"{_DOC_SELECT} WHERE d.collection_id = ? ORDER BY d.id DESC",
                                (collection_id,)).fetchall()
    return get_db().execute(f"{_DOC_SELECT} ORDER BY d.id DESC").fetchall()


def update_document(doc_id: int, **fields) -> None:
    unknown = set(fields) - DOC_FIELDS
    if unknown:
        raise ValueError(f"unknown document fields: {unknown}")
    if not fields:
        return
    db = get_db()
    cols = ", ".join(f"{k} = ?" for k in fields)
    db.execute(f"UPDATE documents SET {cols} WHERE id = ?", (*fields.values(), doc_id))
    db.commit()


def delete_document(doc_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    db.commit()


def find_duplicate_document(collection_id: int, file_hash: str = None, url: str = None) -> sqlite3.Row | None:
    if file_hash:
        return get_db().execute("SELECT * FROM documents WHERE collection_id = ? AND file_hash = ?",
                                (collection_id, file_hash)).fetchone()
    return get_db().execute("SELECT * FROM documents WHERE collection_id = ? AND source_type = 'url' AND path_or_url = ?",
                            (collection_id, url)).fetchone()


def pending_document_ids() -> list[int]:
    return [r["id"] for r in get_db().execute(
        "SELECT id FROM documents WHERE status IN ('queued', 'processing') ORDER BY id")]


# --------------------------------------------------------------------------- conversations
def create_conversation(user_id: int, collection_id: int | None, title: str) -> int:
    db = get_db()
    cur = db.execute("INSERT INTO conversations(user_id, collection_id, title) VALUES (?, ?, ?)",
                     (user_id, collection_id, title[:80] or "New chat"))
    db.commit()
    return cur.lastrowid


def get_conversation(conversation_id: int, user_id: int) -> sqlite3.Row | None:
    """Only the owner can see a conversation."""
    return get_db().execute("SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                            (conversation_id, user_id)).fetchone()


def list_conversations(user_id: int, limit: int = 100) -> list[sqlite3.Row]:
    return get_db().execute(
        """SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
           FROM conversations c WHERE c.user_id = ? ORDER BY c.updated_at DESC, c.id DESC LIMIT ?""",
        (user_id, limit)).fetchall()


def update_conversation(conversation_id: int, **fields) -> None:
    allowed = {"title", "collection_id"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    db = get_db()
    sets = ", ".join([f"{k} = ?" for k in fields] + ["updated_at = datetime('now')"])
    db.execute(f"UPDATE conversations SET {sets} WHERE id = ?", (*fields.values(), conversation_id))
    db.commit()


def delete_conversation(conversation_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    db.commit()


def add_message(conversation_id: int, role: str, content: str, route: str | None = None,
                intent_tag: str | None = None, confidence: float | None = None,
                latency_ms: int | None = None, rewritten_query: str | None = None) -> int:
    db = get_db()
    cur = db.execute(
        """INSERT INTO messages(conversation_id, role, content, route, intent_tag, confidence, latency_ms, rewritten_query)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (conversation_id, role, content, route, intent_tag, confidence, latency_ms, rewritten_query))
    db.execute("UPDATE conversations SET updated_at = datetime('now') WHERE id = ?", (conversation_id,))
    db.commit()
    return cur.lastrowid


def add_message_sources(message_id: int, sources: list[dict]) -> None:
    db = get_db()
    db.executemany(
        """INSERT INTO message_sources(message_id, document_id, chunk_id, page, score, rank, cited, title, heading, excerpt)
           VALUES (?, (SELECT id FROM documents WHERE id = ?), ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(message_id, s["doc_id"], s["chunk_id"], s.get("page"), s.get("score"), s["n"], int(s.get("cited", False)),
          s.get("title"), s.get("heading"), s.get("text")) for s in sources])
    db.commit()


def recent_messages(conversation_id: int, limit: int = 6) -> list[dict]:
    rows = get_db().execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
        (conversation_id, limit)).fetchall()
    return [dict(r) for r in reversed(rows)]


def conversation_messages(conversation_id: int) -> list[dict]:
    db = get_db()
    msgs = [dict(r) for r in db.execute(
        """SELECT m.id, m.role, m.content, m.route, m.intent_tag, m.confidence, m.latency_ms, m.created_at,
                  f.rating AS feedback
           FROM messages m LEFT JOIN feedback f ON f.message_id = m.id
           WHERE m.conversation_id = ? ORDER BY m.id""", (conversation_id,))]
    sources: dict[int, list] = {}
    for s in db.execute(
            """SELECT s.* FROM message_sources s JOIN messages m ON m.id = s.message_id
               WHERE m.conversation_id = ? ORDER BY s.rank""", (conversation_id,)):
        sources.setdefault(s["message_id"], []).append({
            "n": s["rank"], "doc_id": s["document_id"], "chunk_id": s["chunk_id"], "title": s["title"],
            "page": s["page"], "heading": s["heading"], "score": s["score"], "cited": bool(s["cited"]),
            "text": s["excerpt"]})
    for m in msgs:
        m["sources"] = sources.get(m["id"], [])
    return msgs


def message_owner(message_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        """SELECT m.id, m.role, c.user_id FROM messages m JOIN conversations c ON c.id = m.conversation_id
           WHERE m.id = ?""", (message_id,)).fetchone()


def set_feedback(message_id: int, rating: int, comment: str | None = None) -> None:
    db = get_db()
    db.execute("""INSERT INTO feedback(message_id, rating, comment) VALUES (?, ?, ?)
                  ON CONFLICT(message_id) DO UPDATE SET rating = excluded.rating, comment = excluded.comment,
                  created_at = datetime('now')""", (message_id, rating, comment))
    db.commit()


def clear_feedback(message_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM feedback WHERE message_id = ?", (message_id,))
    db.commit()


# --------------------------------------------------------------------------- settings
def get_settings() -> dict[str, str]:
    return {r["key"]: r["value"] for r in get_db().execute("SELECT key, value FROM settings")}


def get_setting(key: str, default: str | None = None) -> str | None:
    row = get_db().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


# --------------------------------------------------------------------------- intents
def import_intents(conn: sqlite3.Connection, intents: list[dict]) -> None:
    """Insert intents (tag, description, patterns, responses); existing tags are replaced."""
    for item in intents:
        conn.execute("DELETE FROM intents WHERE tag = ?", (item["tag"],))
        cur = conn.execute(
            "INSERT INTO intents(tag, description, is_active) VALUES (?, ?, ?)",
            (item["tag"], item.get("description", ""), int(item.get("is_active", True))),
        )
        conn.executemany("INSERT INTO patterns(intent_id, text) VALUES (?, ?)",
                         [(cur.lastrowid, p) for p in item.get("patterns", [])])
        conn.executemany("INSERT INTO responses(intent_id, text) VALUES (?, ?)",
                         [(cur.lastrowid, r) for r in item.get("responses", [])])


def load_intents(active_only: bool = True, conn: sqlite3.Connection | None = None) -> list[dict]:
    """Intents with their patterns and responses, as plain dicts."""
    conn = conn or get_db()
    where = "WHERE is_active = 1" if active_only else ""
    rows = conn.execute(f"SELECT * FROM intents {where} ORDER BY id").fetchall()
    patterns, responses = {}, {}
    for r in conn.execute("SELECT intent_id, text FROM patterns ORDER BY id"):
        patterns.setdefault(r["intent_id"], []).append(r["text"])
    for r in conn.execute("SELECT intent_id, text FROM responses ORDER BY id"):
        responses.setdefault(r["intent_id"], []).append(r["text"])
    return [
        {
            "id": r["id"], "tag": r["tag"], "description": r["description"], "is_active": bool(r["is_active"]),
            "patterns": patterns.get(r["id"], []), "responses": responses.get(r["id"], []),
        }
        for r in rows
    ]


def get_responses(tag: str) -> list[str]:
    return [r["text"] for r in get_db().execute(
        "SELECT r.text FROM responses r JOIN intents i ON i.id = r.intent_id WHERE i.tag = ?", (tag,))]


# --------------------------------------------------------------------------- model runs
def record_model_runs(runs: list[dict], active_algorithm: str) -> None:
    db = get_db()
    db.execute("UPDATE model_runs SET is_active = 0")
    for run in runs:
        db.execute(
            """INSERT INTO model_runs(algorithm, accuracy, precision, recall, f1, test_accuracy, test_f1,
                                      n_samples, n_intents, params, details, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run["algorithm"], run["cv"]["accuracy"], run["cv"]["precision"], run["cv"]["recall"], run["cv"]["f1"],
             run["test"]["accuracy"] if run.get("test") else None, run["test"]["f1"] if run.get("test") else None,
             run["n_samples"], run["n_intents"], json.dumps(run["params"]), json.dumps(run["details"]),
             int(run["algorithm"] == active_algorithm)),
        )
    db.commit()


def latest_model_runs(limit: int = 10) -> list[sqlite3.Row]:
    return get_db().execute(
        "SELECT id, algorithm, accuracy, precision, recall, f1, test_accuracy, test_f1, n_samples, n_intents,"
        " params, trained_at, is_active FROM model_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()


# --------------------------------------------------------------------------- admin: collections
def create_collection(name: str, description: str, icon: str, color: str) -> int:
    db = get_db()
    cur = db.execute("INSERT INTO collections(name, description, icon, color) VALUES (?, ?, ?, ?)",
                     (name, description, icon, color))
    db.commit()
    return cur.lastrowid


def update_collection(collection_id: int, **fields) -> None:
    fields = {k: v for k, v in fields.items() if k in {"name", "description", "icon", "color"}}
    if not fields:
        return
    db = get_db()
    db.execute(f"UPDATE collections SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?",
               (*fields.values(), collection_id))
    db.commit()


def delete_collection(collection_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
    db.commit()


def collection_name_taken(name: str, exclude_id: int | None = None) -> bool:
    row = get_db().execute("SELECT id FROM collections WHERE name = ? AND id IS NOT ?", (name, exclude_id)).fetchone()
    return row is not None


# --------------------------------------------------------------------------- admin: users
def list_users() -> list[dict]:
    db = get_db()
    access: dict[int, list[int]] = {}
    for r in db.execute("SELECT user_id, collection_id FROM user_collections ORDER BY collection_id"):
        access.setdefault(r["user_id"], []).append(r["collection_id"])
    users = []
    for r in db.execute("""SELECT u.id, u.name, u.email, u.role, u.is_active, u.created_at, u.last_login_at,
                                  (SELECT COUNT(*) FROM conversations c WHERE c.user_id = u.id) AS conversations
                           FROM users u ORDER BY u.id"""):
        users.append({**dict(r), "is_active": bool(r["is_active"]), "collection_ids": access.get(r["id"], [])})
    return users


def create_user(name: str, email: str, password: str, role: str) -> int:
    db = get_db()
    cur = db.execute("INSERT INTO users(name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                     (name, email, generate_password_hash(password), role))
    db.commit()
    return cur.lastrowid


def update_user(user_id: int, **fields) -> None:
    if "password" in fields:
        password = fields.pop("password")
        if password:
            fields["password_hash"] = generate_password_hash(password)
    fields = {k: v for k, v in fields.items() if k in {"name", "email", "role", "is_active", "password_hash"}}
    if not fields:
        return
    db = get_db()
    db.execute(f"UPDATE users SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", (*fields.values(), user_id))
    db.commit()


def set_user_collections(user_id: int, collection_ids: list[int]) -> None:
    db = get_db()
    db.execute("DELETE FROM user_collections WHERE user_id = ?", (user_id,))
    db.executemany("INSERT INTO user_collections(user_id, collection_id) VALUES (?, ?)",
                   [(user_id, cid) for cid in sorted(set(collection_ids))])
    db.commit()


def delete_user(user_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()


def active_admin_count(exclude_id: int | None = None) -> int:
    return get_db().execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1 AND id IS NOT ?",
                            (exclude_id,)).fetchone()[0]


def email_taken(email: str, exclude_id: int | None = None) -> bool:
    return get_db().execute("SELECT 1 FROM users WHERE email = ? AND id IS NOT ?", (email, exclude_id)).fetchone() is not None


# --------------------------------------------------------------------------- admin: intents
def get_intent(intent_id: int) -> dict | None:
    return next((i for i in load_intents(active_only=False) if i["id"] == intent_id), None)


def save_intent(intent_id: int | None, tag: str, description: str, is_active: bool,
                patterns: list[str], responses: list[str]) -> int:
    """Create (intent_id None) or replace an intent with its patterns and responses."""
    db = get_db()
    if intent_id is None:
        intent_id = db.execute("INSERT INTO intents(tag, description, is_active) VALUES (?, ?, ?)",
                               (tag, description, int(is_active))).lastrowid
    else:
        db.execute("UPDATE intents SET tag = ?, description = ?, is_active = ? WHERE id = ?",
                   (tag, description, int(is_active), intent_id))
        db.execute("DELETE FROM patterns WHERE intent_id = ?", (intent_id,))
        db.execute("DELETE FROM responses WHERE intent_id = ?", (intent_id,))
    db.executemany("INSERT INTO patterns(intent_id, text) VALUES (?, ?)", [(intent_id, p) for p in patterns])
    db.executemany("INSERT INTO responses(intent_id, text) VALUES (?, ?)", [(intent_id, r) for r in responses])
    db.execute("INSERT INTO settings(key, value) VALUES ('intents_dirty', '1') "
               "ON CONFLICT(key) DO UPDATE SET value = '1'")
    db.commit()
    return intent_id


def delete_intent(intent_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM intents WHERE id = ?", (intent_id,))
    db.execute("INSERT INTO settings(key, value) VALUES ('intents_dirty', '1') "
               "ON CONFLICT(key) DO UPDATE SET value = '1'")
    db.commit()


def intent_tag_taken(tag: str, exclude_id: int | None = None) -> bool:
    return get_db().execute("SELECT 1 FROM intents WHERE tag = ? AND id IS NOT ?", (tag, exclude_id)).fetchone() is not None


# --------------------------------------------------------------------------- admin: settings
def set_settings(values: dict[str, str]) -> None:
    db = get_db()
    db.executemany("INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                   [(k, str(v)) for k, v in values.items()])
    db.commit()


# --------------------------------------------------------------------------- stats
def counts() -> dict[str, int]:
    db = get_db()
    q = lambda sql: db.execute(sql).fetchone()[0]  # noqa: E731
    return {
        "users": q("SELECT COUNT(*) FROM users"),
        "collections": q("SELECT COUNT(*) FROM collections"),
        "documents": q("SELECT COUNT(*) FROM documents"),
        "intents": q("SELECT COUNT(*) FROM intents"),
        "messages": q("SELECT COUNT(*) FROM messages"),
    }
