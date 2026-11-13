"""Train and compare the intent classifiers from the command line.

    .venv\\Scripts\\python -m nlp.train            # train, save best, print report
    .venv\\Scripts\\python -m nlp.train --reseed   # first reload data/intents.json into the DB

Writes data/models/intent_model.joblib, intent_report.json and intent_report.md
(the Markdown tables are ready to paste into the project report).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def to_markdown(report: dict) -> str:
    runs = report["runs"]
    out = ["# Intent classifier report", "", f"Trained: {report['trained_at']}  ",
           f"Samples: {runs[0]['n_samples']} patterns across {runs[0]['n_intents']} intents  ",
           f"Selected model: **{next(r['name'] for r in runs if r['algorithm'] == report['best'])}**", ""]

    out += ["## Model comparison", "",
            "| Model | Best params | CV accuracy | CV precision | CV recall | CV F1 | Test accuracy | Test F1 |",
            "|---|---|---|---|---|---|---|---|"]
    for r in runs:
        t = r["test"] or {}
        params = ", ".join(f"{k}={v}" for k, v in r["params"].items())
        out.append(f"| {r['name']} | {params} | {r['cv']['accuracy']:.3f} | {r['cv']['precision']:.3f} | "
                   f"{r['cv']['recall']:.3f} | {r['cv']['f1']:.3f} | {t.get('accuracy', 0):.3f} | {t.get('f1', 0):.3f} |")
    out += ["", "CV = stratified 5-fold cross-validation on the training patterns. "
            "Test = held-out phrasings in data/intent_test.json (macro averages).", ""]

    best = next(r for r in runs if r["algorithm"] == report["best"])
    if "threshold_sweep" in best["details"]:
        out += ["## Router confidence threshold (selected model, held-out set)", "",
                "| Threshold | Routing accuracy | Wrong canned reply | Small talk → RAG |", "|---|---|---|---|"]
        for row in best["details"]["threshold_sweep"]:
            mark = " ←" if row["threshold"] == best["details"]["recommended_threshold"] else ""
            out.append(f"| {row['threshold']:.2f}{mark} | {row['routing_accuracy']:.3f} | "
                       f"{row['wrong_canned_reply']:.3f} | {row['small_talk_to_rag']:.3f} |")
        out.append("")
        errors = best["details"].get("test_errors", [])
        out += [f"## Held-out misclassifications ({len(errors)})", ""]
        if errors:
            out += ["| Text | Expected | Predicted | Confidence |", "|---|---|---|---|"]
            out += [f"| {e['text']} | {e['expected']} | {e['predicted']} | {e['confidence']:.2f} |" for e in errors]
        out.append("")

    out += ["## Per-intent F1 (selected model, cross-validation)", "", "| Intent | Precision | Recall | F1 | Support |",
            "|---|---|---|---|---|"]
    for lab, m in best["details"]["cv"]["per_class"].items():
        out.append(f"| {lab} | {m['precision']:.2f} | {m['recall']:.2f} | {m['f1-score']:.2f} | {int(m['support'])} |")
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reseed", action="store_true", help="reload data/intents.json into the database first")
    args = parser.parse_args()

    from app import create_app
    from models import database as db
    from nlp.classifier import train_and_activate

    app = create_app(background=False)
    with app.app_context():
        if args.reseed:
            conn = db.get_db()
            db.import_intents(conn, json.loads(Path(app.config["INTENTS_FILE"]).read_text(encoding="utf-8"))["intents"])
            conn.commit()
            print("Reloaded intents from", app.config["INTENTS_FILE"])

        start = time.perf_counter()
        report = train_and_activate(app)
        md = to_markdown(report)
        (Path(app.config["MODEL_DIR"]) / "intent_report.md").write_text(md, encoding="utf-8")
        print(md)
        print(f"Trained in {time.perf_counter() - start:.1f}s → {app.config['MODEL_DIR']}")
        print("intent_threshold setting is now", db.get_setting("intent_threshold"))


if __name__ == "__main__":
    main()
