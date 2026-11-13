"""Phase 7 tests: admin API for collections, users, intents, settings and document rename/move."""
import io

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestConfig
from models import database as db

ADMIN_PW, USER_PW = "test-admin-pw", "test-user-pw"
LEAVE_MD = b"# Leave Policy\n\n## Casual leave\nEmployees get 12 days of casual leave per year.\n"
VPN_MD = b"# VPN Guide\n\n## Connecting\nConnect with GlobalProtect at vpn.example and approve the prompt.\n"


@pytest.fixture()
def app(tmp_path):
    class Cfg(TestConfig):
        DATA_DIR = tmp_path
        DB_PATH = tmp_path / "test.db"
        UPLOAD_DIR = tmp_path / "uploads"
        CHROMA_DIR = tmp_path / "chroma"
        MODEL_DIR = tmp_path / "models"
        ADMIN_PASSWORD = ADMIN_PW
        EMBEDDER = "hash"
        INGEST_SYNC = True

    app = create_app(Cfg)
    with app.app_context():
        conn = db.get_db()
        conn.execute("INSERT INTO users(name, email, password_hash) VALUES ('Riya Sharma', 'riya@convoai.local', ?)",
                     (generate_password_hash(USER_PW),))
        conn.execute("INSERT INTO user_collections VALUES (2, 2)")
        conn.commit()
    return app


def _login(app, email, pw):
    c = app.test_client()
    c.post("/login", data={"email": email, "password": pw})
    return c


@pytest.fixture()
def admin(app):
    return _login(app, "admin@convoai.local", ADMIN_PW)


def _upload(client, cid, name, data):
    return client.post("/api/documents", data={"collection_id": str(cid), "files": (io.BytesIO(data), name)},
                       content_type="multipart/form-data").get_json()["created"][0]


# --------------------------------------------------------------------------- collections
def test_collection_crud(admin):
    r = admin.post("/api/collections", json={"name": "Finance", "description": "Budgets", "icon": "payments", "color": "#386a20"})
    assert r.status_code == 201
    cid = r.get_json()["collection"]["id"]
    assert r.get_json()["collection"]["color"] == "#386A20"
    assert admin.post("/api/collections", json={"name": "finance"}).status_code == 409      # names are case-insensitive
    assert admin.post("/api/collections", json={"name": "X", "icon": "not-an-icon"}).status_code == 400
    assert admin.post("/api/collections", json={"name": ""}).status_code == 400
    assert admin.patch(f"/api/collections/{cid}", json={"name": "Finance & Accounts"}).get_json()["collection"]["name"] == "Finance & Accounts"
    assert admin.delete(f"/api/collections/{cid}").status_code == 200


def test_delete_collection_with_documents_needs_force(admin, app):
    doc = _upload(admin, 4, "vpn.md", VPN_MD)  # Sales
    r = admin.delete("/api/collections/4")
    assert r.status_code == 409 and "1 document" in r.get_json()["error"]
    r = admin.delete("/api/collections/4?force=1")
    assert r.status_code == 200 and r.get_json()["documents_deleted"] == 1
    from rag.store import get_store
    with app.app_context():
        assert db.get_document(doc["id"]) is None and get_store(app).document_chunks(doc["id"]) == []


# --------------------------------------------------------------------------- users
def test_user_crud_and_validation(admin):
    assert admin.post("/api/users", json={"name": "A", "email": "bad", "password": "longenough"}).status_code == 400
    assert admin.post("/api/users", json={"name": "A", "email": "a@x.local", "password": "short"}).status_code == 400
    assert admin.post("/api/users", json={"name": "A", "email": "riya@convoai.local", "password": "longenough"}).status_code == 409
    r = admin.post("/api/users", json={"name": "Kiran Rao", "email": "Kiran@X.local", "password": "longenough",
                                       "collection_ids": [3, 3, 4]})
    assert r.status_code == 201
    user = r.get_json()["user"]
    assert user["email"] == "kiran@x.local" and user["collection_ids"] == [3, 4]
    r = admin.patch(f"/api/users/{user['id']}", json={"collection_ids": [2], "is_active": False})
    assert r.get_json()["user"]["collection_ids"] == [2] and r.get_json()["user"]["is_active"] is False
    assert admin.patch(f"/api/users/{user['id']}", json={"collection_ids": [999]}).status_code == 400
    assert admin.delete(f"/api/users/{user['id']}").status_code == 200


