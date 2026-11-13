"""Flask-Login user model and role helpers."""
from __future__ import annotations

from functools import wraps

from flask import abort
from flask_login import LoginManager, UserMixin, current_user

from models import database as db

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "info"


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.email = row["email"]
        self.role = row["role"]
        self.theme = row["theme"]
        self._active = bool(row["is_active"])

    @property
    def is_active(self) -> bool:  # Flask-Login hook
        return self._active

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def initials(self) -> str:
        parts = [p for p in self.name.split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"


@login_manager.user_loader
def load_user(user_id: str):
    row = db.get_user_by_id(int(user_id))
    return User(row) if row else None


def admin_required(view):
    """Allow only signed-in admins; 403 for regular users."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapper
