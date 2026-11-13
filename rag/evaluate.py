"""Retrieval evaluation on data/rag_eval.json.

    .venv\\Scripts\\python -m rag.evaluate           # report
    .venv\\Scripts\\python -m rag.evaluate --apply   # also save the tuned relevance threshold

Metrics per mode (vector / keyword / hybrid): hit@1, hit@k, MRR@k.
Relevance gate: best vector similarity of answerable vs out-of-scope questions,
and the threshold that separates them best. Writes data/models/rag_report.md.
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path

MODES = ("vector", "keyword", "hybrid")


def is_hit(hit, doc: str, contains: str) -> bool:
    return hit.title.lower() == doc.lower() and contains.lower() in hit.text.lower()


def evaluate(app, k: int = 5) -> dict:
    from models import database as db
    from rag.embeddings import get_embedder
    from rag.retriever import retrieve
    from rag.store import get_store

    gold = json.loads((Path(app.config["DATA_DIR"]) / "rag_eval.json").read_text(encoding="utf-8"))
    store, embedder = get_store(app), get_embedder(app)
    collections = [c["id"] for c in db.list_collections()]

    rows = {m: [] for m in MODES}
    in_scores, misses, per_question = [], [], []
    for item in gold["questions"]:
        vec = embedder.embed_query(item["q"])
        for mode in MODES:
            r = retrieve(store, vec, item["q"], collections, top_k=k, threshold=0, mode=mode)
            rank = next((i for i, h in enumerate(r.hits, start=1) if is_hit(h, item["doc"], item["contains"])), None)
            rows[mode].append(rank)
            if mode == "hybrid":
                in_scores.append(r.best_vector)
                per_question.append({"q": item["q"], "score": r.best_vector, "rank": rank, "doc": item["doc"]})
                if rank is None:
                    misses.append({"q": item["q"], "expected": item["doc"],
                                   "got": [f"{h.title} p.{h.page}" if h.page else h.title for h in r.hits[:3]]})

    out_scores, per_out = [], []
    for q in gold["out_of_scope"]:
        r = retrieve(store, embedder.embed_query(q), q, collections, top_k=k, threshold=0, mode="vector")
        out_scores.append(r.best_vector)
        per_out.append({"q": q, "score": r.best_vector})

    metrics = {}
    for mode, ranks in rows.items():
        n = len(ranks)
        metrics[mode] = {
            "hit@1": round(sum(1 for r in ranks if r == 1) / n, 3),
            f"hit@{k}": round(sum(1 for r in ranks if r) / n, 3),
            f"mrr@{k}": round(sum(1 / r for r in ranks if r) / n, 3),
        }

    # Threshold: maximise correct gating (answerable ≥ t, out-of-scope < t); ties → lower t (prefer answering,
    # the grounded prompt still tells the model to say "not found").
    candidates = sorted(set(round(x, 3) for x in in_scores + out_scores))
    def accuracy(t):
        return (sum(s >= t for s in in_scores) + sum(s < t for s in out_scores)) / (len(in_scores) + len(out_scores))
    best_t = max(candidates, key=lambda t: (accuracy(t), -t))
    # place the threshold midway between the closest scores on either side of the cut
    below = max((s for s in in_scores + out_scores if s < best_t), default=best_t)
    threshold = round((below + best_t) / 2, 3)

    def stats(xs):
        return {"min": round(min(xs), 3), "median": round(statistics.median(xs), 3), "max": round(max(xs), 3)}

    return {
        "k": k, "n_questions": len(in_scores), "n_out_of_scope": len(out_scores),
        "embed_model": embedder.model, "metrics": metrics, "misses": misses,
        "scores": {"answerable": per_question, "out_of_scope": per_out},
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        "gate": {"answerable": stats(in_scores), "out_of_scope": stats(out_scores),
                 "threshold": threshold, "gate_accuracy": round(accuracy(threshold), 3),
                 "answerable_blocked": sum(s < threshold for s in in_scores),
                 "out_of_scope_passed": sum(s >= threshold for s in out_scores)},
    }


def to_markdown(rep: dict) -> str:
    k = rep["k"]
    lines = ["# Retrieval evaluation", "",
             f"{rep['n_questions']} answerable questions, {rep['n_out_of_scope']} out-of-scope questions; "
             f"embeddings `{rep['embed_model']}`; top-{k}.", "",
             f"| Mode | Hit@1 | Hit@{k} | MRR@{k} |", "|---|---|---|---|"]
    for mode in MODES:
        m = rep["metrics"][mode]
        lines.append(f"| {mode} | {m['hit@1']:.3f} | {m[f'hit@{k}']:.3f} | {m[f'mrr@{k}']:.3f} |")
    g = rep["gate"]
    lines += ["", "## Relevance gate (best vector similarity)", "",
              "| Set | Min | Median | Max |", "|---|---|---|---|",
              f"| Answerable | {g['answerable']['min']} | {g['answerable']['median']} | {g['answerable']['max']} |",
              f"| Out of scope | {g['out_of_scope']['min']} | {g['out_of_scope']['median']} | {g['out_of_scope']['max']} |",
              "", f"Recommended threshold **{g['threshold']}**: gate accuracy {g['gate_accuracy']:.3f}, "
              f"{g['answerable_blocked']} answerable blocked, {g['out_of_scope_passed']} out-of-scope passed "
              "(those still reach the LLM, which is instructed to say the answer isn't in the documents).", ""]
    if rep["misses"]:
        lines += [f"## Hybrid misses ({len(rep['misses'])})", "", "| Question | Expected | Top results |", "|---|---|---|"]
        lines += [f"| {m['q']} | {m['expected']} | {'; '.join(m['got'])} |" for m in rep["misses"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="save the recommended relevance threshold to settings")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()

    from app import create_app
    from models import database as db

    app = create_app(background=False)
    with app.app_context():
        rep = evaluate(app, args.k)
        md = to_markdown(rep)
        Path(app.config["MODEL_DIR"]).mkdir(parents=True, exist_ok=True)
        (Path(app.config["MODEL_DIR"]) / "rag_report.md").write_text(md, encoding="utf-8")
        (Path(app.config["MODEL_DIR"]) / "rag_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
        print(md)
        if args.apply:
            conn = db.get_db()
            conn.execute("UPDATE settings SET value = ? WHERE key = 'relevance_threshold'", (str(rep["gate"]["threshold"]),))
            conn.commit()
            print("relevance_threshold set to", rep["gate"]["threshold"])


if __name__ == "__main__":
    main()
