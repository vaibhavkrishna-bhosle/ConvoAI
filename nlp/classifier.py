"""Intent classification (synopsis §4.2, FR-02).

Features : TF-IDF word uni/bi-grams + TF-IDF character 2–4-grams (robust to typos)
Models   : Multinomial Naive Bayes vs Logistic Regression, tuned with grid search and
           compared with stratified 5-fold cross-validation + a held-out test set.
The better model (macro-F1) is saved with joblib (pickle-based) and used for prediction.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline

from nlp import evaluate
from nlp.evaluate import DOC_QUERY
from nlp.preprocess import preprocess

MODEL_FILENAME = "intent_model.joblib"
REPORT_FILENAME = "intent_report.json"
ALGORITHMS = {
    "naive_bayes": "Multinomial Naive Bayes",
    "logistic_regression": "Logistic Regression",
}
PARAM_GRIDS = {
    "naive_bayes": {"clf__alpha": [0.01, 0.05, 0.1, 0.3, 0.5, 1.0]},
    "logistic_regression": {"clf__C": [1, 5, 10, 30, 100]},
}
RANDOM_STATE = 42


def build_pipeline(algorithm: str) -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
                                 token_pattern=r"(?u)\b\w+\b")),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)),
    ])
    if algorithm == "naive_bayes":
        clf = MultinomialNB()
    elif algorithm == "logistic_regression":
        clf = LogisticRegression(max_iter=5000, class_weight="balanced", random_state=RANDOM_STATE)
    else:
        raise ValueError(f"unknown algorithm: {algorithm}")
    return Pipeline([("features", features), ("clf", clf)])


def dataset(intents: list[dict]) -> tuple[list[str], list[str], list[str]]:
    """(raw texts, preprocessed texts, labels) from intents with ≥2 patterns."""
    raw, labels = [], []
    for it in intents:
        if len(it["patterns"]) >= 2:
            raw.extend(it["patterns"])
            labels.extend([it["tag"]] * len(it["patterns"]))
    return raw, [preprocess(t) for t in raw], labels


# --------------------------------------------------------------------------- training
def train(intents: list[dict], test_samples: list[tuple[str, str]] | None = None, folds: int = 5) -> dict:
    """Train + compare all algorithms. Returns {'best': algo, 'runs': [...], 'model': bundle}."""
    _, X, y = dataset(intents)
    labels = sorted(set(y))
    min_count = min(y.count(lab) for lab in labels)
    cv = StratifiedKFold(n_splits=max(2, min(folds, min_count)), shuffle=True, random_state=RANDOM_STATE)

    test = [(t, lab) for t, lab in (test_samples or []) if lab in labels]
    X_test = [preprocess(t) for t, _ in test]
    y_test = [lab for _, lab in test]

    runs, fitted = [], {}
    for algo in ALGORITHMS:
        search = GridSearchCV(build_pipeline(algo), PARAM_GRIDS[algo], cv=cv, scoring="f1_macro", n_jobs=-1)
        search.fit(X, y)
        best_params = {k.replace("clf__", ""): v for k, v in search.best_params_.items()}
        cv_pred = cross_val_predict(search.best_estimator_, X, y, cv=cv, n_jobs=-1)
        run = {
            "algorithm": algo,
            "name": ALGORITHMS[algo],
            "params": best_params,
            "n_samples": len(X),
            "n_intents": len(labels),
            "cv": evaluate.summary(y, cv_pred),
            "details": {"cv": evaluate.details(y, cv_pred, labels)},
            "test": None,
        }
        model = search.best_estimator_  # refit on all patterns
        if X_test:
            proba = model.predict_proba(X_test)
            pred = [model.classes_[i] for i in proba.argmax(axis=1)]
            conf = proba.max(axis=1).tolist()
            sweep = evaluate.threshold_sweep(y_test, pred, conf)
            run["test"] = evaluate.summary(y_test, pred)
            run["test"]["n"] = len(y_test)
            run["details"]["test"] = evaluate.details(y_test, pred, labels)
            run["details"]["threshold_sweep"] = sweep
            run["details"]["recommended_threshold"] = evaluate.best_threshold(sweep)
            run["details"]["test_errors"] = [
                {"text": t, "expected": e, "predicted": p, "confidence": round(c, 3)}
                for (t, e), p, c in zip(test, pred, conf) if p != e
            ]
        runs.append(run)
        fitted[algo] = model

    def score(run):
        return (run["test"]["f1"] if run["test"] else run["cv"]["f1"], run["cv"]["f1"])

    best = max(runs, key=score)
    bundle = {
        "pipeline": fitted[best["algorithm"]],
        "algorithm": best["algorithm"],
        "labels": labels,
        "recommended_threshold": best["details"].get("recommended_threshold"),
        "metrics": {"cv": best["cv"], "test": best["test"]},
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return {"best": best["algorithm"], "runs": runs, "model": bundle}


def save(bundle: dict, report: dict, model_dir: Path) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / MODEL_FILENAME
    joblib.dump(bundle, path)
    (model_dir / REPORT_FILENAME).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- prediction
class IntentClassifier:
    def __init__(self, bundle: dict):
        self.bundle = bundle
        self.pipeline: Pipeline = bundle["pipeline"]
        self.algorithm: str = bundle["algorithm"]

    @classmethod
    def load(cls, path: Path) -> "IntentClassifier":
        return cls(joblib.load(path))

    def predict(self, text: str, top_k: int = 3) -> dict:
        processed = preprocess(text)
        proba = self.pipeline.predict_proba([processed])[0]
        order = np.argsort(proba)[::-1][:top_k]
        top = [{"intent": str(self.pipeline.classes_[i]), "confidence": round(float(proba[i]), 4)} for i in order]
        return {
            "intent": top[0]["intent"],
            "confidence": top[0]["confidence"],
            "is_doc_query": top[0]["intent"] == DOC_QUERY,
            "top": top,
            "processed": processed,
            "algorithm": self.algorithm,
        }


# --------------------------------------------------------------------------- app integration
_lock = threading.Lock()
_cache: dict[str, IntentClassifier] = {}


def _test_samples(app) -> list[tuple[str, str]]:
    path = Path(app.config["DATA_DIR"]) / "intent_test.json"
    if not path.exists():
        path = Path(__file__).resolve().parents[1] / "data" / "intent_test.json"
    if not path.exists():
        return []
    return [tuple(s) for s in json.loads(path.read_text(encoding="utf-8"))["samples"]]


def train_and_activate(app) -> dict:
    """Train from the intents in the DB, save the winner, log runs, apply the tuned threshold.
    Must be called inside an app context."""
    from models import database as db

    with _lock:
        result = train(db.load_intents(active_only=True), _test_samples(app))
        report = {k: v for k, v in result.items() if k != "model"}
        report["trained_at"] = result["model"]["trained_at"]
        save(result["model"], report, Path(app.config["MODEL_DIR"]))
        db.record_model_runs(result["runs"], result["best"])

        threshold = result["model"].get("recommended_threshold")
        if threshold is not None:
            conn = db.get_db()
            conn.execute("UPDATE settings SET value = ? WHERE key = 'intent_threshold'", (str(threshold),))
            conn.commit()
        db.set_settings({"intents_dirty": "0"})  # the model now matches the intents in the database
        _cache.pop(str(app.config["MODEL_DIR"]), None)
    return report


def get_classifier(app) -> IntentClassifier:
    """Load the saved model (cached); trains one first if none exists yet."""
    key = str(app.config["MODEL_DIR"])
    clf = _cache.get(key)
    if clf is None:
        path = Path(key) / MODEL_FILENAME
        if not path.exists():
            app.logger.info("No intent model found; training one now…")
            train_and_activate(app)
        with _lock:
            clf = _cache[key] = IntentClassifier.load(path)
    return clf
