"""Admin API (FR-06): collections, users, intents and settings. All endpoints are admin-only.

Collections  GET/POST /api/collections · PATCH/DELETE /api/collections/<id>  (DELETE ?force=1 removes its documents)
Users        GET/POST /api/users · PATCH/DELETE /api/users/<id>
Intents      GET/POST /api/intents · PATCH/DELETE /api/intents/<id> · GET /api/intents/export
Settings     GET/PATCH /api/settings · POST /api/settings/reset
"""
from __future__ import annotations

import json
import re

from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import current_user

from models import database as db
from models.user import admin_required
from nlp.evaluate import DOC_QUERY
from services import ingest
from services.settings_schema import BY_KEY, SCHEMA, SettingsError, validate

bp = Blueprint("admin_api", __name__, url_prefix="/api")

COLLECTION_ICONS = ["folder", "domain", "groups", "computer", "trending_up", "account_balance", "gavel",
                    "health_and_safety", "school", "support_agent", "engineering", "inventory_2", "campaign",
                    "local_shipping", "payments", "policy", "science", "storefront"]
COLLECTION_COLORS = ["#006A6A", "#7A5900", "#3F5F90", "#8F4C38", "#6750A4", "#386A20", "#984061", "#5D5F5F"]
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TAG = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


class AdminError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


@bp.errorhandler(AdminError)
def _admin_error(exc: AdminError):
    return jsonify(error=str(exc)), exc.status


def _body() -> dict:
    return request.get_json(silent=True) or {}


def _text(body: dict, key: str, label: str, max_len: int, required: bool = True) -> str:
    value = (body.get(key) or "").strip()
    if required and not value:
        raise AdminError(f"{label} is required.")
    if len(value) > max_len:
        raise AdminError(f"{label} is too long (max {max_len} characters).")
    return value


# --------------------------------------------------------------------------- collections
def _collection_fields(body: dict, exclude_id: int | None = None) -> dict:
    out = {}
    if "name" in body or exclude_id is None:
        out["name"] = _text(body, "name", "Name", 40)
        if db.collection_name_taken(out["name"], exclude_id):
            raise AdminError(f"A collection named “{out['name']}” already exists.", 409)
    if "description" in body or exclude_id is None:
        out["description"] = _text(body, "description", "Description", 200, required=False)
    if "icon" in body or exclude_id is None:
        out["icon"] = body.get("icon") or "folder"
        if out["icon"] not in COLLECTION_ICONS:
            raise AdminError("Choose one of the listed icons.")
    if "color" in body or exclude_id is None:
        out["color"] = (body.get("color") or COLLECTION_COLORS[0]).upper()
        if not re.fullmatch(r"#[0-9A-F]{6}", out["color"]):
            raise AdminError("Colour must look like #006A6A.")
    return out


@bp.get("/collections")
@admin_required
def collections():
    return jsonify(collections=[dict(c) for c in db.list_collections()], icons=COLLECTION_ICONS, colors=COLLECTION_COLORS)


@bp.post("/collections")
@admin_required
def create_collection():
    cid = db.create_collection(**_collection_fields(_body()))
    return jsonify(collection=dict(db.get_collection(cid))), 201


@bp.patch("/collections/<int:cid>")
@admin_required
def update_collection(cid):
    if db.get_collection(cid) is None:
        raise AdminError("Collection not found.", 404)
    db.update_collection(cid, **_collection_fields(_body(), exclude_id=cid))
    return jsonify(collection=dict(db.get_collection(cid)))


@bp.delete("/collections/<int:cid>")
@admin_required
def delete_collection(cid):
    if db.get_collection(cid) is None:
        raise AdminError("Collection not found.", 404)
    docs = db.list_documents(cid)
    if docs and request.args.get("force") != "1":
        raise AdminError(f"This collection has {len(docs)} document(s). Delete them too?", 409)
    if any(d["status"] == "processing" for d in docs):
        raise AdminError("A document in this collection is still processing. Try again in a moment.", 409)
    if len(db.list_collections()) <= 1:
        raise AdminError("You can't delete the last collection.", 409)
    app = current_app._get_current_object()
    for row in docs:
        ingest.remove_document(app, row)
    db.delete_collection(cid)
    return jsonify(deleted=cid, documents_deleted=len(docs))


