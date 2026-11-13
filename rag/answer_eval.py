"""End-to-end answer evaluation: the full router with the real models on data/answer_eval.json.

    .venv\\Scripts\\python -m rag.answer_eval                                  # current chat model
    .venv\\Scripts\\python -m rag.answer_eval --models qwen2.5:7b-instruct llama3.2:3b
    .venv\\Scripts\\python -m rag.answer_eval --set neighbor_chunks=0 --tag no-neighbours

Grades every answer automatically:
  route      document question → "rag"; off-topic → declined; small talk → "intent"
  fact       the expected fact appears in the answer (case and thousands separators ignored)
  citation   the expected document is among the cited sources
  grounded   every number in the answer also appears in a retrieved passage (a hallucination check)
  latency    time to first token and to the full answer
It runs on a temporary copy of the database, so evaluation traffic never reaches Analytics.
Writes data/models/answer_report.json and answer_report.md (tables for the project report).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import tempfile
import time
from datetime import datetime
from pathlib import Path

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def norm(text: str) -> str:
    """Lower-case and drop thousands separators: 'INR 1,500' and '5,00,000' compare as plain digits."""
    return re.sub(r"(?<=\d),(?=\d)", "", text or "").lower()


def facts_ok(answer: str, facts: dict) -> bool:
    a = norm(answer)
    if "all" in facts:
        return all(norm(f) in a for f in facts["all"])
    return any(re.search(rf"(?<![\w]){re.escape(norm(f))}(?![\w])", a) for f in facts["any"])


def ungrounded_numbers(answer: str, question: str, sources: list[dict]) -> list[str]:
    """Numbers stated in the answer that appear in no retrieved passage (and not in the question)."""
    from rag.prompt import strip_citations

    corpus = norm(" ".join(s.get("text", "") + " " + (s.get("heading") or "") for s in sources))
    asked = set(NUMBER.findall(norm(question)))
    missing = []
    for n in set(NUMBER.findall(norm(strip_citations(answer)))):
        n = n.rstrip(".")
        if n in asked or len(n) == 1 and n in "0123456789":   # single digits ("1. step") are list markers
            continue
        if not re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", corpus):
            missing.append(n)
    return sorted(missing)


def ttft_ms(timings: dict) -> int | None:
    """Time to first token = every stage up to and including 'first_token'."""
    if "first_token" not in timings:
        return None
    total = 0
    for stage, ms in timings.items():
        total += ms
        if stage == "first_token":
            return total
    return None


def ask(user, question: str) -> dict:
    from services import router

    req = router.prepare(user, question, None, None)
    done = None
    for event in router.handle(user, req):
        if event["type"] == "done":
            done = event
    return done


def run_model(app, user, gold: dict, model: str) -> dict:
    from models import database as db
    from rag.llm import get_llm

    db.set_settings({"llm_model": model})
    llm = get_llm(app)
    llm.warm_up()
    ask(user, "What is the casual leave policy?")      # load models into memory; not scored

    rows, started = [], time.perf_counter()
    for item in gold["answerable"]:
        d = ask(user, item["q"])
        cited = {s["title"] for s in d["sources"] if s["cited"]}
        ungrounded = ungrounded_numbers(d["content"], item["q"], d["sources"]) if d["route"] == "rag" else []
        rows.append({
            "set": "answerable", "q": item["q"], "route": d["route"], "answer": d["content"],
            "route_ok": d["route"] == "rag", "fact_ok": facts_ok(d["content"], item["facts"]),
            "citation_ok": item["doc"] in cited, "cited": sorted(cited),
            "grounded": not ungrounded, "ungrounded": ungrounded,
            "ttft_ms": ttft_ms(d["timings_ms"]), "total_ms": d["latency_ms"], "timings": d["timings_ms"],
        })
    for q in gold["out_of_scope"]:
        d = ask(user, q)
        declined = d["route"] in ("fallback", "intent")
        rows.append({"set": "out_of_scope", "q": q, "route": d["route"], "answer": d["content"],
                     "route_ok": declined, "total_ms": d["latency_ms"], "ttft_ms": ttft_ms(d["timings_ms"])})
    for item in gold["small_talk"]:
        d = ask(user, item["q"])
        rows.append({"set": "small_talk", "q": item["q"], "route": d["route"], "answer": d["content"],
                     "route_ok": d["route"] == "intent" and d["intent"] == item["intent"], "total_ms": d["latency_ms"]})

    ans = [r for r in rows if r["set"] == "answerable"]
    oos = [r for r in rows if r["set"] == "out_of_scope"]
    talk = [r for r in rows if r["set"] == "small_talk"]
    rate = lambda xs, key: round(sum(1 for x in xs if x[key]) / len(xs), 4) if xs else None  # noqa: E731

    def stats(xs):
        xs = [x for x in xs if x is not None]
        return {"median": int(statistics.median(xs)), "p90": int(sorted(xs)[int(0.9 * (len(xs) - 1))]),
                "max": max(xs)} if xs else None

    return {
        "model": model,
        "settings": {k: db.get_setting(k) for k in ("top_k", "relevance_threshold", "intent_threshold",
                                                     "context_window", "temperature", "neighbor_chunks")},
        "summary": {
            "answer_accuracy": rate(ans, "fact_ok"),
            "citation_accuracy": rate(ans, "citation_ok"),
            "grounded_rate": rate([a for a in ans if a["route"] == "rag"], "grounded"),
            "answered_from_documents": rate(ans, "route_ok"),
            "out_of_scope_declined": rate(oos, "route_ok"),
            "small_talk_fast_path": rate(talk, "route_ok"),
            "rag_ttft_ms": stats([a["ttft_ms"] for a in ans]),
            "rag_total_ms": stats([a["total_ms"] for a in ans]),
            "fallback_total_ms": stats([o["total_ms"] for o in oos]),
            "intent_total_ms": stats([t["total_ms"] for t in talk]),
            "n": {"answerable": len(ans), "out_of_scope": len(oos), "small_talk": len(talk)},
            "wall_seconds": round(time.perf_counter() - started, 1),
        },
        "rows": rows,
    }


def to_markdown(report: dict) -> str:
    runs = report["runs"]
    pct = lambda v: "—" if v is None else f"{v * 100:.1f}%"  # noqa: E731
    sec = lambda s, k: "—" if not s else f"{s[k] / 1000:.2f} s"  # noqa: E731
    lines = ["# End-to-end answer evaluation", "",
             f"Run {report['run_at']} · tag `{report['tag']}` · {runs[0]['summary']['n']['answerable']} document questions, "
             f"{runs[0]['summary']['n']['out_of_scope']} off-topic, {runs[0]['summary']['n']['small_talk']} small talk.", "",
             "| Metric | " + " | ".join(f"`{r['model']}`" for r in runs) + " |", "|---|" + "---|" * len(runs)]
    rows = [("Correct fact in answer", "answer_accuracy"), ("Correct document cited", "citation_accuracy"),
            ("Numbers grounded in sources", "grounded_rate"), ("Answered from documents", "answered_from_documents"),
            ("Off-topic declined", "out_of_scope_declined"), ("Small talk on fast path", "small_talk_fast_path")]
    for label, key in rows:
        lines.append(f"| {label} | " + " | ".join(pct(r["summary"][key]) for r in runs) + " |")
    for label, key, k in (("First token, median", "rag_ttft_ms", "median"), ("First token, 90th pct", "rag_ttft_ms", "p90"),
                          ("Full answer, median", "rag_total_ms", "median"), ("Full answer, 90th pct", "rag_total_ms", "p90"),
                          ("“Not found” reply, median", "fallback_total_ms", "median"),
                          ("Quick reply, median", "intent_total_ms", "median")):
        lines.append(f"| {label} | " + " | ".join(sec(r["summary"][key], k) for r in runs) + " |")

    for r in runs:
        fails = [x for x in r["rows"] if not x["route_ok"] or (x["set"] == "answerable" and
                 (not x["fact_ok"] or not x["citation_ok"] or not x["grounded"]))]
        lines += ["", f"## Failures: `{r['model']}` ({len(fails)})", ""]
        if not fails:
            lines.append("None.")
            continue
        lines += ["| Question | Problem | Answer (start) |", "|---|---|---|"]
        for x in fails:
            problems = []
            if not x["route_ok"]:
                problems.append(f"route {x['route']}")
            if x["set"] == "answerable":
                if x["route_ok"] and not x["fact_ok"]:
                    problems.append("wrong/missing fact")
                if x["route_ok"] and not x["citation_ok"]:
                    problems.append(f"cited {', '.join(x['cited']) or 'nothing'}")
                if not x["grounded"]:
                    problems.append(f"ungrounded {', '.join(x['ungrounded'])}")
            answer = x["answer"].replace("\n", " ").replace("|", "/")[:140]
            lines.append(f"| {x['q']} | {'; '.join(problems)} | {answer} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", help="Ollama chat models to compare (default: the configured one)")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override a setting for this run")
    parser.add_argument("--tag", default="baseline", help="label stored with the report")
    args = parser.parse_args()

    from app import create_app
    from config import Config
    from models import database as db
    from models.user import User

    tmp = Path(tempfile.mkdtemp(prefix="convoai-eval-"))
    shutil.copy(Config.DB_PATH, tmp / "eval.db")

    class EvalConfig(Config):
        DB_PATH = tmp / "eval.db"   # evaluation chats stay out of the real history

    app = create_app(EvalConfig, background=False)
    try:
        with app.test_request_context():
            overrides = dict(kv.split("=", 1) for kv in args.set)
            if overrides:
                db.set_settings(overrides)
            user = User(db.get_db().execute("SELECT * FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone())
            gold = json.loads((Path(app.config["DATA_DIR"]) / "answer_eval.json").read_text(encoding="utf-8"))
            models = args.models or [db.get_setting("llm_model")]
            runs = []
            for m in models:
                print(f"Evaluating {m} …", flush=True)
                runs.append(run_model(app, user, gold, m))
                s = runs[-1]["summary"]
                print(f"  fact {s['answer_accuracy']:.0%} · citation {s['citation_accuracy']:.0%} · "
                      f"grounded {s['grounded_rate']:.0%} · off-topic declined {s['out_of_scope_declined']:.0%} · "
                      f"{s['wall_seconds']} s", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # the request context closed the DB connection

    report = {"tag": args.tag, "run_at": datetime.now().isoformat(timespec="seconds"), "runs": runs}
    out = Path(Config.MODEL_DIR)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"answer_report_{args.tag}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = to_markdown(report)
    (out / f"answer_report_{args.tag}.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
