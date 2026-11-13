"""Intent fast-path: classify a message, decide the route, and pick a reply.

The full hybrid router (phase 4) calls `classify()` first; a `route` of "rag"
hands the message to document retrieval.
"""
from __future__ import annotations

import time

from flask import current_app

from models import database as db
from nlp import responder
from nlp.classifier import get_classifier
from nlp.evaluate import route_for
from nlp.preprocess import explain


def classify(text: str, user_name: str = "", collections: list[str] | None = None,
             with_steps: bool = False) -> dict:
    start = time.perf_counter()
    prediction = get_classifier(current_app).predict(text)
    threshold = float(db.get_setting("intent_threshold", "0.35"))
    route = route_for(prediction["intent"], prediction["confidence"], threshold)

    reply = None
    if route == "intent":
        ctx = responder.build_context(user_name, collections)
        reply = responder.choose(db.get_responses(prediction["intent"]), ctx)
        if reply is None:  # intent with no responses configured → let documents answer
            route = "rag"

    result = {**prediction, "threshold": threshold, "route": route, "reply": reply,
              "latency_ms": round((time.perf_counter() - start) * 1000, 1)}
    if with_steps:
        result["steps"] = explain(text)
    return result
