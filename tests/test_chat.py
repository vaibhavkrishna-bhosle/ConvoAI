"""Phase 4 tests: retrieval fusion, prompt helpers, hybrid router, chat/stream/conversation/feedback APIs.
Uses HashEmbedder + EchoLLM (no Ollama needed)."""
import io
import json

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestConfig
from models import database as db
from rag import prompt as P
from rag.retriever import rrf_fuse
from rag.store import Hit

ADMIN_PW, USER_PW, OTHER_PW = "test-admin-pw", "test-user-pw", "test-other-pw"
LEAVE_MD = (b"# Leave Policy\n\n## Casual leave\nEmployees get 12 days of casual leave per year, credited "
            b"monthly. Casual leave lapses on 31 December.\n\n## Sick leave\nEmployees get 10 days of sick "
            b"leave per year. A medical certificate is needed after 2 days.\n")
VPN_MD = (b"# VPN Guide\n\n## Connecting\nConnect to the VPN with GlobalProtect at vpn.example and approve the "
          b"authenticator prompt on your phone.\n")


# --------------------------------------------------------------------------- unit helpers
def _hit(i, score=0.5):
    return Hit(id=f"d:{i}", text=f"text {i}", score=score, doc_id=1, collection_id=1, title="T",
               page=None, heading=None, chunk_index=i)


def test_rrf_prefers_chunks_ranked_by_both():
    fused = rrf_fuse([[_hit(1), _hit(2), _hit(3)], [_hit(3), _hit(4), _hit(1)]])
    assert [h.id for h in fused][:2] == ["d:1", "d:3"]  # both appear in both lists


def test_citation_helpers():
    answer = "You get 12 days [1]. Sick leave is 10 days [3][1]. Bogus [9]."
    assert P.cited_numbers(answer, 3) == [1, 3]
    assert "[9]" not in P.remove_invalid_citations(answer, 3)
    assert P.strip_citations("Twelve days [1][2].") == "Twelve days."


def test_needs_rewrite():
    history = [{"role": "user", "content": "How many casual leaves?"}, {"role": "bot", "content": "12 [1]"}]
    assert P.needs_rewrite("and sick leave?", history)
    assert P.needs_rewrite("what about that for interns", history)
    assert not P.needs_rewrite("How many casual leaves do I get per year at Nimbus?", history)
    assert not P.needs_rewrite("and sick leave?", [])


def test_relevance_gate_grey_zone(monkeypatch):
    """Below the threshold but above the floor, a question passes only if keyword search agrees."""
    from rag import retriever

    class FakeStore:
        def search(self, vec, ids, k):
            return [_hit(1, 0.60), _hit(2, 0.55), _hit(3, 0.50), _hit(4, 0.45)]

    class FakeIndex:
        def __init__(self, top):
            self.top = top

        def search(self, q, k):
            return [_hit(self.top, 1.0)]

    for keyword_top, expected in ((2, True), (4, False)):     # 2 is in the vector top-3, 4 is not
        monkeypatch.setattr(retriever.KeywordIndex, "for_collections", lambda store, ids, t=keyword_top: FakeIndex(t))
        r = retriever.retrieve(FakeStore(), [0.0], "q", [1], threshold=0.618, floor=0.57)
        assert r.relevant is expected and r.keyword_agrees is expected
    r = retriever.retrieve(FakeStore(), [0.0], "q", [1], threshold=0.618, floor=0.61)   # 0.60 is below the floor
    assert r.relevant is False
    r = retriever.retrieve(FakeStore(), [0.0], "q", [1], threshold=0.59)               # above the threshold
    assert r.relevant is True


def test_expand_with_neighbors():
    from rag.retriever import expand_with_neighbors

    class FakeStore:
        def __init__(self):
            self.asked = None

        def chunks_by_ids(self, ids):
            self.asked = ids
            return [Hit(id=i, text=f"n {i}", score=0.0, doc_id=int(i.split(":")[0]), collection_id=1, title="T",
                        page=None, heading=None, chunk_index=int(i.split(":")[1])) for i in ids if not i.endswith(":99")]

    hits = [Hit(id="7:3", text="a", score=0.9, doc_id=7, collection_id=1, title="T", page=None, heading=None, chunk_index=3),
            Hit(id="7:4", text="b", score=0.8, doc_id=7, collection_id=1, title="T", page=None, heading=None, chunk_index=4),
            Hit(id="9:0", text="c", score=0.7, doc_id=9, collection_id=1, title="T", page=None, heading=None, chunk_index=0)]
    store = FakeStore()
    out = expand_with_neighbors(store, hits, top_n=2)
    assert store.asked == ["7:2", "7:5"]                     # no duplicates of hits, no negative index
    assert [h.id for h in out] == ["7:3", "7:4", "9:0", "7:2", "7:5"]  # ranked hits keep their numbers


