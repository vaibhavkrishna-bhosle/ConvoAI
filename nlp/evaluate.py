"""Metrics for the intent classifier: accuracy / precision / recall / F1,
confusion matrix, and the confidence-threshold sweep used by the hybrid router."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             precision_recall_fscore_support)

DOC_QUERY = "doc_query"


def summary(y_true, y_pred) -> dict:
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    return {"accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "precision": round(float(p), 4), "recall": round(float(r), 4), "f1": round(float(f), 4)}


def details(y_true, y_pred, labels: list[str]) -> dict:
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    per_class = {lab: {k: round(float(v), 4) for k, v in report[lab].items()} for lab in labels}
    return {
        "labels": labels,
        "per_class": per_class,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def expected_route(label: str) -> str:
    return "rag" if label == DOC_QUERY else "intent"


def route_for(pred_label: str, confidence: float, threshold: float) -> str:
    """Hybrid router rule: confident small-talk → intent reply, everything else → documents (RAG)."""
    if pred_label != DOC_QUERY and confidence >= threshold:
        return "intent"
    return "rag"


def threshold_sweep(y_true: list[str], pred_labels: list[str], confidences: list[float],
                    thresholds=None) -> list[dict]:
    """For each threshold, how often the router makes the right end-to-end decision.

    Correct = (should go to RAG and does) or (should get an intent reply and gets the *right* one).
    """
    thresholds = thresholds if thresholds is not None else np.round(np.arange(0.05, 0.96, 0.05), 2)
    rows = []
    for t in thresholds:
        correct = wrong_intent = leaked_to_rag = 0
        for truth, pred, conf in zip(y_true, pred_labels, confidences):
            route = route_for(pred, conf, t)
            if route == expected_route(truth) == "rag":
                correct += 1
            elif route == "intent" and pred == truth:
                correct += 1
            elif route == "intent":
                wrong_intent += 1          # answered with the wrong canned reply (bad)
            else:
                leaked_to_rag += 1         # small talk sent to RAG (slower, but RAG can still cope)
        n = len(y_true) or 1
        rows.append({"threshold": float(t), "routing_accuracy": round(correct / n, 4),
                     "wrong_canned_reply": round(wrong_intent / n, 4),
                     "small_talk_to_rag": round(leaked_to_rag / n, 4)})
    return rows


WRONG_REPLY_COST = 2.0   # a wrong canned reply is worse than…
TO_RAG_COST = 1.0        # …sending small talk to the document search (which can still cope)


def routing_cost(row: dict) -> float:
    return WRONG_REPLY_COST * row["wrong_canned_reply"] + TO_RAG_COST * row["small_talk_to_rag"]


MIN_THRESHOLD = 0.25     # safety floor: below this, predictions over 25 classes are close to noise


def best_threshold(sweep: list[dict]) -> float:
    """Lowest weighted routing cost at or above the floor; ties go to the higher (safer) threshold."""
    candidates = [r for r in sweep if r["threshold"] >= MIN_THRESHOLD] or sweep
    best = min(candidates, key=lambda r: (round(routing_cost(r), 6), -r["threshold"]))
    return best["threshold"]