def test_new_password_works(admin, app):
    admin.patch("/api/users/2", json={"password": "brand-new-pass"})
    assert _login(app, "riya@convoai.local", "brand-new-pass").get("/api/me").status_code == 200


def test_admin_safety_rules(admin):
    assert admin.delete("/api/users/1").status_code == 409                          # not yourself
    assert admin.patch("/api/users/1", json={"role": "user"}).status_code == 409     # last admin
    assert admin.patch("/api/users/1", json={"is_active": False}).status_code == 409


def test_admin_api_forbidden_for_users(app):
    riya = _login(app, "riya@convoai.local", USER_PW)
    for method, url in (("get", "/api/users"), ("post", "/api/collections"), ("get", "/api/settings"),
                        ("get", "/api/intents"), ("post", "/api/documents/reindex-all")):
        assert getattr(riya, method)(url).status_code == 403
    for page in ("/admin/collections", "/admin/users", "/admin/settings"):
        assert riya.get(page).status_code == 403


# --------------------------------------------------------------------------- intents
def test_intent_crud_marks_model_dirty(admin, app):
    bad = admin.post("/api/intents", json={"tag": "office_hours", "patterns": "when do you open", "responses": "9 to 6"})
    assert bad.status_code == 400 and "at least 2" in bad.get_json()["error"]
    assert admin.post("/api/intents", json={"tag": "Bad Tag!", "patterns": "a\nb", "responses": "x"}).status_code == 400
    r = admin.post("/api/intents", json={"tag": "office_hours", "description": "Opening hours",
                                         "patterns": "when is the office open\nwhat are office hours\n\nwhat are office hours",
                                         "responses": "The office is open 8 AM to 8 PM, {day} included."})
    assert r.status_code == 201
    intent = r.get_json()["intent"]
    assert intent["patterns"] == ["when is the office open", "what are office hours"]  # blank + duplicate dropped
    assert admin.get("/api/intents").get_json()["dirty"] is True
    assert admin.post("/api/intents", json={"tag": "office_hours", "patterns": "a\nb", "responses": "x"}).status_code == 409

    r = admin.patch(f"/api/intents/{intent['id']}", json={"is_active": False})
    assert r.status_code == 200 and r.get_json()["intent"]["is_active"] is False
    assert admin.delete(f"/api/intents/{intent['id']}").status_code == 200

    from nlp.classifier import train_and_activate
    with app.app_context():
        train_and_activate(app)
    assert admin.get("/api/intents").get_json()["dirty"] is False


def test_doc_query_is_protected(admin):
    dq = next(i for i in admin.get("/api/intents").get_json()["intents"] if i["tag"] == "doc_query")
    assert admin.delete(f"/api/intents/{dq['id']}").status_code == 409
    assert admin.patch(f"/api/intents/{dq['id']}", json={"tag": "questions"}).status_code == 400
    assert admin.patch(f"/api/intents/{dq['id']}", json={"responses": "hello"}).status_code == 400
    assert admin.patch(f"/api/intents/{dq['id']}", json={"is_active": False}).status_code == 400
    ok = admin.patch(f"/api/intents/{dq['id']}", json={"patterns": dq["patterns"] + ["what is the canteen menu"]})
    assert ok.status_code == 200
    assert admin.post("/api/intents", json={"tag": "doc_query", "patterns": "a\nb", "responses": "x"}).status_code in (400, 409)


