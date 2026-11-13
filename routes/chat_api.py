"""Chat REST API (FR-01, FR-05, FR-08).

POST /api/chat                      {message, conversation_id?, collection_id?} → full answer as JSON
POST /api/chat/stream               same body → text/event-stream (events: start, status, sources, token, done, error)
GET  /api/conversations             the signed-in user's conversations
GET  /api/conversations/<id>        messages with their sources
PATCH /api/conversations/<id>       {title}
DELETE /api/conversations/<id>
POST /api/messages/<id>/feedback    {rating: 1 | -1 | 0, comment?}   (0 clears it)

The stream uses POST (not EventSource/GET) because it carries a JSON body and the CSRF header;
the browser reads it with fetch() + ReadableStream.
"""
from __future__ import annotations

import json

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask_login import current_user, login_required

from models import database as db
from services import router

bp = Blueprint("chat_api", __name__, url_prefix="/api")


def _parse_request() -> dict:
    body = request.get_json(silent=True) or {}

    def opt_int(key):
        value = body.get(key)
        if value in (None, "", "all"):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise router.ChatError(f"{key} must be a number.")

    return router.prepare(current_user, body.get("message"), opt_int("conversation_id"), opt_int("collection_id"))


@bp.errorhandler(router.ChatError)
def _chat_error(exc: router.ChatError):
    return jsonify(error=str(exc)), exc.status


@bp.post("/chat")
@login_required
def chat():
    req = _parse_request()
    done, statuses, errors = None, [], []
    for event in router.handle(current_user, req):
        if event["type"] == "done":
            done = event
        elif event["type"] == "status":
            statuses.append(event["text"])
        elif event["type"] == "error":
            errors.append(event["error"])
    done.pop("type", None)
    return jsonify({**done, "warnings": errors})


@bp.post("/chat/stream")
@login_required
def chat_stream():
    req = _parse_request()  # validation errors return normal JSON errors before the stream opens
    user = current_user._get_current_object()

    def events():
        try:
            for event in router.handle(user, req):
                yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # last resort: tell the client instead of silently closing
            from flask import current_app
            current_app.logger.exception("Chat stream failed")
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': f'Unexpected error: {exc}'})}\n\n"

    return Response(stream_with_context(events()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# --------------------------------------------------------------------------- conversations
def _own_conversation(conversation_id: int):
    conv = db.get_conversation(conversation_id, current_user.id)
    if conv is None:
        raise router.ChatError("Conversation not found.", 404)
    return conv


@bp.get("/conversations")
@login_required
def conversations():
    return jsonify(conversations=[dict(r) for r in db.list_conversations(current_user.id)])


@bp.get("/conversations/<int:conversation_id>")
@login_required
def conversation(conversation_id):
    conv = _own_conversation(conversation_id)
    return jsonify(conversation=dict(conv), messages=db.conversation_messages(conversation_id))


@bp.patch("/conversations/<int:conversation_id>")
@login_required
def rename_conversation(conversation_id):
    _own_conversation(conversation_id)
    title = ((request.get_json(silent=True) or {}).get("title") or "").strip()
    if not title:
        raise router.ChatError("Title is required.")
    db.update_conversation(conversation_id, title=title[:80])
    return jsonify(conversation=dict(db.get_conversation(conversation_id, current_user.id)))


@bp.delete("/conversations/<int:conversation_id>")
@login_required
def delete_conversation(conversation_id):
    _own_conversation(conversation_id)
    db.delete_conversation(conversation_id)
    return jsonify(deleted=conversation_id)


@bp.post("/messages/<int:message_id>/feedback")
@login_required
def feedback(message_id):
    owner = db.message_owner(message_id)
    if owner is None or owner["user_id"] != current_user.id:
        raise router.ChatError("Message not found.", 404)
    if owner["role"] != "bot":
        raise router.ChatError("Only answers can be rated.")
    body = request.get_json(silent=True) or {}
    rating = body.get("rating")
    if rating == 0:
        db.clear_feedback(message_id)
    elif rating in (1, -1):
        db.set_feedback(message_id, rating, (body.get("comment") or "").strip()[:1000] or None)
    else:
        raise router.ChatError("rating must be 1, -1 or 0.")
    return jsonify(message_id=message_id, rating=rating or None)
