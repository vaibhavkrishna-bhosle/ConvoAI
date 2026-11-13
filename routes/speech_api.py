"""Speech API.

POST /api/speech/transcribe   multipart field "audio" → {text, language, duration_s, ms, …}
GET  /api/speech/status       {available, model, device, loaded}
"""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required

from models import database as db
from services.speech import MAX_AUDIO_BYTES, SpeechError, get_transcriber, vocabulary_hint

bp = Blueprint("speech_api", __name__, url_prefix="/api/speech")


def _app():
    return current_app._get_current_object()


@bp.get("/status")
@login_required
def status():
    try:
        import faster_whisper  # noqa: F401
        available = True
    except ImportError:
        available = current_app.config.get("SPEECH") == "fake"
    t = get_transcriber(_app()) if available else None
    return jsonify(available=available, model=getattr(t, "model_name", None),
                   device=getattr(t, "device", None), loaded=bool(getattr(t, "loaded", False)))


@bp.post("/transcribe")
@login_required
def transcribe():
    upload = request.files.get("audio")
    if upload is None:
        return jsonify(error="No audio received."), 400
    audio = upload.read(MAX_AUDIO_BYTES + 1)
    if len(audio) > MAX_AUDIO_BYTES:
        return jsonify(error="The recording is too large (max 10 MB)."), 413
    if len(audio) < 100:
        return jsonify(error="The recording is empty."), 400

    language = db.get_setting("speech_language", "en") or None
    if language == "auto":
        language = None
    try:
        result = get_transcriber(_app()).transcribe(audio, language=language, hint=vocabulary_hint(_app()))
    except SpeechError as exc:
        return jsonify(error=str(exc)), exc.status
    if not result["text"]:
        return jsonify(error="I didn't catch that. Try again a little closer to the microphone.", **result), 422
    return jsonify(result)
