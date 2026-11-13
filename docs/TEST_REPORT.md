# ConvoAI — Test and evaluation report

Generated 12 November 2026, 22:32 by `tools/make_test_report.py` from saved results. Hardware: laptop with NVIDIA RTX 3060 (6 GB), 39 GB RAM; models served by Ollama on the same machine. Manual acceptance tests: see [UAT.md](UAT.md).

## 1. Automated tests

`pytest`: **97 of 97 passed**, 0 skipped, in 85 s.

| Test module | What it covers | Tests | Failed |
|---|---|---|---|
| `test_admin` | Collections, users, intents, settings, document move, admin-only access | 13 | 0 |
| `test_analytics` | Dashboard figures, time windows, metrics API | 5 | 0 |
| `test_app` | App factory, schema, sign-in, roles, theme API, health | 9 | 0 |
| `test_chat` | Hybrid retrieval, prompts, router, chat/stream API, conversations, feedback, stop | 19 | 0 |
| `test_nlp` | Pre-processing, responses, router rule, classifier training, predict API | 20 | 0 |
| `test_rag` | Loaders (PDF/DOCX/TXT/MD/URL), chunker, ingestion, document API, retrieval scope | 22 | 0 |
| `test_speech` | Speech API, Whisper on silence/tones/real speech | 5 | 0 |
| `test_ui` | No-sign-in mode, chat page, conversation links | 4 | 0 |

Line coverage: **80%** of all application code, and **89%** of the code that runs inside the app. The three command-line evaluation scripts (`nlp/train.py`, `rag/evaluate.py`, `rag/answer_eval.py`) are exercised by the evaluation runs in sections 2–4 rather than by unit tests. The Ollama clients are only partly covered because unit tests use stand-ins; the end-to-end run in section 4 exercises them with the real models.

| Package | Statements | Covered |
|---|---|---|
| `app/config` | 112 | 72% |
| `models/` | 321 | 97% |
| `nlp/` | 293 | 81% |
| `rag/` | 877 | 64% |
| `services/` | 437 | 84% |
| `routes/` | 751 | 89% |

## 2. Intent classifier

638 training patterns across 25 intents; held-out set of 100 unseen phrasings (`data/intent_test.json`), including off-topic questions that must not get a canned reply.

| Model | Tuned setting | CV accuracy | CV macro-F1 | Test accuracy | Test macro-F1 |
|---|---|---|---|---|---|
| Multinomial Naive Bayes | alpha=0.05 | 0.732 | 0.724 | 0.890 | 0.875 |
| Logistic Regression **(selected)** | C=5 | 0.762 | 0.763 | 0.910 | 0.905 |

Confidence threshold chosen by the training script: **0.35**. At that value, 90.0% of held-out messages are routed correctly, 4.0% get the wrong quick reply and 6.0% of small talk goes to the documents (cost function: a wrong quick reply counts twice).

Weakest intents (cross-validation F1): `help_usage` 0.50, `frustration` 0.55, `bot_capabilities` 0.58.

## 3. Document retrieval

46 questions with a known answer passage and 15 off-topic questions (`data/rag_eval.json`); embeddings `nomic-embed-text`.

| Search mode | Hit@1 | Hit@5 | MRR@5 |
|---|---|---|---|
| vector | 0.891 | 0.978 | 0.931 |
| keyword | 0.848 | 0.978 | 0.909 |
| hybrid (used) | 0.891 | 0.978 | 0.935 |

"Not found" threshold: answerable questions scored 0.636–0.857, off-topic 0.468–0.6. Threshold **0.618** separates them with 100.0% accuracy (0 answerable blocked, 0 off-topic let through).

Retrieval misses: “Which days do we have to come to the office?”.

## 4. End-to-end answers

Every question goes through the full pipeline (classifier → rewrite → hybrid retrieval → LLM) on a copy of the database (`python -m rag.answer_eval`, gold set `data/answer_eval.json`). Graded automatically: the expected fact is in the answer; the right document is cited; every number in the answer appears in a retrieved passage ("grounded", a hallucination check); off-topic questions are declined; small talk takes the fast path.

### Run `baseline` (2026-11-12 21:20)

| Metric | `qwen2.5:7b-instruct` | `llama3.2:3b` |
|---|---|---|
| Correct fact in answer | 92.7% | 90.2% |
| Correct document cited | 100.0% | 53.7% |
| Numbers grounded in sources | 97.6% | 100.0% |
| Off-topic declined | 100.0% | 100.0% |
| Small talk on fast path | 100.0% | 100.0% |
| First token (median) | 1.62 s | 1.00 s |
| First token (90th pct) | 1.77 s | 1.12 s |
| Full answer (median) | 3.06 s | 1.32 s |
| Full answer (90th pct) | 4.20 s | 1.77 s |
| "Not found" reply (median) | 613 ms | 595 ms |
| Quick reply (median) | 2 ms | 2 ms |

### Run `final` (2026-11-12 22:29)

| Metric | `qwen2.5:7b-instruct` |
|---|---|
| Correct fact in answer | 92.7% |
| Correct document cited | 100.0% |
| Numbers grounded in sources | 97.6% |
| Off-topic declined | 100.0% |
| Small talk on fast path | 100.0% |
| First token (median) | 1.52 s |
| First token (90th pct) | 1.84 s |
| Full answer (median) | 3.10 s |
| Full answer (90th pct) | 6.35 s |
| "Not found" reply (median) | 586 ms |
| Quick reply (median) | 2 ms |

### Run `neighbours` (2026-11-12 21:23)

| Metric | `qwen2.5:7b-instruct` |
|---|---|
| Correct fact in answer | 92.7% |
| Correct document cited | 100.0% |
| Numbers grounded in sources | 97.6% |
| Off-topic declined | 100.0% |
| Small talk on fast path | 100.0% |
| First token (median) | 1.76 s |
| First token (90th pct) | 2.16 s |
| Full answer (median) | 3.04 s |
| Full answer (90th pct) | 4.20 s |
| "Not found" reply (median) | 683 ms |
| Quick reply (median) | 2 ms |

### Run `prompt-v2` (2026-11-12 21:26)

| Metric | `qwen2.5:7b-instruct` |
|---|---|
| Correct fact in answer | 92.7% |
| Correct document cited | 100.0% |
| Numbers grounded in sources | 97.6% |
| Off-topic declined | 100.0% |
| Small talk on fast path | 100.0% |
| First token (median) | 1.63 s |
| First token (90th pct) | 1.72 s |
| Full answer (median) | 2.97 s |
| Full answer (90th pct) | 4.05 s |
| "Not found" reply (median) | 600 ms |
| Quick reply (median) | 2 ms |

## 5. Findings and known limitations

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