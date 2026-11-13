"""Admin panel pages (the data behind them comes from the JSON APIs in routes/*_api.py)."""
from flask import Blueprint, render_template

from models import database as db
from models.user import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

# endpoint -> (title, icon, what it does): the overview page links to each
SECTIONS = {
    "documents": ("Documents", "description",
                  "Upload PDF, Word, text and Markdown files or web pages; watch indexing; test retrieval."),
    "collections": ("Collections", "folder_shared", "Create and edit department collections such as HR and IT Support."),
    "intents": ("Intents", "psychology", "Edit small-talk intents, try messages and retrain the classifier."),
    "analytics": ("Analytics", "monitoring", "Usage, answer routes, most-cited documents and content gaps."),
    "metrics": ("Model metrics", "query_stats", "Classifier comparison, confusion matrix and retrieval evaluation."),
    "settings": ("Settings", "tune", "Models, thresholds, chunking and voice."),
    "users": ("Users", "manage_accounts", "Accounts and collection access (used when sign-in is switched on)."),
}


@bp.route("/analytics")
@admin_required
def analytics():
    return render_template("admin/analytics.html")


@bp.route("/metrics")
@admin_required
def metrics():
    return render_template("admin/metrics.html")


@bp.route("/collections")
@admin_required
def collections():
    return render_template("admin/collections.html")


@bp.route("/users")
@admin_required
def users():
    from flask import current_app

    return render_template("admin/users.html", collections=db.list_collections(),
                           login_required=current_app.config["LOGIN_REQUIRED"])


@bp.route("/settings")
@admin_required
def settings():
    return render_template("admin/settings.html")


@bp.route("/documents")
@admin_required
def documents():
    from rag.loaders import SUPPORTED_EXTENSIONS

    return render_template("admin/documents.html", collections=db.list_collections(),
                           accept=",".join(SUPPORTED_EXTENSIONS),
                           settings=db.get_settings())


@bp.route("/")
@admin_required
def index():
    return render_template(
        "admin/overview.html",
        counts=db.counts(),
        collections=db.list_collections(),
        settings=db.get_settings(),
        sections=SECTIONS,
    )


@bp.route("/intents")
@admin_required
def intents():
    runs = db.latest_model_runs(limit=20)
    active = next((r for r in runs if r["is_active"]), None)
    compare = [r for r in runs if active and r["trained_at"] == active["trained_at"]]
    return render_template(
        "admin/intents.html",
        intents=db.load_intents(active_only=False),
        active=active,
        compare=compare,
        threshold=db.get_setting("intent_threshold"),
        intents_dirty=db.get_setting("intents_dirty", "0") == "1",
        algorithm_names={"naive_bayes": "Multinomial Naive Bayes", "logistic_regression": "Logistic Regression"},
    )

