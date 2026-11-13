"""Response selection for intent replies (FR-03)."""
from __future__ import annotations

import random
from datetime import datetime
from string import Formatter


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def render(template: str, context: dict) -> str:
    return Formatter().vformat(template, (), _SafeDict(context))


def build_context(user_name: str = "", collections: list[str] | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    names = collections or []
    return {
        "name": (user_name.split()[0] if user_name else "there"),
        "time": now.strftime("%I:%M %p").lstrip("0"),
        "date": now.strftime("%d %B %Y").lstrip("0"),
        "day": now.strftime("%A"),
        "collections": ", ".join(names) if names else "no collections yet",
    }


def choose(responses: list[str], context: dict, rng: random.Random | None = None) -> str | None:
    if not responses:
        return None
    return render((rng or random).choice(responses), context)
