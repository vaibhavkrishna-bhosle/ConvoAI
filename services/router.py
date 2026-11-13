"""Hybrid message router (the heart of ConvoAI).

    message ─► intent classifier ─► confident small talk? ─► canned reply          (route "intent")
                                 └► otherwise ─► rewrite follow-up ─► hybrid retrieval
                                        ├─ nothing relevant ─► polite "not found"  (route "fallback")
                                        └─ relevant chunks ─► grounded LLM answer   (route "rag")

`handle()` is a generator of events, so the same code serves the streaming
endpoint (Server-Sent Events) and the plain JSON endpoint. Every user and bot
message is saved with its route, intent, confidence, latency and sources.
"""
from __future__ import annotations

import time
from typing import Iterator

from flask import current_app

from models import database as db
from rag import prompt as P
from rag.embeddings import EmbeddingError, get_embedder
from rag.llm import LLMError, get_llm
from rag.retriever import expand_with_neighbors, retrieve
from rag.store import get_store
from services.intents import classify

NOT_FOUND_MARKER = "couldn't find that in the documents"


class ChatError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _source_json(n: int, hit, cited: bool = False) -> dict:
    return {"n": n, "doc_id": hit.doc_id, "chunk_id": hit.id, "title": hit.title, "page": hit.page,
            "heading": hit.heading, "score": hit.score, "cited": cited, "text": hit.text,
            "label": P.source_label(hit)}


def prepare(user, text: str, conversation_id: int | None, collection_id: int | None) -> dict:
    """Validate the request before streaming starts (so errors become proper HTTP status codes)."""
    text = (text or "").strip()
    if not text:
        raise ChatError("Message is empty.")
    if len(text) > 4000:
        raise ChatError("Message is too long (max 4000 characters).")

    allowed = db.collections_for_user(user.id, user.is_admin)
    allowed_ids = [c["id"] for c in allowed]
    if collection_id is not None:
        if collection_id not in allowed_ids:
            raise ChatError("You don't have access to that collection.", 403)
        scope = [c for c in allowed if c["id"] == collection_id]
    else:
        scope = list(allowed)

    if conversation_id is not None:
        if db.get_conversation(conversation_id, user.id) is None:
            raise ChatError("Conversation not found.", 404)
    return {"text": text, "conversation_id": conversation_id, "collection_id": collection_id,
            "scope_ids": [c["id"] for c in scope], "scope_names": [c["name"] for c in scope],
            "all_names": [c["name"] for c in allowed]}


def handle(user, req: dict) -> Iterator[dict]:
    """Run one chat turn. Yields events: start, status, sources, token, done (and error).

    If the client stops reading (the Stop button, or a closed tab), the server notices at the
    next write and closes this generator; the partial answer is then saved, marked as stopped,
    so the conversation never ends with an unanswered question."""
    turn = {"conversation_id": None, "saved": False, "parts": [], "sources": None,
            "started": time.perf_counter()}
    inner = _run(user, req, turn)
    try:
        yield from inner
    except GeneratorExit:
        if turn["conversation_id"] and not turn["saved"]:
            partial = "".join(turn["parts"]).strip()
            content = f"{partial}\n\n_(Stopped.)_" if partial else "_(Stopped before an answer was written.)_"
            message_id = db.add_message(turn["conversation_id"], "bot", content, route="rag" if partial else None,
                                        latency_ms=int((time.perf_counter() - turn["started"]) * 1000))
            if partial and turn["sources"]:
                cited = set(P.cited_numbers(partial, len(turn["sources"])))
                db.add_message_sources(message_id, [{**s, "cited": s["n"] in cited} for s in turn["sources"]])
        raise


