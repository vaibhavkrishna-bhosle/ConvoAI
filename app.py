"""ConvoAI — Flask application entry point.

Run:  start.bat                                   (Windows: checks Ollama, opens the browser)
 or:  .venv\\Scripts\\python app.py                 (http://127.0.0.1:5000; set FLASK_DEBUG=1 to develop)
"""
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import database
from models.user import login_manager

csrf = CSRFProtect()


def create_app(config_class=Config, background: bool = True) -> Flask:
    """App factory. `background=False` skips the warm-up and ingestion-resume threads
    (used by command-line tools)."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    database.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from routes import admin, admin_api, analytics_api, api, auth, chat, chat_api, documents, speech_api

    for module in (auth, chat, admin, api, documents, chat_api, speech_api, admin_api, analytics_api):
        app.register_blueprint(module.bp)

    # In `flask run --debug` the reloader's parent process only watches files;
    # background work belongs to the child (WERKZEUG_RUN_MAIN=true).
    is_server_process = not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    run_background = background and not app.testing and is_server_process

    from services import ingest
    ingest.init_app(app, resume=run_background)
    if run_background:
        _warm_up_in_background(app)

    if not app.config["LOGIN_REQUIRED"]:
        _enable_local_mode(app)

    @app.context_processor
    def inject_nav():
        return {"app_name": "ConvoAI", "login_required": app.config["LOGIN_REQUIRED"]}

    def _error(code: int, title: str, message: str):
        if request.path.startswith("/api/"):
            return jsonify(error=title), code
        return render_template("error.html", code=code, title=title, message=message), code

    app.register_error_handler(403, lambda e: _error(403, "Access denied",
                                                     "This page is for administrators only."))
    app.register_error_handler(404, lambda e: _error(404, "Page not found",
                                                     "The page you were looking for doesn't exist."))
    app.register_error_handler(413, lambda e: _error(413, "File too large",
                                                     "Uploads are limited to 50 MB per request."))
    return app


def _enable_local_mode(app: Flask) -> None:
    """No sign-in: every request is made as the built-in local admin account."""
    from flask_login import current_user, login_user

    from models.user import User

    @app.before_request
    def auto_login():
        if request.endpoint == "static" or current_user.is_authenticated:
            return
        row = database.get_db().execute(
            "SELECT * FROM users WHERE role = 'admin' AND is_active = 1 ORDER BY id LIMIT 1").fetchone()
        if row is not None:
            login_user(User(row), remember=True)


def _warm_up_in_background(app: Flask) -> None:
    """Load the intent model, NLTK data and the Ollama chat/embedding models off the
    request path, so the first chat message is answered as fast as the rest (NFR-01)."""
    import threading

    from nlp.classifier import MODEL_FILENAME, get_classifier

    def warm():
        with app.app_context():
            try:
                if (Path(app.config["MODEL_DIR"]) / MODEL_FILENAME).exists():
                    get_classifier(app).predict("hello there")
            except Exception:  # never block startup on this
                app.logger.exception("Intent model warm-up failed")
            try:
                from rag.embeddings import get_embedder
                from rag.llm import get_llm
                get_embedder(app).embed_query("warm up")
                get_llm(app).warm_up()
            except Exception as exc:  # Ollama may simply not be running yet
                app.logger.warning("Ollama warm-up skipped: %s", exc)
            try:
                from services.speech import get_transcriber
                get_transcriber(app).warm_up()  # Whisper on the CPU, ~0.5 GB RAM
            except Exception as exc:  # faster-whisper not installed: voice input is simply off
                app.logger.warning("Whisper warm-up skipped: %s", exc)

    threading.Thread(target=warm, name="convoai-warmup", daemon=True).start()


if __name__ == "__main__":
    # Normal runs are not in debug mode (no auto-reloader second process, no interactive debugger).
    # Set FLASK_DEBUG=1 while developing.
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    port = int(os.getenv("PORT", "5000"))
    application = create_app()
    print(f"\n  ConvoAI is running at  http://127.0.0.1:{port}\n  Press Ctrl+C to stop.\n", flush=True)
    application.run(host="127.0.0.1", port=port, debug=debug, threaded=True)
