"""Phase 3 tests: loaders, chunker, store, ingestion pipeline and document API.
Uses the HashEmbedder and synchronous ingestion, so Ollama is not needed."""
import io

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestConfig
from models import database as db
from rag import loaders
from rag.chunker import chunk_sections
from rag.loaders import LoaderError, Section

ADMIN_PW = "test-admin-pw"
USER_PW = "test-user-pw"


# --------------------------------------------------------------------------- loaders
def test_markdown_sections():
    sections, title = loaders.markdown_sections(
        "# Handbook\nIntro text.\n\n## Leave\n**Casual** leave is [12 days](https://x.example).\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    assert title == "Handbook"
    assert [s.heading for s in sections] == ["Handbook", "Leave"]
    assert "Casual leave is 12 days (https://x.example)." in sections[1].text
    assert "1 | 2" in sections[1].text and "---" not in sections[1].text


def test_txt_headings(tmp_path):
    p = tmp_path / "policy.txt"
    p.write_text("SECURITY RULES\nIntro line.\n\n1. PASSWORDS\nUse 12 characters.\n\n2. PHISHING\nReport it.\n")
    doc = loaders.load_txt(p)
    assert [s.heading for s in doc.sections] == ["Security rules", "Passwords", "Phishing"]


def test_docx_headings_and_tables(tmp_path):
    import docx
    d = docx.Document()
    d.add_heading("Pricing", level=1)
    d.add_paragraph("Plans are billed per agent.")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Plan", "Price"
    t.cell(1, 0).text, t.cell(1, 1).text = "Basic", "INR 499"
    d.add_heading("Refunds", level=1)
    d.add_paragraph("30-day money back.")
    p = tmp_path / "guide.docx"
    d.save(p)
    doc = loaders.load_docx(p)
    assert [s.heading for s in doc.sections] == ["Pricing", "Refunds"]
    assert "Basic | INR 499" in doc.sections[0].text


def _make_pdf(path, pages):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(False)  # keep the footer on the same page
    pdf.set_font("Helvetica", size=11)
    for i, body in enumerate(pages, start=1):
        pdf.add_page()
        pdf.cell(0, 8, "ACME Handbook", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 6, body)
        pdf.set_y(-15)
        pdf.cell(0, 8, f"Page {i} of {len(pages)}")
    pdf.output(str(path))


def test_pdf_pages_and_repeated_margins(tmp_path):
    p = tmp_path / "h.pdf"
    _make_pdf(p, ["Casual leave is twelve days.", "Sick leave needs a certificate.",
                  "The VPN portal is vpn.example.", "Refunds are allowed within thirty days."])
    doc = loaders.load_pdf(p)
    assert doc.page_count == 4 and [s.page for s in doc.sections] == [1, 2, 3, 4]
    assert all("ACME Handbook" not in s.text and "Page" not in s.text for s in doc.sections)


def test_pdf_without_text(tmp_path):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(10, 10, 50, 50)  # an image-only page has no extractable text
    p = tmp_path / "scan.pdf"
    pdf.output(str(p))
    with pytest.raises(LoaderError, match="OCR"):
        loaders.load_pdf(p)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "http://127.0.0.1:5000/",
                                 "http://localhost/admin", "http://192.168.1.10/", "not a url"])
def test_validate_url_blocks_unsafe(url):
    with pytest.raises(LoaderError):
        loaders.validate_url(url)


def test_load_url_extracts_article(monkeypatch):
    html = ("<html><head><title>Remote Work Policy</title></head><body><nav>Menu Home About</nav>"
            "<article><h1>Remote Work Policy</h1>" + "<p>Employees may work remotely two days per week "
            "with manager approval and must use the VPN at all times.</p>" * 6 + "</article></body></html>")

    class Raw:
        def read(self, n, decode_content=True):
            return html.encode()

    class Resp:
        url = "https://docs.example.com/remote"
        headers = {"Content-Type": "text/html; charset=utf-8"}
        encoding = "utf-8"
        raw = Raw()

        def raise_for_status(self):
            pass

    import requests
    monkeypatch.setattr(loaders, "validate_url", lambda u: u)
    monkeypatch.setattr(requests, "get", lambda *a, **k: Resp())
    doc = loaders.load_url("https://docs.example.com/remote")
    assert doc.title == "Remote Work Policy"
    assert "two days per week" in " ".join(s.text for s in doc.sections)


# --------------------------------------------------------------------------- chunker
def test_chunker_sizes_overlap_and_pages():
    para = " ".join(f"Sentence number {i} explains a rule." for i in range(60))
    chunks = chunk_sections([Section(para, page=1), Section("Short page two text that is long enough.", page=2)],
                            size=300, overlap=60)
    assert all(len(c.text) <= 300 for c in chunks)
    page1 = [c for c in chunks if c.page == 1]
    assert len(page1) > 3
    assert page1[0].text[-20:].split()[-1] in page1[1].text  # overlap carries text forward
    assert chunks[-1].page == 2 and [c.index for c in chunks] == list(range(len(chunks)))


