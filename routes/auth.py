"""Sign-in / sign-out."""
from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from models import database as db
from models.user import User

bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> str:
    """Only allow relative redirects (prevents open-redirects via ?next=)."""
    if target:
        parts = urlsplit(target)
        if not parts.scheme and not parts.netloc and target.startswith("/"):
            return target
    return url_for("chat.index")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated or not current_app.config["LOGIN_REQUIRED"]:
        return redirect(_safe_next(request.args.get("next")))

    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        row = db.get_user_by_email(email) if email else None

        if row and row["is_active"] and check_password_hash(row["password_hash"], password):
            login_user(User(row), remember=bool(request.form.get("remember")))
            db.touch_last_login(row["id"])
            return redirect(_safe_next(request.args.get("next")))
        flash("Incorrect email or password.", "error")

    return render_template("login.html", email=email)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    if not current_app.config["LOGIN_REQUIRED"]:
        return redirect(url_for("chat.index"))  # nothing to sign out of in local mode
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
