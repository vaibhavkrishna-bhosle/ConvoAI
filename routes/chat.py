"""Chat UI pages. `/c/<id>` opens a saved conversation (a shareable, reload-safe link)."""
from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from models import database as db

bp = Blueprint("chat", __name__)


def _render(conversation_id=None):
    collections = db.collections_for_user(current_user.id, current_user.is_admin)
    return render_template("chat.html", collections=collections, conversation_id=conversation_id)


@bp.route("/")
@login_required
def index():
    return _render()


@bp.route("/c/<int:conversation_id>")
@login_required
def conversation(conversation_id):
    if db.get_conversation(conversation_id, current_user.id) is None:
        abort(404)
    return _render(conversation_id)