def _run(user, req: dict, turn: dict) -> Iterator[dict]:
    app = current_app._get_current_object()
    started = turn["started"]
    text = req["text"]

    conversation_id = req["conversation_id"]
    history = db.recent_messages(conversation_id) if conversation_id else []
    if conversation_id is None:
        conversation_id = db.create_conversation(user.id, req["collection_id"], text[:60])
    else:
        db.update_conversation(conversation_id, collection_id=req["collection_id"])
    turn["conversation_id"] = conversation_id
    user_message_id = db.add_message(conversation_id, "user", text)
    yield {"type": "start", "conversation_id": conversation_id, "user_message_id": user_message_id}

    def elapsed() -> int:
        return int((time.perf_counter() - started) * 1000)

    timings: dict[str, int] = {}  # per-stage milliseconds, returned with the answer
    mark = [time.perf_counter()]

    def lap(stage: str) -> None:
        now = time.perf_counter()
        timings[stage] = int((now - mark[0]) * 1000)
        mark[0] = now

    def finish(content: str, route: str, sources: list[dict] | None = None, rewritten: str | None = None,
               intent: str | None = None, confidence: float | None = None) -> dict:
        latency = elapsed()
        turn["saved"] = True
        message_id = db.add_message(conversation_id, "bot", content, route=route, intent_tag=intent,
                                    confidence=confidence, latency_ms=latency, rewritten_query=rewritten)
        if sources:
            db.add_message_sources(message_id, sources)
        return {"type": "done", "conversation_id": conversation_id, "message_id": message_id, "route": route,
                "content": content, "intent": intent, "confidence": confidence, "latency_ms": latency,
                "rewritten_query": rewritten, "sources": sources or [], "timings_ms": timings}

    # 1 ── intent fast path ----------------------------------------------------------------------
    lap("save")
    intent = classify(text, user.name, req["all_names"])
    lap("intent")
    if intent["route"] == "intent":
        yield finish(intent["reply"], "intent", intent=intent["intent"], confidence=intent["confidence"])
        return

    intent_tag, intent_conf = intent["intent"], intent["confidence"]
    if not req["scope_ids"]:
        yield finish("You don't have access to any document collections yet. Ask an administrator to give you "
                     "access, and then I can answer questions from your company's documents.",
                     "fallback", intent=intent_tag, confidence=intent_conf)
        return

    llm = get_llm(app)
    settings = db.get_settings()

    # 2 ── follow-up rewriting -------------------------------------------------------------------
    query = text
    if P.needs_rewrite(text, history):
        yield {"type": "status", "text": "Understanding your follow-up…"}
        try:
            rewritten = llm.complete(P.rewrite_messages(text, history), max_tokens=80)
            rewritten = rewritten.strip().strip('"').splitlines()[0] if rewritten.strip() else ""
            if 3 <= len(rewritten) <= 400:
                query = rewritten
        except LLMError:
            pass  # retrieval still works with the original wording
        lap("rewrite")
    rewritten_query = query if query != text else None

    # 3 ── hybrid retrieval ----------------------------------------------------------------------
    scope_label = ", ".join(req["scope_names"]) if len(req["scope_names"]) <= 3 else "your"
    yield {"type": "status", "text": f"Searching {scope_label} documents…"}
    try:
        vector = get_embedder(app).embed_query(query)
        lap("embed")
    except EmbeddingError as exc:
        yield {"type": "error", "error": str(exc)}
        yield finish(f"Sorry, I can't search the documents right now: {exc}", "fallback",
                     rewritten=rewritten_query, intent=intent_tag, confidence=intent_conf)
        return

    store = get_store(app)
    result = retrieve(store, vector, query, req["scope_ids"],
                      top_k=int(settings.get("top_k", 5)), threshold=float(settings.get("relevance_threshold", 0.618)),
                      floor=float(settings.get("relevance_floor", 0.57)))
    if result.relevant and settings.get("neighbor_chunks", "0") == "1":
        # neighbours come from the same documents, so collection access control still holds
        result.hits = expand_with_neighbors(store, result.hits)
    lap("retrieve")

    if not result.relevant or not result.hits:
        where = f"the {scope_label} documents" if scope_label != "your" else "your documents"
        yield finish(f"I couldn't find anything about that in {where}. Try rephrasing your question with more "
                     "detail, or choose a different collection.", "fallback",
                     rewritten=rewritten_query, intent=intent_tag, confidence=intent_conf)
        return

    sources = [_source_json(i, h) for i, h in enumerate(result.hits, start=1)]
    turn["sources"] = sources
    yield {"type": "sources", "sources": sources, "best_score": result.best_vector}

    # 4 ── grounded generation (streamed) --------------------------------------------------------
    yield {"type": "status", "text": "Writing the answer…"}
    parts: list[str] = turn["parts"]
    try:
        for token in llm.stream(P.build_messages(query, result.hits, history)):
            if not parts:
                lap("first_token")
            parts.append(token)
            yield {"type": "token", "text": token}
        lap("generate")
    except LLMError as exc:
        yield {"type": "error", "error": str(exc)}
        partial = "".join(parts).strip()
        msg = (partial + "\n\n_(The answer was cut off.)_") if partial else f"Sorry, the language model isn't available right now: {exc}"
        yield finish(msg, "fallback", rewritten=rewritten_query, intent=intent_tag, confidence=intent_conf)
        return

    answer = P.remove_invalid_citations("".join(parts).strip(), len(sources))
    if not answer:
        answer = "I couldn't find that in the documents you have access to."
    for n in P.cited_numbers(answer, len(sources)):
        sources[n - 1]["cited"] = True

    # The model itself can decide the sources don't answer the question
    route = "fallback" if NOT_FOUND_MARKER in answer.lower() and not any(s["cited"] for s in sources) else "rag"
    yield finish(answer, route, sources=sources, rewritten=rewritten_query, intent=intent_tag, confidence=intent_conf)