# --------------------------------------------------------------------------- users
def _user_fields(body: dict, user_id: int | None = None) -> dict:
    out = {}
    if "name" in body or user_id is None:
        out["name"] = _text(body, "name", "Name", 80)
    if "email" in body or user_id is None:
        out["email"] = _text(body, "email", "Email", 120).lower()
        if not EMAIL.match(out["email"]):
            raise AdminError("Enter a valid email address.")
        if db.email_taken(out["email"], user_id):
            raise AdminError("Another account already uses that email.", 409)
    if "role" in body or user_id is None:
        out["role"] = body.get("role") or "user"
        if out["role"] not in ("admin", "user"):
            raise AdminError("Role must be admin or user.")
    if "password" in body or user_id is None:
        password = body.get("password") or ""
        if (user_id is None or password) and len(password) < 8:
            raise AdminError("Password must be at least 8 characters.")
        out["password"] = password
    if "is_active" in body:
        out["is_active"] = 1 if body["is_active"] else 0
    return out


def _collection_ids(body: dict) -> list[int] | None:
    if "collection_ids" not in body:
        return None
    try:
        ids = sorted({int(x) for x in body["collection_ids"] or []})
    except (TypeError, ValueError):
        raise AdminError("collection_ids must be a list of numbers.")
    valid = {c["id"] for c in db.list_collections()}
    if not set(ids) <= valid:
        raise AdminError("Unknown collection in collection_ids.")
    return ids


@bp.get("/users")
@admin_required
def users():
    return jsonify(users=db.list_users(), me=current_user.id,
                   login_required=current_app.config["LOGIN_REQUIRED"])


@bp.post("/users")
@admin_required
def create_user():
    body = _body()
    fields = _user_fields(body)
    uid = db.create_user(fields["name"], fields["email"], fields["password"], fields["role"])
    ids = _collection_ids(body)
    if ids is not None:
        db.set_user_collections(uid, ids)
    return jsonify(user=next(u for u in db.list_users() if u["id"] == uid)), 201


@bp.patch("/users/<int:uid>")
@admin_required
def update_user(uid):
    if db.get_user_by_id(uid) is None:
        raise AdminError("User not found.", 404)
    body = _body()
    fields = _user_fields(body, uid)
    losing_admin = fields.get("role") == "user" or fields.get("is_active") == 0
    if losing_admin and db.get_user_by_id(uid)["role"] == "admin" and db.active_admin_count(exclude_id=uid) == 0:
        raise AdminError("ConvoAI needs at least one active admin.", 409)
    if uid == current_user.id and losing_admin:
        raise AdminError("You can't remove your own admin access or deactivate yourself.", 409)
    db.update_user(uid, **fields)
    ids = _collection_ids(body)
    if ids is not None:
        db.set_user_collections(uid, ids)
    return jsonify(user=next(u for u in db.list_users() if u["id"] == uid))


@bp.delete("/users/<int:uid>")
@admin_required
def delete_user(uid):
    row = db.get_user_by_id(uid)
    if row is None:
        raise AdminError("User not found.", 404)
    if uid == current_user.id:
        raise AdminError("You can't delete your own account.", 409)
    if row["role"] == "admin" and db.active_admin_count(exclude_id=uid) == 0:
        raise AdminError("ConvoAI needs at least one active admin.", 409)
    db.delete_user(uid)
    return jsonify(deleted=uid)


# --------------------------------------------------------------------------- intents
def _lines(value, label: str, max_items: int = 300, max_len: int = 400) -> list[str]:
    items = value.splitlines() if isinstance(value, str) else (value or [])
    out, seen = [], set()
    for item in items:
        item = str(item).strip()
        if item and item.lower() not in seen:
            if len(item) > max_len:
                raise AdminError(f"Each {label} must be at most {max_len} characters.")
            seen.add(item.lower())
            out.append(item)
    if len(out) > max_items:
        raise AdminError(f"Too many {label}s (max {max_items}).")
    return out


