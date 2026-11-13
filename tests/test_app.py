"""Phase 0–1 tests: app factory, schema/seed, auth, roles, theme API, health."""
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestConfig
from models import database as db

ADMIN_PW = "test-admin-pw"
USER_PW = "test-user-pw"


@pytest.fixture()
def app(tmp_path):
    class Cfg(TestConfig):
        DATA_DIR = tmp_path
        DB_PATH = tmp_path / "test.db"
        UPLOAD_DIR = tmp_path / "uploads"
        CHROMA_DIR = tmp_path / "chroma"
        MODEL_DIR = tmp_path / "models"
        ADMIN_PASSWORD = ADMIN_PW
        OLLAMA_HOST = "http://127.0.0.1:9"  # nothing listens here

    app = create_app(Cfg)
    with app.app_context():
        conn = db.get_db()
        conn.execute(
            "INSERT INTO users(name, email, password_hash, role) VALUES (?, ?, ?, 'user')",
            ("Riya Sharma", "riya@convoai.local", generate_password_hash(USER_PW)),
        )
        conn.execute("INSERT INTO user_collections VALUES (2, 2)")  # HR only
        conn.commit()
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password})


def test_schema_seeded(app):
    with app.app_context():
        c = db.counts()
        assert c["users"] == 2 and c["collections"] == 4
        assert db.get_setting("llm_model") == "qwen2.5:7b-instruct"


def test_requires_login(client):
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_bad_password(client):
    r = login(client, "admin@convoai.local", "wrong")
    assert r.status_code == 200 and b"Incorrect email or password" in r.data


def test_admin_login_and_admin_pages(client):
    r = login(client, "admin@convoai.local", ADMIN_PW)
    assert r.status_code == 302
    assert client.get("/").status_code == 200
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/documents").status_code == 200


def test_user_blocked_from_admin_and_sees_own_collections(client):
    login(client, "riya@convoai.local", USER_PW)
    assert client.get("/admin/").status_code == 403
    page = client.get("/").get_data(as_text=True)
    assert 'label="HR"' in page and 'label="Sales"' not in page


def test_open_redirect_blocked(client):
    r = client.post("/login?next=https://evil.example", data={"email": "admin@convoai.local", "password": ADMIN_PW})
    assert r.headers["Location"] == "/"


def test_theme_api(client):
    login(client, "riya@convoai.local", USER_PW)
    assert client.post("/api/me/theme", json={"theme": "dark"}).status_code == 200
    assert client.get("/api/me").get_json()["theme"] == "dark"
    assert client.post("/api/me/theme", json={"theme": "pink"}).status_code == 400


def test_logout(client):
    login(client, "admin@convoai.local", ADMIN_PW)
    client.post("/logout")
    assert client.get("/").status_code == 302


def test_health_reports_ollama_down(client):
    h = client.get("/api/health").get_json()
    assert h["database"]["ok"] is True
    assert h["ollama"]["ok"] is False and h["status"] == "degraded"
