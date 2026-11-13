"""Assemble docs/TEST_REPORT.md from the saved evaluation results.

    .venv\\Scripts\\python -m pytest --junitxml=data/models/pytest.xml --cov=. --cov-report=json:data/models/coverage.json
    .venv\\Scripts\\python tools/make_test_report.py

Reads data/models/: pytest.xml, coverage.json, intent_report.json, rag_report.json,
answer_report_<tag>.json (every tag found). Each section is skipped if its file is missing.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "data" / "models"
OUT = ROOT / "docs" / "TEST_REPORT.md"

pct = lambda v: "—" if v is None else f"{v * 100:.1f}%"   # noqa: E731
sec = lambda ms: "—" if ms is None else (f"{ms} ms" if ms < 1000 else f"{ms / 1000:.2f} s")  # noqa: E731


def load(name):
    p = MODELS / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def unit_tests() -> list[str]:
    p = MODELS / "pytest.xml"
    if not p.exists():
        return []
    root = ET.parse(p).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    per_file = Counter()
    failed = Counter()
    for case in suite.iter("testcase"):
        module = case.get("classname", "").split(".")[-1]
        per_file[module] += 1
        if case.find("failure") is not None or case.find("error") is not None:
            failed[module] += 1
    about = {
        "test_app": "App factory, schema, sign-in, roles, theme API, health",
        "test_nlp": "Pre-processing, responses, router rule, classifier training, predict API",
        "test_rag": "Loaders (PDF/DOCX/TXT/MD/URL), chunker, ingestion, document API, retrieval scope",
        "test_chat": "Hybrid retrieval, prompts, router, chat/stream API, conversations, feedback, stop",
        "test_ui": "No-sign-in mode, chat page, conversation links",
        "test_speech": "Speech API, Whisper on silence/tones/real speech",
        "test_admin": "Collections, users, intents, settings, document move, admin-only access",
        "test_analytics": "Dashboard figures, time windows, metrics API",
    }
    lines = ["## 1. Automated tests", "",
             f"`pytest`: **{int(suite.get('tests')) - int(suite.get('failures', 0)) - int(suite.get('errors', 0))} of "
             f"{suite.get('tests')} passed**, {suite.get('skipped', 0)} skipped, in {float(suite.get('time', 0)):.0f} s.", "",
             "| Test module | What it covers | Tests | Failed |", "|---|---|---|---|"]
    for module, n in sorted(per_file.items()):
        lines.append(f"| `{module}` | {about.get(module, '')} | {n} | {failed[module]} |")
    cov = load("coverage.json")
    if cov:
        files = cov["files"]
        groups = {"app/config": ("app.py", "config.py"), "models/": ("models",), "nlp/": ("nlp",), "rag/": ("rag",),
                  "services/": ("services",), "routes/": ("routes",)}
        cli = ("nlp/train.py", "rag/evaluate.py", "rag/answer_eval.py")
        run_stmts = sum(f["summary"]["num_statements"] for p, f in files.items() if p.replace("\\", "/") not in cli)
        run_cov = sum(f["summary"]["covered_lines"] for p, f in files.items() if p.replace("\\", "/") not in cli)
        lines += ["", f"Line coverage: **{cov['totals']['percent_covered']:.0f}%** of all application code, and "
                  f"**{run_cov / run_stmts * 100:.0f}%** of the code that runs inside the app. The three command-line "
                  "evaluation scripts (`nlp/train.py`, `rag/evaluate.py`, `rag/answer_eval.py`) are exercised by the "
                  "evaluation runs in sections 2–4 rather than by unit tests. The Ollama clients are only partly covered "
                  "because unit tests use stand-ins; the end-to-end run in section 4 exercises them with the real models.",
                  "", "| Package | Statements | Covered |", "|---|---|---|"]
        for label, prefixes in groups.items():
            stmts = covd = 0
            for path, f in files.items():
                path = path.replace("\\", "/")
                if path.startswith(prefixes):
                    stmts += f["summary"]["num_statements"]
                    covd += f["summary"]["covered_lines"]
            if stmts:
                lines.append(f"| `{label}` | {stmts} | {covd / stmts * 100:.0f}% |")
    return lines + [""]


def intent_section() -> list[str]:
    rep = load("intent_report.json")
    if not rep:
        return []
    lines = ["## 2. Intent classifier", "",
             f"{rep['runs'][0]['n_samples']} training patterns across {rep['runs'][0]['n_intents']} intents; "
             f"held-out set of {rep['runs'][0]['test']['n']} unseen phrasings (`data/intent_test.json`), including "
             "off-topic questions that must not get a canned reply.", "",
             "| Model | Tuned setting | CV accuracy | CV macro-F1 | Test accuracy | Test macro-F1 |", "|---|---|---|---|---|---|"]
    for r in rep["runs"]:
        params = ", ".join(f"{k}={v}" for k, v in r["params"].items())
        mark = " **(selected)**" if r["algorithm"] == rep["best"] else ""
        lines.append(f"| {r['name']}{mark} | {params} | {r['cv']['accuracy']:.3f} | {r['cv']['f1']:.3f} | "
                     f"{r['test']['accuracy']:.3f} | {r['test']['f1']:.3f} |")
    best = next(r for r in rep["runs"] if r["algorithm"] == rep["best"])
    t = best["details"]["recommended_threshold"]
    row = next(x for x in best["details"]["threshold_sweep"] if abs(x["threshold"] - t) < 1e-9)
    lines += ["", f"Confidence threshold chosen by the training script: **{t}**. At that value, "
              f"{pct(row['routing_accuracy'])} of held-out messages are routed correctly, {pct(row['wrong_canned_reply'])} "
              f"get the wrong quick reply and {pct(row['small_talk_to_rag'])} of small talk goes to the documents "
              "(cost function: a wrong quick reply counts twice)."]
    weakest = sorted(best["details"]["cv"]["per_class"].items(), key=lambda kv: kv[1]["f1-score"])[:3]
    lines += ["", "Weakest intents (cross-validation F1): " + ", ".join(f"`{k}` {v['f1-score']:.2f}" for k, v in weakest) + "."]
    return lines + [""]


def rag_section() -> list[str]:
    rep = load("rag_report.json")
    if not rep:
        return []
    k = rep["k"]
    lines = ["## 3. Document retrieval", "",
             f"{rep['n_questions']} questions with a known answer passage and {rep['n_out_of_scope']} off-topic questions "
             f"(`data/rag_eval.json`); embeddings `{rep['embed_model']}`.", "",
             f"| Search mode | Hit@1 | Hit@{k} | MRR@{k} |", "|---|---|---|---|"]
    for mode in ("vector", "keyword", "hybrid"):
        m = rep["metrics"][mode]
        lines.append(f"| {mode}{' (used)' if mode == 'hybrid' else ''} | {m['hit@1']:.3f} | {m[f'hit@{k}']:.3f} | {m[f'mrr@{k}']:.3f} |")
    g = rep["gate"]
    lines += ["", f"\"Not found\" threshold: answerable questions scored {g['answerable']['min']}–{g['answerable']['max']}, "
              f"off-topic {g['out_of_scope']['min']}–{g['out_of_scope']['max']}. Threshold **{g['threshold']}** separates them "
              f"with {pct(g['gate_accuracy'])} accuracy ({g['answerable_blocked']} answerable blocked, "
              f"{g['out_of_scope_passed']} off-topic let through)."]
    if rep["misses"]:
        lines += ["", "Retrieval misses: " + "; ".join(f"“{m['q']}”" for m in rep["misses"]) + "."]
    return lines + [""]


def answer_section() -> list[str]:
    reports = sorted(MODELS.glob("answer_report_*.json"))
    if not reports:
        return []
    lines = ["## 4. End-to-end answers", "",
             "Every question goes through the full pipeline (classifier → rewrite → hybrid retrieval → LLM) on a copy of "
             "the database (`python -m rag.answer_eval`, gold set `data/answer_eval.json`). Graded automatically: the "
             "expected fact is in the answer; the right document is cited; every number in the answer appears in a "
             "retrieved passage (\"grounded\", a hallucination check); off-topic questions are declined; small talk takes "
             "the fast path.", ""]
    for p in reports:
        rep = json.loads(p.read_text(encoding="utf-8"))
        runs = rep["runs"]
        lines += [f"### Run `{rep['tag']}` ({rep['run_at'][:16].replace('T', ' ')})", "",
                  "| Metric | " + " | ".join(f"`{r['model']}`" for r in runs) + " |", "|---|" + "---|" * len(runs)]
        for label, key in (("Correct fact in answer", "answer_accuracy"), ("Correct document cited", "citation_accuracy"),
                           ("Numbers grounded in sources", "grounded_rate"), ("Off-topic declined", "out_of_scope_declined"),
                           ("Small talk on fast path", "small_talk_fast_path")):
            lines.append(f"| {label} | " + " | ".join(pct(r["summary"][key]) for r in runs) + " |")
        for label, key, stat in (("First token (median)", "rag_ttft_ms", "median"), ("First token (90th pct)", "rag_ttft_ms", "p90"),
                                 ("Full answer (median)", "rag_total_ms", "median"), ("Full answer (90th pct)", "rag_total_ms", "p90"),
                                 ("\"Not found\" reply (median)", "fallback_total_ms", "median"),
                                 ("Quick reply (median)", "intent_total_ms", "median")):
            lines.append(f"| {label} | " + " | ".join(sec((r["summary"][key] or {}).get(stat)) for r in runs) + " |")
        lines.append("")
    return lines


FINDINGS = """## 5. Findings and known limitations