def test_chunker_rejects_bad_overlap():
    with pytest.raises(ValueError):
        chunk_sections([Section("x" * 100)], size=100, overlap=100)


# --------------------------------------------------------------------------- pipeline + API
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
        conn.execute("INSERT INTO users(name, email, password_hash) VALUES (?, ?, ?)",
                     ("Riya Sharma", "riya@convoai.local", generate_password_hash(USER_PW)))
        conn.commit()
    return app


@pytest.fixture()
def admin(app):
    client = app.test_client()
    client.post("/login", data={"email": "admin@convoai.local", "password": ADMIN_PW})
    return client


LEAVE_MD = (b"# Leave Policy\n\n## Casual leave\nEmployees get 12 days of casual leave per year, "
            b"credited monthly. It lapses on 31 December.\n\n## Sick leave\nEmployees get 10 days of "
            b"sick leave per year. A medical certificate is needed after 2 days.\n")
VPN_TXT = (b"VPN GUIDE\nConnect with GlobalProtect to vpn.example and approve the authenticator prompt. "
           b"If the VPN keeps disconnecting, switch gateway or restart the laptop.\n")


def _upload(client, collection_id, name, data):
    return client.post("/api/documents", data={"collection_id": str(collection_id),
                                               "files": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")


def test_upload_ingest_and_view_chunks(admin):
    r = _upload(admin, 2, "Leave_Policy.md", LEAVE_MD)
    assert r.status_code == 201
    doc = r.get_json()["created"][0]
    assert doc["title"] == "Leave Policy" and doc["collection_name"] == "HR"

    doc = admin.get(f"/api/documents/{doc['id']}").get_json()
    assert doc["status"] == "ready" and doc["progress"] == 100 and doc["chunk_count"] >= 2
    chunks = admin.get(f"/api/documents/{doc['id']}/chunks").get_json()["chunks"]
    assert {c["heading"] for c in chunks} >= {"Casual leave", "Sick leave"}


def test_duplicate_and_unsupported_files_skipped(admin):
    _upload(admin, 2, "leave.md", LEAVE_MD)
    r = _upload(admin, 2, "leave-copy.md", LEAVE_MD)
    assert r.status_code == 400 and "Already in HR" in r.get_json()["skipped"][0]["reason"]
    r = _upload(admin, 2, "photo.png", b"\x89PNG....")
    assert "Unsupported" in r.get_json()["skipped"][0]["reason"]
    assert _upload(admin, 3, "leave.md", LEAVE_MD).status_code == 201  # same file, other collection is fine


def test_broken_file_marked_failed(admin):
    doc = _upload(admin, 2, "broken.pdf", b"%PDF-1.4 not really a pdf").get_json()["created"][0]
    doc = admin.get(f"/api/documents/{doc['id']}").get_json()
    assert doc["status"] == "failed" and doc["error"]


def test_search_respects_collections(admin):
    _upload(admin, 2, "leave.md", LEAVE_MD)       # HR
    _upload(admin, 3, "vpn.txt", VPN_TXT)         # IT Support
    r = admin.get("/api/documents/search?q=casual leave days").get_json()
    assert r["vector"][0]["title"] == "leave" and r["keyword"][0]["title"] == "leave"
    r = admin.get("/api/documents/search?q=casual leave days&collection_id=3").get_json()
    assert all(h["title"] == "vpn" for h in r["vector"] + r["keyword"])


def test_reindex_and_delete(admin, app):
    doc = _upload(admin, 2, "leave.md", LEAVE_MD).get_json()["created"][0]
    assert admin.post(f"/api/documents/{doc['id']}/reindex").status_code == 202
    assert admin.get(f"/api/documents/{doc['id']}").get_json()["status"] == "ready"

    from rag.store import get_store
    with app.app_context():
        path = db.get_document(doc["id"])["path_or_url"]
        assert get_store(app).document_chunks(doc["id"])
    assert admin.delete(f"/api/documents/{doc['id']}").status_code == 200
    with app.app_context():
        assert get_store(app).document_chunks(doc["id"]) == []
    assert admin.get(f"/api/documents/{doc['id']}").status_code == 404
    import os
    assert not os.path.exists(path)


def test_add_url_validation(admin):
    assert admin.post("/api/documents/url", json={"url": "http://localhost/x", "collection_id": 1}).status_code == 400
    assert admin.post("/api/documents/url", json={"url": "https://example.com", "collection_id": 999}).status_code == 400


def test_documents_api_admin_only(app):
    client = app.test_client()
    client.post("/login", data={"email": "riya@convoai.local", "password": USER_PW})
    assert client.get("/api/documents").status_code == 403
    assert _upload(client, 2, "leave.md", LEAVE_MD).status_code == 403
    assert client.get("/admin/documents").status_code == 403


def test_documents_page(admin):
    page = admin.get("/admin/documents").get_data(as_text=True)
    assert "Upload documents" in page and "Test retrieval" in page
