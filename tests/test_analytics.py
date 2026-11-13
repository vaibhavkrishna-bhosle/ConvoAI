"""Phase 8 tests: analytics figures computed from real messages, metrics API, admin-only access."""
import json

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestConfig
from models import database as db
from services import analytics

ADMIN_PW, USER_PW = "test-admin-pw", "test-user-pw"


@pytest.fixture()
def app(tmp_path):
    class Cfg(TestConfig):
        DATA_DIR = tmp_path
        DB_PATH = tmp_path / "test.db"
        UPLOAD_DIR = tmp_path / "uploads"
        CHROMA_DIR = tmp_path / "chroma"
        MODEL_DIR = tmp_path / "models"
        ADMIN_PASSWORD = ADMIN_PW

    app = create_app(Cfg)
    with app.app_context():
        conn = db.get_db()
        conn.execute("INSERT INTO users(name, email, password_hash) VALUES ('Riya', 'riya@convoai.local', ?)",
                     (generate_password_hash(USER_PW),))
        conn.execute("INSERT INTO documents(id, collection_id, title, source_type, path_or_url, status) "
                     "VALUES (1, 2, 'Leave Policy', 'md', 'x', 'ready')")
        conn.commit()
        _seed_history()
    return app


def _turn(cid, question, route, answer="answer", intent=None, latency=1000, cited_doc=None, rating=None):
    db.add_message(cid, "user", question)
    mid = db.add_message(cid, "bot", answer, route=route, intent_tag=intent, latency_ms=latency)
    if cited_doc:
        db.add_message_sources(mid, [{"n": 1, "doc_id": cited_doc, "chunk_id": f"{cited_doc}:0", "page": 2,
                                      "score": 0.7, "cited": True, "title": "Leave Policy", "heading": None, "text": "t"}])
    if rating:
        db.set_feedback(mid, rating, "too vague" if rating == -1 else None)
    return mid


def _seed_history():
    c1 = db.create_conversation(1, None, "admin chat")
    _turn(c1, "hi", "intent", "Hello!", intent="greeting", latency=5)
    _turn(c1, "How many casual leaves?", "rag", "12 days [1]", latency=2000, cited_doc=1, rating=1)
    _turn(c1, "What is the capital of France?", "fallback", "I couldn't find…", latency=600)
    c2 = db.create_conversation(2, 2, "riya chat")                      # HR collection
    _turn(c2, "what is the capital of france? ", "fallback", "I couldn't find…", latency=700)
    _turn(c2, "Sick leave rules?", "rag", "10 days [1]", latency=4000, cited_doc=1, rating=-1)
    _turn(c2, "thanks", "intent", "You're welcome", intent="thanks", latency=7)


def test_dashboard_figures(app):
    with app.app_context():
        d = analytics.dashboard(30)
    k = d["kpis"]
    assert k["questions"] == 6 and k["answered"] == 6 and k["conversations"] == 2 and k["users"] == 2
    assert d["routes"] == {"rag": 2, "intent": 2, "fallback": 2}
    assert k["rag_rate"] == pytest.approx(1 / 3, abs=1e-3) and k["fallback_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert k["thumbs_up"] == 1 and k["thumbs_down"] == 1 and k["satisfaction"] == 0.5
    assert d["latency"]["rag"]["median_ms"] == 3000 and d["latency"]["intent"]["n"] == 2
    assert d["per_day"][-1]["rag"] == 2 and len(d["per_day"]) == 30          # zero-filled window
    assert {i["label"] for i in d["top_intents"]} == {"greeting", "thanks"}
    assert d["top_documents"] == [{"label": "Leave Policy", "n": 2}]
    assert {c["label"]: c["n"] for c in d["by_collection"]} == {"All collections": 3, "HR": 3}
    # the same question asked twice (different case/spacing) is grouped, with its count
    assert d["unanswered"][0]["times"] == 2 and "capital of France" in d["unanswered"][0]["question"]
    assert d["disliked"][0]["question"] == "Sick leave rules?" and d["disliked"][0]["comment"] == "too vague"


def test_dashboard_time_window_excludes_old_messages(app):
    with app.app_context():
        conn = db.get_db()
        conn.execute("UPDATE messages SET created_at = datetime('now', '-60 days') WHERE conversation_id = 2")
        conn.commit()
        assert analytics.dashboard(30)["kpis"]["questions"] == 3
        assert analytics.dashboard(90)["kpis"]["questions"] == 6
        assert analytics.dashboard(None)["kpis"]["questions"] == 6


def test_empty_database(tmp_path):
    class Cfg(TestConfig):
        DATA_DIR = tmp_path
        DB_PATH = tmp_path / "e.db"
        UPLOAD_DIR = tmp_path / "u"
        CHROMA_DIR = tmp_path / "c"
        MODEL_DIR = tmp_path / "m"
        ADMIN_PASSWORD = ADMIN_PW

    app = create_app(Cfg)
    with app.app_context():
        d = analytics.dashboard(7)
    assert d["kpis"]["questions"] == 0 and d["kpis"]["rag_rate"] is None and d["per_day"] == []


def test_analytics_api(app):
    admin = app.test_client()
    admin.post("/login", data={"email": "admin@convoai.local", "password": ADMIN_PW})
    assert admin.get("/api/analytics?days=7").status_code == 200
    assert admin.get("/api/analytics?days=0").get_json()["days"] is None
    assert admin.get("/api/analytics?days=13").status_code == 400
    assert admin.get("/admin/analytics").status_code == 200 and admin.get("/admin/metrics").status_code == 200

    riya = app.test_client()
    riya.post("/login", data={"email": "riya@convoai.local", "password": USER_PW})
    assert riya.get("/api/analytics").status_code == 403 and riya.get("/api/metrics").status_code == 403


def test_metrics_api_reads_reports(app):
    admin = app.test_client()
    admin.post("/login", data={"email": "admin@convoai.local", "password": ADMIN_PW})
    m = admin.get("/api/metrics").get_json()
    assert m["intent"] is None and m["rag"] is None and m["thresholds"]["relevance"] == pytest.approx(0.618)

    from nlp.classifier import train_and_activate
    with app.app_context():
        train_and_activate(app)
    (app.config["MODEL_DIR"] / "rag_report.json").write_text(json.dumps({"k": 5, "metrics": {}}), encoding="utf-8")
    m = admin.get("/api/metrics").get_json()
    assert m["intent"]["best"] in ("naive_bayes", "logistic_regression")
    assert "confusion_matrix" in m["intent"]["runs"][0]["details"]["cv"] and m["rag"]["k"] == 5