**Model choice.** `llama3.2:3b` answers about twice as fast as `qwen2.5:7b-instruct`, but it left out citations in
almost half its answers and made up facts in two cases (it gave a Pune per diem of INR 5,000 and called Mysuru a metro city).
The 7B model cited the right document every time, so it stays the default. The 3B model remains the fallback.

**Experiments that did not help** (same 41 questions, `qwen2.5:7b-instruct`):

| Change | Correct fact | Result |
|---|---|---|
| Baseline (top 5 chunks, original prompt) | 92.7% | shipped |
| Also include the chunks next to the top two matches (`neighbor_chunks=1`) | 92.7% | not adopted: slower, and the Pune answer got worse |
| Stricter prompt rules (check category definitions, list every case, never compute totals) | 92.7% | not adopted: no change |

**The three questions the 7B model still gets wrong** all need a condition resolved across sections:

1. *"Per diem for a trip to Pune?"* The per-diem table only says "metro cities"; the list of metro cities (which
   includes Pune) is in the hotel section. The model gives the "other cities" figure, or with neighbouring chunks the
   hotel limit.
2. *"How much does the Professional plan cost per agent?"* It gives the monthly-billing price and then multiplies it
   into a yearly total that isn't in the guide. The grounding check flags that number. It doesn't mention the
   annual-billing price (INR 999).
