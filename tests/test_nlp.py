"""Phase 2 tests: preprocessing, response rendering, router rule, training + API."""
import random
from datetime import datetime

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestConfig
from models import database as db
from nlp import evaluate, responder
from nlp.preprocess import explain, preprocess

ADMIN_PW = "test-admin-pw"
USER_PW = "test-user-pw"


# --------------------------------------------------------------------------- preprocessing
@pytest.mark.parametrize("text, expected", [
    ("Who are you?", "who be you"),
    ("Hiiii there!!", "hi"),
    ("thx u r great", "thank you be great"),
    ("I don't want that", "i do not want"),
    ("What's the leave policy for employees?", "what be leave policy employee"),
])
def test_preprocess(text, expected):
    assert preprocess(text) == expected


def test_preprocess_never_empty():
    assert preprocess("the") == "the"  # only stop-words → keep them rather than return nothing


def test_explain_has_all_stages():
    steps = explain("How do I reset my VPN password?")
    assert steps["tokens"][:3] == ["how", "do", "i"]
    assert "vpn" in steps["lemmas"] and "password" in steps["lemmas"]


# --------------------------------------------------------------------------- responses + router rule
def test_render_placeholders():
    ctx = responder.build_context("Riya Sharma", ["HR", "IT Support"], now=datetime(2026, 11, 10, 9, 5))
    out = responder.render("Hi {name}! It's {time} on {day}, {date}. Search: {collections}. {unknown}", ctx)
    assert out == "Hi Riya! It's 9:05 AM on Tuesday, 10 November 2026. Search: HR, IT Support. {unknown}"


def test_choose_without_responses():
    assert responder.choose([], {}) is None
    assert responder.choose(["a"], {}, random.Random(1)) == "a"


def test_route_rule():
    assert evaluate.route_for("greeting", 0.9, 0.35) == "intent"
    assert evaluate.route_for("greeting", 0.2, 0.35) == "rag"
    assert evaluate.route_for("doc_query", 0.99, 0.35) == "rag"


def test_threshold_sweep_and_floor():
    sweep = evaluate.threshold_sweep(["greeting", "doc_query"], ["greeting", "joke"], [0.9, 0.2],
                                     thresholds=[0.1, 0.3, 0.95])
    assert [r["routing_accuracy"] for r in sweep] == [0.5, 1.0, 0.5]
    assert evaluate.best_threshold(sweep) == 0.3


# --------------------------------------------------------------------------- training + API
@pytest.fixture(scope="module")
def app(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("nlp")

    class Cfg(TestConfig):
        DATA_DIR = tmp
        DB_PATH = tmp / "test.db"
        UPLOAD_DIR = tmp / "uploads"
        CHROMA_DIR = tmp / "chroma"
        MODEL_DIR = tmp / "models"
        ADMIN_PASSWORD = ADMIN_PW

    app = create_app(Cfg)
    with app.app_context():
        conn = db.get_db()
        conn.execute("INSERT INTO users(name, email, password_hash) VALUES (?, ?, ?)",
                     ("Riya Sharma", "riya@convoai.local", generate_password_hash(USER_PW)))
        conn.commit()
    return app


@pytest.fixture(scope="module")
def trained(app):
    from nlp.classifier import train_and_activate
    with app.app_context():
        return train_and_activate(app)


def test_intents_seeded(app):
    with app.app_context():
        tags = {i["tag"] for i in db.load_intents()}
    assert {"greeting", "doc_query", "thanks"} <= tags and len(tags) >= 25


def test_training_meets_target(trained, app):
    best = next(r for r in trained["runs"] if r["algorithm"] == trained["best"])
    assert {r["algorithm"] for r in trained["runs"]} == {"naive_bayes", "logistic_regression"}
    assert best["test"]["f1"] >= 0.85
    assert (app.config["MODEL_DIR"] / "intent_model.joblib").exists()
    with app.app_context():
        assert sum(r["is_active"] for r in db.latest_model_runs()) == 1
        assert float(db.get_setting("intent_threshold")) >= evaluate.MIN_THRESHOLD


def _login(client, email, pw):
    client.post("/login", data={"email": email, "password": pw})


@pytest.mark.parametrize("text, route, intent", [
    ("hello", "intent", "greeting"),
    ("thank you so much!", "intent", "thanks"),
    ("How many casual leaves do I get per year?", "rag", "doc_query"),
    ("how do i connect to the vpn from home", "rag", "doc_query"),
])
def test_predict_api(trained, app, text, route, intent):
    client = app.test_client()
    _login(client, "riya@convoai.local", USER_PW)
    r = client.post("/api/intent/predict", json={"text": text}).get_json()
    assert r["route"] == route and r["intent"] == intent
    assert (r["reply"] is not None) == (route == "intent")
    assert "steps" in r and r["latency_ms"] < 1000  # NFR-01 for the intent path


def test_predict_api_validation(trained, app):
    client = app.test_client()
    _login(client, "riya@convoai.local", USER_PW)
    assert client.post("/api/intent/predict", json={"text": "  "}).status_code == 400


def test_train_api_admin_only(trained, app):
    client = app.test_client()
    _login(client, "riya@convoai.local", USER_PW)
    assert client.post("/api/model/train").status_code == 403
    assert client.get("/api/model/runs").status_code == 403


def test_intents_page(trained, app):
    client = app.test_client()
    _login(client, "admin@convoai.local", ADMIN_PW)
    page = client.get("/admin/intents").get_data(as_text=True)
    assert "Logistic Regression" in page or "Multinomial Naive Bayes" in page
    assert "doc_query" in page