def _intent_payload(body: dict, existing: dict | None) -> dict:
    tag = (body.get("tag") if "tag" in body else (existing or {}).get("tag") or "").strip().lower()
    if not TAG.match(tag):
        raise AdminError("Tag must be 2–41 lowercase letters, digits or underscores, starting with a letter.")
    if db.intent_tag_taken(tag, existing["id"] if existing else None):
        raise AdminError(f"An intent called “{tag}” already exists.", 409)
    patterns = _lines(body.get("patterns", (existing or {}).get("patterns", [])), "pattern")
    responses = _lines(body.get("responses", (existing or {}).get("responses", [])), "response", max_items=30, max_len=1500)
    is_active = bool(body.get("is_active", (existing or {}).get("is_active", True)))
    description = _text({"d": body.get("description", (existing or {}).get("description", ""))}, "d", "Description", 200, False)

    if existing and existing["tag"] == DOC_QUERY:
        if tag != DOC_QUERY or not is_active or responses:
            raise AdminError("doc_query is the routing class that sends questions to the documents: "
                             "you can edit its patterns, but not rename it, deactivate it or give it responses.")
    elif tag == DOC_QUERY:
        raise AdminError("doc_query is reserved.")
    if is_active and len(patterns) < 2:
        raise AdminError("Add at least 2 example patterns (one per line) so the classifier can learn it.")
    if is_active and tag != DOC_QUERY and not responses:
        raise AdminError("Add at least one response.")
    return {"tag": tag, "description": description, "is_active": is_active, "patterns": patterns, "responses": responses}


@bp.get("/intents")
@admin_required
def intents():
    return jsonify(intents=db.load_intents(active_only=False), dirty=db.get_setting("intents_dirty", "0") == "1")


@bp.post("/intents")
@admin_required
def create_intent():
    iid = db.save_intent(None, **_intent_payload(_body(), None))
    return jsonify(intent=db.get_intent(iid)), 201


@bp.patch("/intents/<int:iid>")
@admin_required
def update_intent(iid):
    existing = db.get_intent(iid)
    if existing is None:
        raise AdminError("Intent not found.", 404)
    db.save_intent(iid, **_intent_payload(_body(), existing))
    return jsonify(intent=db.get_intent(iid))


@bp.delete("/intents/<int:iid>")
@admin_required
def delete_intent(iid):
    existing = db.get_intent(iid)
    if existing is None:
        raise AdminError("Intent not found.", 404)
    if existing["tag"] == DOC_QUERY:
        raise AdminError("doc_query can't be deleted: it routes questions to the documents.", 409)
    db.delete_intent(iid)
    return jsonify(deleted=iid)


@bp.get("/intents/export")
@admin_required
def export_intents():
    data = {"version": 1, "intents": [{k: i[k] for k in ("tag", "description", "is_active", "patterns", "responses")}
                                      for i in db.load_intents(active_only=False)]}
    return Response(json.dumps(data, indent=2, ensure_ascii=False), mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=convoai-intents.json"})


# --------------------------------------------------------------------------- settings
def _installed_models() -> list[str] | None:
    from routes.api import _ollama_status

    status = _ollama_status()
    return status.get("models") if status["ok"] else None


@bp.get("/settings")
@admin_required
def settings():
    values = db.get_settings()
    docs = db.list_documents()
    embed = values.get("embed_model")
    stale = [d["id"] for d in docs if d["status"] == "ready" and d["embed_model"] and
             d["embed_model"].split(":")[0] != (embed or "").split(":")[0]]
    return jsonify(schema=SCHEMA, values={s["key"]: values.get(s["key"]) for s in SCHEMA},
                   defaults=current_app.config["DEFAULT_SETTINGS"], installed_models=_installed_models(),
                   stale_documents=len(stale), total_documents=len(docs))


@bp.patch("/settings")
@admin_required
def update_settings():
    body = _body()
    current = db.get_settings()
    changed = {k: v for k, v in body.items() if str(v) != str(current.get(k))}
    try:
        clean = validate(changed, installed_models=_installed_models() if any(
            BY_KEY.get(k, {}).get("type") == "ollama_model" for k in changed) else None, current=current)
    except SettingsError as exc:
        raise AdminError(str(exc))
    db.set_settings(clean)
    needs_reindex = any(BY_KEY[k].get("reindex") for k in clean)
    return jsonify(saved=sorted(clean), needs_reindex=needs_reindex)


@bp.post("/settings/reset")
@admin_required
def reset_settings():
    defaults = {s["key"]: current_app.config["DEFAULT_SETTINGS"][s["key"]] for s in SCHEMA
                if s["key"] in current_app.config["DEFAULT_SETTINGS"]}
    current = db.get_settings()
    db.set_settings(defaults)
    changed = [k for k, v in defaults.items() if current.get(k) != v]
    return jsonify(reset=changed, needs_reindex=any(BY_KEY[k].get("reindex") for k in changed))
