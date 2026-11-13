-- ConvoAI SQLite schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    theme         TEXT NOT NULL DEFAULT 'system' CHECK (theme IN ('light', 'dark', 'system')),
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS collections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    description TEXT NOT NULL DEFAULT '',
    icon        TEXT NOT NULL DEFAULT 'folder',
    color       TEXT NOT NULL DEFAULT '#006A6A',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_collections (
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, collection_id)
);

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    source_type   TEXT NOT NULL CHECK (source_type IN ('pdf', 'docx', 'txt', 'md', 'url')),
    path_or_url   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'queued'
                  CHECK (status IN ('queued', 'processing', 'ready', 'failed')),
    chunk_count   INTEGER NOT NULL DEFAULT 0,
    error         TEXT,
    uploaded_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at   TEXT NOT NULL DEFAULT (datetime('now')),
    progress      INTEGER NOT NULL DEFAULT 0,   -- 0-100 while processing
    page_count    INTEGER,
    char_count    INTEGER,
    size_bytes    INTEGER,
    file_hash     TEXT,                         -- sha256, to skip duplicate uploads
    embed_model   TEXT,
    processed_at  TEXT
);

CREATE TABLE IF NOT EXISTS intents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tag         TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS patterns (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id INTEGER NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
    text      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS responses (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id INTEGER NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
    text      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    collection_id INTEGER REFERENCES collections(id) ON DELETE SET NULL,
    title         TEXT NOT NULL DEFAULT 'New chat',
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'bot')),
    content         TEXT NOT NULL,
    route           TEXT CHECK (route IN ('intent', 'rag', 'fallback')),
    intent_tag      TEXT,
    confidence      REAL,
    latency_ms      INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS message_sources (
    message_id  INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    chunk_id    TEXT NOT NULL,
    page        INTEGER,
    score       REAL,
    rank        INTEGER,                 -- position given to the model ([1], [2] …)
    cited       INTEGER NOT NULL DEFAULT 0,
    title       TEXT,
    heading     TEXT,
    excerpt     TEXT                     -- chunk text at answer time (survives re-indexing)
);
CREATE INDEX IF NOT EXISTS idx_message_sources ON message_sources(message_id);

CREATE TABLE IF NOT EXISTS feedback (
    message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    rating     INTEGER NOT NULL CHECK (rating IN (-1, 1)),
    comment    TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm  TEXT NOT NULL,
    accuracy   REAL,
    precision  REAL,
    recall     REAL,
    f1         REAL,
    trained_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_active  INTEGER NOT NULL DEFAULT 0,
    test_accuracy REAL,           -- held-out set (data/intent_test.json)
    test_f1       REAL,
    n_samples     INTEGER,
    n_intents     INTEGER,
    params        TEXT,           -- JSON: best hyper-parameters
    details       TEXT            -- JSON: per-class report, confusion matrix, labels
);

CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user    ON conversations(user_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_created      ON messages(created_at);
