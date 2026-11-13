"""Analytics + model metrics API (FR-07, FR-08). Admin only.

GET  /api/analytics?days=7|30|90|0      usage dashboard (0 = all time)
GET  /api/metrics                       intent classifier report + retrieval evaluation report
POST /api/metrics/rag/evaluate          re-run the retrieval evaluation now (~10 s)
"""
from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from models import database as db
from models.user import admin_required
from services import analytics

bp = Blueprint("analytics_api", __name__, url_prefix="/api")


@bp.get("/analytics")
@admin_required
def dashboard():
    days = request.args.get("days", 30, type=int)
    if days not in (0, 1, 7, 30, 90, 365):
        return jsonify(error="days must be 0, 1, 7, 30, 90 or 365"), 400
    return jsonify(analytics.dashboard(days or None))


def _read_json(name: str) -> dict | None:
    path = Path(current_app.config["MODEL_DIR"]) / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@bp.get("/metrics")
@admin_required
def metrics():
    from nlp.classifier import REPORT_FILENAME

    settings = db.get_settings()
    return jsonify(intent=_read_json(REPORT_FILENAME), rag=_read_json("rag_report.json"),
                   thresholds={"intent": float(settings.get("intent_threshold", 0.35)),
                               "relevance": float(settings.get("relevance_threshold", 0.618))},
                   intents_dirty=settings.get("intents_dirty") == "1")


@bp.post("/metrics/rag/evaluate")
@admin_required
def run_rag_evaluation():
    from rag.embeddings import EmbeddingError
    from rag.evaluate import evaluate, to_markdown

    app = current_app._get_current_object()
    gold = Path(app.config["DATA_DIR"]) / "rag_eval.json"
    if not gold.exists():
        return jsonify(error="No evaluation set found (data/rag_eval.json)."), 404
    try:
        report = evaluate(app)
    except EmbeddingError as exc:
        return jsonify(error=str(exc)), 503
    model_dir = Path(app.config["MODEL_DIR"])
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "rag_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (model_dir / "rag_report.md").write_text(to_markdown(report), encoding="utf-8")
    return jsonify(report)