def test_intent_export(admin):
    r = admin.get("/api/intents/export")
    assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]
    assert any(i["tag"] == "greeting" for i in r.get_json()["intents"])


# --------------------------------------------------------------------------- settings
def test_settings_validation(admin, monkeypatch):
    import routes.admin_api as admin_api
    monkeypatch.setattr(admin_api, "_installed_models", lambda: ["qwen2.5:7b-instruct", "llama3.2:3b", "nomic-embed-text:latest"])

    s = admin.get("/api/settings").get_json()
    assert {f["key"] for f in s["schema"]} >= {"llm_model", "top_k", "relevance_threshold", "whisper_model"}

    assert admin.patch("/api/settings", json={"top_k": "7", "temperature": "0.1"}).get_json()["saved"] == ["temperature", "top_k"]
    assert admin.patch("/api/settings", json={"top_k": "50"}).status_code == 400
    assert admin.patch("/api/settings", json={"temperature": "warm"}).status_code == 400
    assert admin.patch("/api/settings", json={"whisper_model": "huge"}).status_code == 400
    assert admin.patch("/api/settings", json={"chunk_overlap": "900"}).status_code == 400   # ≥ chunk size
    assert admin.patch("/api/settings", json={"relevance_floor": "0.9"}).status_code == 400  # > threshold
    assert admin.patch("/api/settings", json={"secret_key": "x"}).status_code == 400
    r = admin.patch("/api/settings", json={"llm_model": "mistral:7b"})
    assert r.status_code == 400 and "ollama pull mistral:7b" in r.get_json()["error"]
    r = admin.patch("/api/settings", json={"embed_model": "nomic-embed-text"})
    assert r.status_code == 200
    r = admin.patch("/api/settings", json={"chunk_size": "600"})
    assert r.get_json()["needs_reindex"] is True

    r = admin.post("/api/settings/reset").get_json()
    assert "top_k" in r["reset"] and admin.get("/api/settings").get_json()["values"]["top_k"] == "5"


# --------------------------------------------------------------------------- documents: rename / move / reindex-all
def test_move_document_changes_who_can_find_it(admin, app):
    doc = _upload(admin, 3, "VPN Guide.md", VPN_MD)          # IT Support: Riya (HR only) can't see it
    riya = _login(app, "riya@convoai.local", USER_PW)
    with app.app_context():
        db.set_settings({"relevance_threshold": "0.05"})
    first = riya.post("/api/chat", json={"message": "how do I connect with globalprotect to the vpn"}).get_json()
    assert all(s["title"] != "VPN Guide" for s in first["sources"])

    r = admin.patch(f"/api/documents/{doc['id']}", json={"collection_id": 2, "title": "Remote Access Guide"})
    assert r.status_code == 200 and r.get_json()["collection_name"] == "HR" and r.get_json()["title"] == "Remote Access Guide"
    after = riya.post("/api/chat", json={"message": "how do I connect with globalprotect to the vpn"}).get_json()
    assert any(s["title"] == "Remote Access Guide" for s in after["sources"])
    assert admin.patch(f"/api/documents/{doc['id']}", json={"title": "  "}).status_code == 400


def test_reindex_all(admin):
    _upload(admin, 2, "leave.md", LEAVE_MD)
    _upload(admin, 3, "vpn.md", VPN_MD)
    r = admin.post("/api/documents/reindex-all")
    assert r.status_code == 202 and r.get_json()["queued"] == 2
    assert all(d["status"] == "ready" for d in admin.get("/api/documents").get_json()["documents"])


def test_admin_pages_render(admin):
    for page, marker in (("/admin/collections", "collection-grid"), ("/admin/users", "user-rows"),
                         ("/admin/settings", "settings-groups"), ("/admin/intents", "intent-rows"),
                         ("/admin/documents", "edit-dialog")):
        r = admin.get(page)
        assert r.status_code == 200 and marker in r.get_data(as_text=True), page
