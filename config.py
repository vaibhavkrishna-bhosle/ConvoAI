"""Central configuration for ConvoAI.

Values can be overridden with environment variables (or a .env file).
Runtime-tunable values (model names, thresholds) are also stored in the
`settings` table so admins can change them from the UI.
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = Path(os.getenv("CONVOAI_DATA_DIR", BASE_DIR / "data"))


def _secret_key() -> str:
    """Use SECRET_KEY from env, else a key persisted in data/.secret_key."""
    if os.getenv("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    key_file = DATA_DIR / ".secret_key"
    if not key_file.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        key_file.write_text(secrets.token_hex(32))
    return key_file.read_text().strip()


class Config:
    SECRET_KEY = _secret_key()

    DATA_DIR = DATA_DIR
    DB_PATH = Path(os.getenv("CONVOAI_DB", DATA_DIR / "convoai.db"))
    UPLOAD_DIR = DATA_DIR / "uploads"
    CHROMA_DIR = DATA_DIR / "chroma"
    MODEL_DIR = DATA_DIR / "models"
    INTENTS_FILE = DATA_DIR / "intents.json"
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB uploads

    # Sign-in. Off by default: ConvoAI runs on one computer, so everyone using it is the
    # built-in local admin. Set LOGIN_REQUIRED=1 to require accounts and per-department access.
    LOGIN_REQUIRED = os.getenv("LOGIN_REQUIRED", "0").lower() in ("1", "true", "yes")

    # First-run admin account (see .env.example)
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrator")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@convoai.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")  # generated if missing

    # Ollama / RAG defaults (copied into the settings table on first run)
    # 127.0.0.1, not "localhost": on Windows "localhost" tries IPv6 (::1) first, and Ollama only
    # listens on IPv4, which added ~2 s to every embedding and chat call (measured).
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    DEFAULT_SETTINGS = {
        "llm_model": os.getenv("LLM_MODEL", "qwen2.5:7b-instruct"),
        "llm_fallback_model": "llama3.2:3b",
        "embed_model": os.getenv("EMBED_MODEL", "nomic-embed-text"),
        "temperature": "0.2",
        "top_k": "5",
        "neighbor_chunks": "0",   # decided by the Phase 9 answer evaluation
        "chunk_size": "800",
        "chunk_overlap": "150",
        "relevance_threshold": "0.618",  # tuned with `python -m rag.evaluate --apply` (nomic-embed-text)
        "relevance_floor": "0.57",       # grey zone needing keyword agreement (Phase 9 follow-up fix)
        "intent_threshold": "0.35",      # tuned by `python -m nlp.train`
        "max_answer_tokens": "700",
        # Voice input (local Whisper). CPU keeps the 6 GB GPU free for the chat model.
        "whisper_model": "small",
        "whisper_device": "cpu",
        "speech_language": "en",       # "auto" to detect the language
        "context_window": "4096",  # 6144 doesn't fit a 6 GB GPU next to the embedding model
    }

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    LOGIN_REQUIRED = True  # most tests exercise accounts and access control
