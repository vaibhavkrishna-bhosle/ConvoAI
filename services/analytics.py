"""Usage analytics (FR-07) computed straight from the chat history in SQLite.

Every figure comes from real messages: nothing is sampled or estimated. Days are
grouped in this computer's local time.
"""
from __future__ import annotations

from datetime import date, timedelta

from models import database as db

ROUTES = ("rag", "intent", "fallback")


def _since(days: int | None) -> tuple[str, tuple]:
    """SQL fragment + params limiting messages to the last `days` days (None = all time)."""
    if not days:
        return "1 = 1", ()
    return "m.created_at >= datetime('now', ?)", (f"-{int(days)} days",)


def _percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return int(values[lo] + (values[hi] - values[lo]) * (k - lo))


def dashboard(days: int | None = 30) -> dict:
    conn = db.get_db()
    where, params = _since(days)

    def q(sql: str, extra: tuple = ()):
        return conn.execute(sql, params + extra).fetchall()

    # --- headline numbers
    questions = q(f"SELECT COUNT(*) FROM messages m WHERE m.role = 'user' AND {where}")[0][0]
    by_route = {r["route"]: r["n"] for r in q(
        f"SELECT m.route, COUNT(*) AS n FROM messages m WHERE m.role = 'bot' AND m.route IS NOT NULL AND {where} "
        "GROUP BY m.route")}
    answered = sum(by_route.get(r, 0) for r in ROUTES)
    conversations = q(f"SELECT COUNT(DISTINCT m.conversation_id) FROM messages m WHERE {where}")[0][0]
    users = q(f"""SELECT COUNT(DISTINCT c.user_id) FROM messages m JOIN conversations c ON c.id = m.conversation_id
                  WHERE {where}""")[0][0]
    fb = {r["rating"]: r["n"] for r in q(
        f"""SELECT f.rating, COUNT(*) AS n FROM feedback f JOIN messages m ON m.id = f.message_id
            WHERE {where} GROUP BY f.rating""")}

    latencies: dict[str, list[int]] = {r: [] for r in ROUTES}
    for r in q(f"SELECT m.route, m.latency_ms FROM messages m WHERE m.role = 'bot' AND m.latency_ms IS NOT NULL AND {where}"):
        if r["route"] in latencies:
            latencies[r["route"]].append(r["latency_ms"])
    latency = {route: {"median_ms": _percentile(v, 0.5), "p90_ms": _percentile(v, 0.9), "n": len(v)}
               for route, v in latencies.items()}

    # --- per day, by route (zero-filled so gaps show as gaps, not as missing days)
    per_day_rows = q(f"""SELECT date(m.created_at, 'localtime') AS day, m.route, COUNT(*) AS n FROM messages m
                         WHERE m.role = 'bot' AND m.route IS NOT NULL AND {where}
                         GROUP BY day, m.route ORDER BY day""")
    counts: dict[str, dict[str, int]] = {}
    for r in per_day_rows:
        counts.setdefault(r["day"], {})[r["route"]] = r["n"]
    if counts:
        first = date.fromisoformat(min(counts)) if not days else date.today() - timedelta(days=int(days) - 1)
        span = (date.today() - first).days + 1
        day_list = [(first + timedelta(d)).isoformat() for d in range(max(span, 1))]
    else:
        day_list = []
    per_day = [{"day": d, **{route: counts.get(d, {}).get(route, 0) for route in ROUTES}} for d in day_list]

    # --- rankings
    top_intents = [dict(r) for r in q(
        f"""SELECT m.intent_tag AS label, COUNT(*) AS n FROM messages m
            WHERE m.role = 'bot' AND m.route = 'intent' AND m.intent_tag IS NOT NULL AND {where}
            GROUP BY m.intent_tag ORDER BY n DESC, label LIMIT 10""")]
    top_documents = [dict(r) for r in q(
        f"""SELECT COALESCE(d.title, s.title) AS label, COUNT(DISTINCT s.message_id) AS n
            FROM message_sources s JOIN messages m ON m.id = s.message_id
            LEFT JOIN documents d ON d.id = s.document_id
            WHERE s.cited = 1 AND {where}
            GROUP BY COALESCE(s.document_id, s.title) ORDER BY n DESC, label LIMIT 10""")]
    by_collection = [dict(r) for r in q(
        f"""SELECT COALESCE(col.name, 'All collections') AS label, COUNT(*) AS n
            FROM messages m JOIN conversations c ON c.id = m.conversation_id
            LEFT JOIN collections col ON col.id = c.collection_id
            WHERE m.role = 'user' AND {where}
            GROUP BY label ORDER BY n DESC""")]

    # --- questions the documents couldn't answer (each fallback paired with the question before it)
    unanswered_rows = q(f"""
        SELECT u.content AS question, MAX(m.created_at) AS last_asked, COUNT(*) AS times
        FROM messages m
        JOIN messages u ON u.id = (SELECT MAX(id) FROM messages WHERE conversation_id = m.conversation_id
                                   AND role = 'user' AND id < m.id)
        WHERE m.role = 'bot' AND m.route = 'fallback' AND {where}
        GROUP BY lower(trim(u.content)) ORDER BY times DESC, last_asked DESC LIMIT 25""")
    unanswered = [dict(r) for r in unanswered_rows]

    disliked = [dict(r) for r in q(f"""
        SELECT u.content AS question, m.content AS answer, f.comment, f.created_at, m.conversation_id
        FROM feedback f JOIN messages m ON m.id = f.message_id
        JOIN messages u ON u.id = (SELECT MAX(id) FROM messages WHERE conversation_id = m.conversation_id
                                   AND role = 'user' AND id < m.id)
        WHERE f.rating = -1 AND {where}
        ORDER BY f.created_at DESC LIMIT 25""")]

    rated = fb.get(1, 0) + fb.get(-1, 0)
    return {
        "days": days,
        "kpis": {
            "questions": questions,
            "conversations": conversations,
            "users": users,
            "answered": answered,
            "rag_rate": round(by_route.get("rag", 0) / answered, 4) if answered else None,
            "fallback_rate": round(by_route.get("fallback", 0) / answered, 4) if answered else None,
            "thumbs_up": fb.get(1, 0),
            "thumbs_down": fb.get(-1, 0),
            "satisfaction": round(fb.get(1, 0) / rated, 4) if rated else None,
        },
        "routes": {route: by_route.get(route, 0) for route in ROUTES},
        "latency": latency,
        "per_day": per_day,
        "top_intents": top_intents,
        "top_documents": top_documents,
        "by_collection": by_collection,
        "unanswered": unanswered,
        "disliked": disliked,
    }