def test_prompt_numbers_sources():
    msgs = P.build_messages("q?", [_hit(1), _hit(2)])
    assert msgs[0]["role"] == "system" and "[1]" in msgs[-1]["content"] and "[2]" in msgs[-1]["content"]


# --------------------------------------------------------------------------- app fixtures
@pytest.fixture(scope="module")
def app(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("chat")

    class Cfg(TestConfig):
        DATA_DIR = tmp
        DB_PATH = tmp / "test.db"
        UPLOAD_DIR = tmp / "uploads"
        CHROMA_DIR = tmp / "chroma"
        MODEL_DIR = tmp / "models"
        ADMIN_PASSWORD = ADMIN_PW
        EMBEDDER = "hash"
        LLM = "echo"
        INGEST_SYNC = True

    app = create_app(Cfg)
    with app.app_context():
        conn = db.get_db()
        for name, email, pw in (("Riya Sharma", "riya@convoai.local", USER_PW),
                                ("Omar Ali", "omar@convoai.local", OTHER_PW)):
            conn.execute("INSERT INTO users(name, email, password_hash) VALUES (?, ?, ?)",
                         (name, email, generate_password_hash(pw)))
        conn.execute("INSERT INTO user_collections VALUES (2, 2)")  # Riya → HR only; Omar → nothing
        conn.execute("UPDATE settings SET value = '0.1' WHERE key = 'relevance_threshold'")  # hash vectors score low
        conn.commit()
        from nlp.classifier import train_and_activate
        train_and_activate(app)

    admin = app.test_client()
    admin.post("/login", data={"email": "admin@convoai.local", "password": ADMIN_PW})
    for cid, name, data in ((2, "Leave Policy.md", LEAVE_MD), (3, "VPN Guide.md", VPN_MD)):
        r = admin.post("/api/documents", data={"collection_id": str(cid), "files": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")
        assert r.status_code == 201
    return app


def _client(app, email, pw):
    c = app.test_client()
    c.post("/login", data={"email": email, "password": pw})
    return c


@pytest.fixture()
def riya(app):
    return _client(app, "riya@convoai.local", USER_PW)


def _set_threshold(app, value):
    """Set the relevance threshold and keep the grey-zone floor at or below it."""
    with app.app_context():
        db.set_settings({"relevance_threshold": str(value), "relevance_floor": str(value)})


# --------------------------------------------------------------------------- router via /api/chat
def test_small_talk_uses_intent_fast_path(riya):
    r = riya.post("/api/chat", json={"message": "hello"}).get_json()
    assert r["route"] == "intent" and r["intent"] == "greeting" and "Riya" in r["content"]
    assert r["sources"] == [] and r["conversation_id"]


def test_document_question_answered_with_citation(riya):
    r = riya.post("/api/chat", json={"message": "How many days of casual leave do I get per year?"}).get_json()
    assert r["route"] == "rag", r
    assert "[1]" in r["content"] and r["sources"][0]["cited"] is True
    assert r["sources"][0]["title"] == "Leave Policy"
    conv = riya.get(f"/api/conversations/{r['conversation_id']}").get_json()
    bot = conv["messages"][-1]
    assert bot["route"] == "rag" and bot["sources"][0]["cited"] and bot["sources"][0]["text"]


def test_nothing_relevant_gives_fallback(app, riya):
    _set_threshold(app, 0.99)
    try:
        r = riya.post("/api/chat", json={"message": "What is the policy on casual leave carry forward?"}).get_json()
    finally:
        _set_threshold(app, 0.1)
    assert r["route"] == "fallback" and "couldn't find" in r["content"] and r["sources"] == []


def test_access_control_on_collections(riya):
    assert riya.post("/api/chat", json={"message": "how do I connect to the vpn", "collection_id": 3}).status_code == 403
    r = riya.post("/api/chat", json={"message": "how do I connect to the vpn with globalprotect"}).get_json()
    assert all(s["title"] != "VPN Guide" for s in r["sources"])  # IT docs are never shown to an HR-only user


def test_user_without_collections(app):
    omar = _client(app, "omar@convoai.local", OTHER_PW)
    r = omar.post("/api/chat", json={"message": "What is the casual leave policy?"}).get_json()
    assert r["route"] == "fallback" and "don't have access" in r["content"]


def test_follow_up_in_same_conversation(riya):
    first = riya.post("/api/chat", json={"message": "How many days of casual leave per year?"}).get_json()
    second = riya.post("/api/chat", json={"message": "and sick leave?",
                                          "conversation_id": first["conversation_id"]}).get_json()
    assert second["conversation_id"] == first["conversation_id"]
    msgs = riya.get(f"/api/conversations/{first['conversation_id']}").get_json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "bot", "user", "bot"]


def test_validation_errors(riya):
    assert riya.post("/api/chat", json={"message": "   "}).status_code == 400
    assert riya.post("/api/chat", json={"message": "hi", "conversation_id": 99999}).status_code == 404
    assert riya.post("/api/chat", json={"message": "hi", "collection_id": "abc"}).status_code == 400


# --------------------------------------------------------------------------- streaming
def _events(raw: str) -> list[dict]:
    out = []
    for block in raw.strip().split("\n\n"):
        data = [l[6:] for l in block.splitlines() if l.startswith("data: ")]
        if data:
            out.append(json.loads(data[0]))
    return out


def test_stream_event_order(riya):
    r = riya.post("/api/chat/stream", json={"message": "How many days of sick leave per year?"})
    assert r.status_code == 200 and r.mimetype == "text/event-stream"
    types = [e["type"] for e in _events(r.get_data(as_text=True))]
    assert types[0] == "start" and types[-1] == "done"
    assert "sources" in types and "token" in types
    assert types.index("sources") < types.index("token")


def test_stream_validation_is_plain_json(riya):
    r = riya.post("/api/chat/stream", json={"message": ""})
    assert r.status_code == 400 and r.is_json


# --------------------------------------------------------------------------- conversations + feedback
def test_conversation_crud_and_ownership(app, riya):
    cid = riya.post("/api/chat", json={"message": "hi there"}).get_json()["conversation_id"]
    assert any(c["id"] == cid for c in riya.get("/api/conversations").get_json()["conversations"])
    assert riya.patch(f"/api/conversations/{cid}", json={"title": "Greetings"}).get_json()["conversation"]["title"] == "Greetings"

    omar = _client(app, "omar@convoai.local", OTHER_PW)
    assert omar.get(f"/api/conversations/{cid}").status_code == 404
    assert omar.delete(f"/api/conversations/{cid}").status_code == 404

    assert riya.delete(f"/api/conversations/{cid}").status_code == 200
    assert riya.get(f"/api/conversations/{cid}").status_code == 404


def test_feedback(app, riya):
    r = riya.post("/api/chat", json={"message": "How many days of casual leave per year?"}).get_json()
    mid = r["message_id"]
    assert riya.post(f"/api/messages/{mid}/feedback", json={"rating": 1}).status_code == 200
    assert riya.post(f"/api/messages/{mid}/feedback", json={"rating": -1, "comment": "too short"}).status_code == 200
    msgs = riya.get(f"/api/conversations/{r['conversation_id']}").get_json()["messages"]
    assert msgs[-1]["feedback"] == -1
    assert riya.post(f"/api/messages/{mid}/feedback", json={"rating": 0}).status_code == 200
    assert riya.post(f"/api/messages/{mid}/feedback", json={"rating": 5}).status_code == 400
    user_msg_id = msgs[0]["id"]
    assert riya.post(f"/api/messages/{user_msg_id}/feedback", json={"rating": 1}).status_code == 400
    omar = _client(app, "omar@convoai.local", OTHER_PW)
    assert omar.post(f"/api/messages/{mid}/feedback", json={"rating": 1}).status_code == 404


def test_stopped_answer_is_saved(app):
    """Closing the stream mid-answer (Stop button) saves the partial answer, marked as stopped."""
    from models.user import User
    from services import router

    with app.test_request_context():
        user = User(db.get_user_by_email("riya@convoai.local"))
        req = router.prepare(user, "How many days of casual leave do I get per year?", None, None)
        stream = router.handle(user, req)
        cid = None
        for event in stream:
            if event["type"] == "start":
                cid = event["conversation_id"]
            if event["type"] == "token":
                break
        stream.close()  # what the server does when the browser stops reading
        msgs = db.conversation_messages(cid)
    assert [m["role"] for m in msgs] == ["user", "bot"]
    assert msgs[-1]["content"].endswith("_(Stopped.)_") and msgs[-1]["sources"]


def test_chat_requires_login(app):
    assert app.test_client().post("/api/chat", json={"message": "hi"}).status_code in (302, 401)
