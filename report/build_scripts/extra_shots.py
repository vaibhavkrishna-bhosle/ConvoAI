"""Extra light-theme screenshots for the project report (runs on DB copies)."""
import os, shutil, sqlite3, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
ROOT = Path(r"D:/MCA Projects/2026/ConvoAI")
OUT = ROOT / "report" / "screenshots"
PY = ROOT / ".venv" / "Scripts" / "python.exe"

def start(db, port, extra=None):
    env = {**os.environ, "CONVOAI_DB": str(db), "PORT": str(port), "FLASK_DEBUG": "0", **(extra or {})}
    p = subprocess.Popen([str(PY), "app.py"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(160):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1); time.sleep(4); return p
        except OSError: time.sleep(0.5)
    p.kill(); sys.exit("no start")

def settle(page, ms=900):
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(ms)

def shot(page, name, full=False):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full); print("saved", name, flush=True)

def ask(page, q):
    before = page.locator(".msg.bot .route-pill").count()
    page.fill("#message", q); page.press("#message", "Enter")
    page.wait_for_function(f"document.querySelectorAll('.msg.bot .route-pill').length > {before}", timeout=120_000)
    page.wait_for_timeout(700)

from playwright.sync_api import sync_playwright
tmp = Path(tempfile.mkdtemp(prefix="convoai-rep-"))
chat_db, full_db = tmp / "chat.db", tmp / "full.db"
for d in (chat_db, full_db): shutil.copy(ROOT / "data" / "convoai.db", d)
with sqlite3.connect(chat_db) as c:
    c.execute("PRAGMA foreign_keys = ON"); c.execute("DELETE FROM conversations"); c.execute("UPDATE users SET theme='light'")
with sqlite3.connect(full_db) as c:
    c.execute("UPDATE users SET theme='light'")
which = sys.argv[1:] or ["chat", "admin", "login"]
with sync_playwright() as pw:
    br = pw.chromium.launch(channel="msedge")
    desk = dict(viewport={"width": 1440, "height": 900}, device_scale_factor=1, color_scheme="light")
    if "chat" in which:
        s = start(chat_db, 5081)
        try:
            b = "http://127.0.0.1:5081"
            ctx = br.new_context(**desk); pg = ctx.new_page(); pg.goto(b + "/"); settle(pg)
            ask(pg, "How do I connect to the VPN from home?")
            shot(pg, "15-chat-vpn-light")
            ask(pg, "What is the reimbursement limit for hotel stays in metro cities?")
            shot(pg, "16-chat-travel")
            ctx.close()
            ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="light",
                                 is_mobile=True, has_touch=True)
            pg = ctx.new_page(); pg.goto(b + "/"); settle(pg)
            ask(pg, "What discount can I offer on annual plans?")
            shot(pg, "17-mobile-light")
            ctx.close()
        finally:
            s.terminate(); s.wait(10)
    if "admin" in which:
        s = start(full_db, 5082)
        try:
            b = "http://127.0.0.1:5082"
            ctx = br.new_context(**desk); pg = ctx.new_page()
            pg.goto(b + "/admin/documents"); settle(pg)
            pg.locator('md-icon-button[data-act="chunks"]:not([disabled])').first.click()
            pg.wait_for_timeout(1500); shot(pg, "18-chunk-viewer")
            pg.goto(b + "/admin/intents"); settle(pg)
            pg.fill("#try-text", "hey, how are you doing?"); pg.press("#try-text", "Enter"); pg.wait_for_timeout(1500)
            shot(pg, "19-intent-try")
            pg.locator("tr[data-id]").first.click(); pg.wait_for_timeout(1500)
            shot(pg, "20-intent-editor")
            pg.goto(b + "/admin/users"); settle(pg); shot(pg, "21-users")
            ctx.close()
        finally:
            s.terminate(); s.wait(10)
    if "login" in which:
        s = start(full_db, 5083, {"LOGIN_REQUIRED": "1"})
        try:
            ctx = br.new_context(**desk); pg = ctx.new_page()
            pg.goto("http://127.0.0.1:5083/login"); settle(pg); shot(pg, "22-login")
            ctx.close()
        finally:
            s.terminate(); s.wait(10)
    br.close()