3. *"Who approves a 25 percent discount?"* It gives only the non-profit special case (Sales Manager), not the
   general rule for 20–30% (VP Sales).

Ways to address them: a larger model (needs more than 6 GB of GPU memory), or writing documents so that each table
names its categories ("metro cities as listed in section 4").

**Relevance gate: follow-up fix (found while capturing screenshots).** The follow-up *"and can I carry them forward?"*
was rewritten correctly to *"Can I carry forward the casual leaves?"*, and the right passage was retrieved first, but its
similarity (0.598) was just under the 0.618 threshold, so the user got "not found". The gate now also accepts questions
in a grey zone [0.57, 0.618) when the BM25 keyword search independently ranks one of the top-3 vector passages first.
Measured on 85 answerable questions (the gold sets plus six realistic follow-up phrasings, one of them this case) and 18
off-topic questions: the old rule blocked 1 and let through 0; the new rule blocks 0 and lets through 0. The closest
off-topic question ("share price of Apple", 0.563 with keyword agreement) sits just below the floor, so the margin is
small. Run `final` above confirms the end-to-end results are unchanged.

**Limits of the automatic checks.** The grounding check only finds numbers that appear in no retrieved passage. A wrong
number that happens to appear elsewhere in the passages passes (the 3B model's INR 5,000 is a hotel limit). Fact
matching is substring-based, so very short facts can be satisfied by chance; the gold set avoids those where it can.
Answers vary slightly between runs (temperature 0.2). The gold sets were written by the developer for the sample
documents, and the "not found" threshold and the intent threshold were tuned on held-out sets that are also used for
reporting, so the scores are likely a little optimistic for new documents.
"""


def main() -> None:
    sections = [unit_tests(), intent_section(), rag_section(), answer_section(), FINDINGS.splitlines()]
    body = [line for s in sections for line in s]
    if not body:
        sys.exit("No results found in data/models/. Run the tests and evaluations first.")
    header = ["# ConvoAI — Test and evaluation report", "",
              f"Generated {datetime.now():%d %B %Y, %H:%M} by `tools/make_test_report.py` from saved results. "
              "Hardware: laptop with NVIDIA RTX 3060 (6 GB), 39 GB RAM; models served by Ollama on the same machine. "
              "Manual acceptance tests: see [UAT.md](UAT.md).", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(header + body), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
