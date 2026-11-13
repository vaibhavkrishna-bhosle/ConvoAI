"""Phase 5 tests: local (no sign-in) mode and the chat page routes."""
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestConfig
from models import database as db


def _app(tmp_path, login_required: bool):
    class Cfg(TestConfig):
        DATA_DIR = tmp_path
        DB_PATH = tmp_path / "test.db"
        UPLOAD_DIR = tmp_path / "uploads"
        CHROMA_DIR = tmp_path / "chroma"
        MODEL_DIR = tmp_path / "models"
        ADMIN_PASSWORD = "test-admin-pw"
        ADMIN_NAME = "Shardul Test"
        LOGIN_REQUIRED = login_required

    return create_app(Cfg)


@pytest.fixture()
def local_app(tmp_path):
    return _app(tmp_path, login_required=False)


def test_local_mode_needs_no_sign_in(local_app):
    client = local_app.test_client()
    page = client.get("/")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Shardul" in html and "Local mode" in html and "Sign out" not in html
    assert client.get("/admin/").status_code == 200           # the local user is the admin
    assert client.get("/api/me").get_json()["role"] == "admin"


def test_local_mode_login_page_redirects(local_app):
    client = local_app.test_client()
    r = client.get("/login?next=/admin/documents")
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin/documents")
    assert client.post("/logout").status_code == 302


def test_login_still_enforced_when_switched_on(tmp_path):
    client = _app(tmp_path, login_required=True).test_client()
    assert client.get("/").status_code == 302
    assert client.get("/api/me").status_code in (302, 401)


def test_chat_page_and_conversation_links(local_app):
    client = local_app.test_client()
    html = client.get("/").get_data(as_text=True)
    for element in ('id="thread"', 'id="composer"', 'id="history-list"', 'id="source-sheet"', "marked.umd.js", "js/chat.js"):
        assert element in html

    with local_app.app_context():
        own = db.create_conversation(1, None, "Leave questions")
        conn = db.get_db()
        conn.execute("INSERT INTO users(name, email, password_hash) VALUES ('Other', 'o@x.local', ?)",
                     (generate_password_hash("pw-other-123"),))
        conn.commit()
        other = db.create_conversation(2, None, "Not yours")

    page = client.get(f"/c/{own}")
    assert page.status_code == 200 and f'data-conversation="{own}"' in page.get_data(as_text=True)
    assert client.get(f"/c/{other}").status_code == 404
    assert client.get("/c/99999").status_code == 404
