"""Capture the screenshots in docs/screenshots/ for the README and user manual.

    .venv\\Scripts\\pip install playwright          (dev only; drives the installed Microsoft Edge)
    .venv\\Scripts\\python tools/take_screenshots.py

Runs ConvoAI on temporary copies of the database, so the real chat history is never changed:
  * admin pages use a full copy (Analytics shows real usage),
  * chat pages use a copy with the history cleared, then ask demo questions through the UI.
Ollama must be running (the demo questions are answered for real).
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
PY = ROOT / ".venv" / "Scripts" / "python.exe"


def start_server(db_path: Path, port: int) -> subprocess.Popen:
    env = {**os.environ, "CONVOAI_DB": str(db_path), "PORT": str(port), "FLASK_DEBUG": "0"}
    proc = subprocess.Popen([str(PY), "app.py"], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(120):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1)
            time.sleep(4)  # let the warm-up thread load the models
            return proc
        except OSError:
            time.sleep(0.5)
    proc.kill()
    sys.exit("ConvoAI did not start")


def settle(page, ms=900):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


def shot(page, name, full=False):
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print("  saved", name)


def ask(page, question):
    before = page.locator(".msg.bot .route-pill").count()
    page.fill("#message", question)
    page.press("#message", "Enter")
    page.wait_for_function(f"document.querySelectorAll('.msg.bot .route-pill').length > {before}", timeout=90_000)
    page.wait_for_timeout(600)


def main() -> None:
    from playwright.sync_api import sync_playwright

    tmp = Path(tempfile.mkdtemp(prefix="convoai-shots-"))
    full_db, chat_db = tmp / "full.db", tmp / "chat.db"
    shutil.copy(ROOT / "data" / "convoai.db", full_db)
    shutil.copy(ROOT / "data" / "convoai.db", chat_db)
    with sqlite3.connect(chat_db) as conn:          # a clean chat history for the chat screenshots
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM conversations")
        conn.execute("UPDATE users SET theme = 'system'")
    with sqlite3.connect(full_db) as conn:
        conn.execute("UPDATE users SET theme = 'system'")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge")
        desktop = dict(viewport={"width": 1440, "height": 900}, device_scale_factor=1)

        # ---------------------------------------------------------------- chat (clean history)
        server = start_server(chat_db, 5077)
        try:
            base = "http://127.0.0.1:5077"
            for scheme in ("light", "dark"):
                ctx = browser.new_context(**desktop, color_scheme=scheme)
                page = ctx.new_page()
                page.goto(base + "/")
                settle(page)
                if scheme == "light":
                    shot(page, "01-chat-home")
                    ask(page, "How many casual leaves do I get per year?")
                    ask(page, "and can I carry them forward?")
                    shot(page, "02-chat-answer")
                    page.locator(".msg.bot .source-chip").last.click()
                    page.wait_for_selector("#source-sheet:not([hidden])")
                    page.wait_for_timeout(500)
                    shot(page, "03-sources-panel")
                    page.keyboard.press("Escape")
                    ask(page, "What is the capital of France?")
                    ask(page, "thanks!")
                    shot(page, "04-routes")
                else:
                    page.goto(base + "/")
                    settle(page)
                    ask(page, "How do I connect to the VPN from home?")
                    shot(page, "05-chat-dark")
                ctx.close()

            ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                      color_scheme="dark", is_mobile=True, has_touch=True)
            page = ctx.new_page()
            page.goto(base + "/")
            settle(page)
            ask(page, "What discount can I offer on annual plans?")
            shot(page, "06-mobile-chat")
            ctx.close()
        finally:
            server.terminate()
            server.wait(10)

        # ---------------------------------------------------------------- admin (full copy)
        server = start_server(full_db, 5078)
        try:
            base = "http://127.0.0.1:5078"
            ctx = browser.new_context(**desktop, color_scheme="light")
            page = ctx.new_page()
            for path, name, full in (("/admin/", "07-admin-overview", False),
                                     ("/admin/documents", "08-documents", False),
                                     ("/admin/collections", "09-collections", False),
                                     ("/admin/intents", "10-intents", False),
                                     ("/admin/analytics", "11-analytics", True),
                                     ("/admin/metrics", "12-metrics", True),
                                     ("/admin/settings", "13-settings", True)):
                page.goto(base + path)
                settle(page, 1500)
                shot(page, name, full=full)

            # retrieval test panel and chunk viewer on the Documents page
            page.goto(base + "/admin/documents")
            settle(page)
            page.fill("#search-q", "who approves discounts above 20 percent")
            page.press("#search-q", "Enter")
            page.wait_for_selector("#search-results:not([hidden])")
            page.wait_for_timeout(500)
            shot(page, "14-test-retrieval")
            ctx.close()
        finally:
            server.terminate()
            server.wait(10)
        browser.close()
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"Screenshots in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
