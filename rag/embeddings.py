"""Embeddings via Ollama (nomic-embed-text, 768-d).

nomic-embed-text is trained with task prefixes: documents are embedded as
"search_document: …" and questions as "search_query: …".
A deterministic `HashEmbedder` is used in tests so they don't need Ollama.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Callable, Protocol

BATCH_SIZE = 32
KEEP_ALIVE = "30m"  # keep the model on the GPU between uploads (first load takes ~15 s)


class EmbeddingError(Exception):
    pass


class Embedder(Protocol):
    model: str

    def embed_documents(self, texts: list[str], progress: Callable[[int], None] | None = None) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class OllamaEmbedder:
    def __init__(self, host: str, model: str):
        import ollama

        self.model = model
        self._client = ollama.Client(host=host, timeout=300)

    def _prefix(self, kind: str) -> str:
        return f"search_{kind}: " if "nomic" in self.model else ""

    def _embed(self, texts: list[str]) -> list[list[float]]:
        import ollama

        try:
            return list(self._client.embed(model=self.model, input=texts, keep_alive=KEEP_ALIVE).embeddings)
        except ollama.ResponseError as exc:
            if exc.status_code == 404:
                raise EmbeddingError(f"Embedding model '{self.model}' is not installed. Run: ollama pull {self.model}") from exc
            raise EmbeddingError(f"Ollama error: {exc.error}") from exc
        except (ConnectionError, OSError) as exc:  # httpx.ConnectError subclasses these
            raise EmbeddingError("Cannot reach Ollama. Is it running? (ollama serve)") from exc
        except Exception as exc:
            if "connect" in type(exc).__name__.lower():
                raise EmbeddingError("Cannot reach Ollama. Is it running? (ollama serve)") from exc
            raise

    def embed_documents(self, texts, progress=None):
        prefix, vectors = self._prefix("document"), []
        for start in range(0, len(texts), BATCH_SIZE):
            vectors.extend(self._embed([prefix + t for t in texts[start:start + BATCH_SIZE]]))
            if progress:
                progress(len(vectors))
        return vectors

    def embed_query(self, text):
        return self._embed([self._prefix("query") + text])[0]


class HashEmbedder:
    """Bag-of-words hashing into a fixed vector. Meaningful enough for tests, needs no model."""

    model = "hash-test"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0 if (h >> 8) & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts, progress=None):
        out = [self._vec(t) for t in texts]
        if progress:
            progress(len(out))
        return out

    def embed_query(self, text):
        return self._vec(text)


def get_embedder(app) -> Embedder:
    if app.config.get("EMBEDDER") == "hash":
        return HashEmbedder()
    from models import database as db

    model = db.get_setting("embed_model", app.config["DEFAULT_SETTINGS"]["embed_model"])
    return OllamaEmbedder(app.config["OLLAMA_HOST"], model)
