"""JSON REST API (FR-08). Chat/document endpoints are added in later phases."""
import requests
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from models import database as db
from models.user import admin_required

bp = Blueprint("api", __name__, url_prefix="/api")


def _ollama_status() -> dict:
    host = current_app.config["OLLAMA_HOST"]
    try:
        resp = requests.get(f"{host}/api/tags", timeout=2)
        resp.raise_for_status()
        models = sorted(m["name"] for m in resp.json().get("models", []))
        return {"ok": True, "host": host, "models": models}
    except requests.RequestException as exc:
        return {"ok": False, "host": host, "error": type(exc).__name__}


@bp.get("/health")
def health():
    try:
        db.get_db().execute("SELECT 1")
        db_ok = True
    except Exception:  # pragma: no cover - reported, not raised
        db_ok = False
    ollama = _ollama_status()
    status = "ok" if db_ok and ollama["ok"] else "degraded"
    return jsonify(status=status, database={"ok": db_ok}, ollama=ollama)


@bp.post("/intent/predict")
@login_required
def intent_predict():
    """Classify a message with the intent model (FR-02/03). Body: {"text": "..."}"""
    from services.intents import classify

    text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
    if not text:
        return jsonify(error="text is required"), 400
    if len(text) > 2000:
        return jsonify(error="text is too long (max 2000 characters)"), 400
    names = [c["name"] for c in db.collections_for_user(current_user.id, current_user.is_admin)]
    return jsonify(classify(text, current_user.name, names, with_steps=True))


@bp.post("/model/train")
@admin_required
def model_train():
    """Retrain the intent classifier from the intents in the database."""
    from nlp.classifier import train_and_activate

    report = train_and_activate(current_app._get_current_object())
    return jsonify(
        best=report["best"],
        trained_at=report["trained_at"],
        threshold=float(db.get_setting("intent_threshold")),
        runs=[{"algorithm": r["algorithm"], "name": r["name"], "params": r["params"],
               "cv": r["cv"], "test": r["test"]} for r in report["runs"]],
    )


@bp.get("/model/runs")
@admin_required
def model_runs():
    return jsonify([dict(r) for r in db.latest_model_runs()])


@bp.get("/me")
@login_required
def me():
    return jsonify(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        theme=current_user.theme,
    )


@bp.post("/me/theme")
@login_required
def set_theme():
    theme = (request.get_json(silent=True) or {}).get("theme")
    if theme not in ("light", "dark", "system"):
        return jsonify(error="theme must be light, dark or system"), 400
    db.set_user_theme(current_user.id, theme)
    return jsonify(theme=theme)
