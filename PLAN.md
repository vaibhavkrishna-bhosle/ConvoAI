# ConvoAI — Build Plan (RAG Edition)

> A local, browser-based company assistant: hybrid **intent classifier + Retrieval-Augmented Generation (RAG)** over company documents, organised into **departments/collections**, with a **Material 3** web UI, **light/dark theme**, and **voice input/output**. Everything runs on your PC; no cloud services needed.

---

## 1. What changes vs. the synopsis

| Synopsis (original) | This build | Why |
|---|---|---|
| Intent classifier only (TF-IDF + NB) | **Hybrid router**: intent classifier for small talk / fixed FAQs, **RAG** for document questions | Answers from real company documents, and the synopsis's NLP pipeline still has a job |
| `intents.json` knowledge base | Intents **plus** uploaded PDF / DOCX / TXT / MD / URL documents | Admins add knowledge by uploading files, without retraining |
| Single shared bot | **Collections** (HR, IT, Sales, …) with per-user access | Departmental assistants |
| Plain HTML/CSS | **Material 3** (Material Web components) + dark/light | Modern UI, as you asked |
| — | Voice in/out (Web Speech API) | Implements one of the report's "future enhancements" |
| NFR-01: reply < 1 s | Intent replies < 300 ms; RAG **first token < 2 s**, full answer 3–8 s on your RTX 3060 | A local LLM can't answer in under 1 s. **Update this NFR in the report.** |

> **"Trained on documents":** with RAG, the LLM is **not retrained**. Documents are split into chunks, turned into embeddings, and stored in a vector database. At question time the relevant chunks are retrieved and the LLM answers using only those chunks, with citations. A new upload can be queried within seconds. The *intent classifier* is still trained in the usual way, from labelled patterns.

---

## 2. Your machine (checked)

- Python **3.11** (use this, not 3.14, because ChromaDB, NLTK and scikit-learn wheels are stable on 3.11)
- **39 GB RAM**, **NVIDIA RTX 3060 Laptop (6 GB VRAM)**: enough to run a 7B model on the GPU
- Node.js present (not required)
- **Ollama not installed yet.** It is step 1 of setup.

**Model choices (defaults, all changeable in Admin → Settings):**

| Role | Model | Size | Notes |
|---|---|---|---|
| Generator (LLM) | `qwen2.5:7b-instruct` (Q4) | ~4.7 GB | Good at following "answer only from context"; fits 6 GB VRAM |
| Lightweight fallback | `llama3.2:3b` | ~2 GB | For when the GPU is busy or speed matters more than quality |
| Embeddings | `nomic-embed-text` (via Ollama) | ~270 MB | Avoids installing PyTorch/sentence-transformers |

---

## 3. Architecture

```
┌──────────────────────── Presentation tier (browser) ─────────────────────────┐
│ Jinja2 templates + Material Web (M3) components + Chart.js + Web Speech API  │
│ Chat · History · Collections picker · Admin (Docs, Collections, Users,       │
│ Intents, Settings) · Analytics · Model metrics                               │
└───────────────▲──────────────────────────────────────────────┬───────────────┘
                │ HTML / JSON / SSE (streamed tokens)          │ REST /api/*
┌───────────────┴──────────── Application tier (Flask) ────────▼───────────────┐
│ auth (Flask-Login, roles)        chat router ──► intent classifier (sklearn) │
│ ingestion service (parse→chunk→embed)       └─► RAG: retrieve → prompt → LLM │
│ analytics service      admin CRUD      background job queue (ingest)         │
└───────┬──────────────────────────┬──────────────────────────────┬────────────┘
        │                          │                              │
┌───────▼────────┐   ┌─────────────▼─────────────┐   ┌────────────▼────────────┐
│ SQLite         │   │ ChromaDB (persistent)     │   │ Ollama (localhost:11434)│
│ users, colls,  │   │ chunk embeddings +        │   │ qwen2.5:7b, llama3.2:3b │
│ docs, intents, │   │ metadata (collection_id,  │   │ nomic-embed-text        │
│ conversations, │   │ doc_id, page)             │   └─────────────────────────┘
│ messages, fb   │   │ + BM25 index (rank_bm25)  │
└────────────────┘   └───────────────────────────┘   models/*.pkl (classifier)
```

### 3.1 Message flow (hybrid router)

```
User message
  │
  ├─ 1. Preprocess (lowercase, tokenize, stop-words, lemmatize — NLTK)
  ├─ 2. Intent classifier → (intent, confidence)
  │      if intent ∈ {greeting, thanks, goodbye, bot_identity, help, smalltalk, …}
  │         and confidence ≥ 0.75  → canned response (fast path, < 300 ms)
  │
  ├─ 3. Otherwise → RAG
  │      a. Rewrite follow-ups into standalone questions using the last 4 turns (context awareness)
  │      b. Hybrid retrieval in the user's allowed collection(s):
  │           vector search (Chroma, top 20) + BM25 keyword search (top 20)
  │           → Reciprocal Rank Fusion → top 5 chunks
  │      c. If best relevance < threshold → fallback ("I couldn't find that in
  │           the <collection> documents…"), and the question is logged as unanswered
  │      d. Build grounded prompt (system rules + chunks with [1]..[5] tags + question)
  │      e. Stream answer from Ollama via SSE → UI renders tokens + citation chips
  │
  └─ 4. Persist message, route taken, intent/confidence, retrieved doc ids,
         latency, and user feedback (👍/👎) → feeds analytics
```

---

## 4. Tech stack

| Layer | Technology |
|---|---|
| Backend | Flask 3, Flask-Login, Flask-WTF (CSRF), Werkzeug password hashing |
| NLP (classifier) | NLTK (tokenize, stop-words, WordNet lemmatizer), scikit-learn (TF-IDF, MultinomialNB, LogisticRegression), pickle/joblib |
| RAG | ChromaDB (persistent vector store), rank_bm25, Ollama Python client |
| Parsing | pypdf (PDF), python-docx (DOCX), markdown/plain text, requests + trafilatura (URL → clean text) |
| Chunking | Recursive splitter (~800 chars, 150 overlap, keeps headings and page numbers) |
| Database | SQLite (via the `sqlite3` module and a thin DAO, matching the synopsis's `models/database.py`) |
| Frontend | Jinja2, **Material Web** (`@material/web`) bundled into `static/vendor` so it works offline, Material Symbols, Roboto/Inter, Chart.js 4 |
| Voice | Browser Web Speech API: `SpeechRecognition` (mic → text), `speechSynthesis` (read answer aloud). Works in Chrome/Edge |
| Testing | pytest, a small evaluation script for classifier and RAG metrics |

---

## 5. Project structure

```
ConvoAI/
├── app.py                     # Flask app factory, blueprints, config
├── config.py                  # paths, thresholds, model names (overridable in DB settings)
├── requirements.txt
├── README.md
├── models/
│   ├── database.py            # SQLite schema init + CRUD + stats queries
│   └── schema.sql
├── nlp/
│   ├── preprocess.py          # tokenize, stop-words, lemmatize
│   ├── classifier.py          # train/compare NB vs LR, predict, save/load .pkl
│   └── evaluate.py            # accuracy, precision, recall, F1, confusion matrix
├── rag/
│   ├── loaders.py             # PDF / DOCX / TXT / MD / URL → text + page metadata
│   ├── chunker.py
│   ├── embeddings.py          # Ollama embed wrapper (batching)
│   ├── store.py               # Chroma + BM25 per collection
│   ├── retriever.py           # hybrid search + RRF + threshold
│   ├── prompt.py              # grounded prompt + citation format
│   ├── llm.py                 # Ollama chat streaming
│   └── evaluate.py            # hit-rate@k, MRR on a Q&A test set
├── services/
│   ├── router.py              # hybrid intent/RAG decision
│   ├── ingest.py              # background ingestion jobs + status
│   └── analytics.py
├── routes/
│   ├── auth.py  chat.py  admin.py  api.py  analytics.py
├── templates/
│   ├── base.html  login.html  chat.html
│   └── admin/ documents.html collections.html users.html intents.html
│               settings.html analytics.html metrics.html
├── static/
│   ├── css/theme.css          # M3 color tokens (light + dark), layout
│   ├── js/chat.js  voice.js  theme.js  admin.js  charts.js
│   └── vendor/                # material-web bundle, chart.js, fonts (offline)
├── data/
│   ├── intents.json           # small-talk + fixed FAQ intents
│   ├── sample_docs/           # demo company docs (HR policy, IT handbook, sales FAQ)
│   ├── uploads/               # original uploaded files
│   ├── chroma/                # vector store
│   └── convoai.db
└── tests/
```

---

## 6. Database design (SQLite)

| Table | Key columns |
|---|---|
| `users` | id, name, email, password_hash, role (`admin`/`user`), created_at |
| `collections` | id, name (HR, IT, Sales…), description, icon, color |
| `user_collections` | user_id, collection_id (access control) |
| `documents` | id, collection_id, title, source_type (pdf/docx/txt/md/url), path_or_url, status (queued/processing/ready/failed), chunk_count, error, uploaded_by, uploaded_at |
| `intents` | id, tag, description, is_active |
| `patterns` | id, intent_id, text |
| `responses` | id, intent_id, text |
| `conversations` | id, user_id, collection_id, title, created_at, updated_at |
| `messages` | id, conversation_id, role (user/bot), content, route (intent/rag/fallback), intent_tag, confidence, latency_ms, created_at |
| `message_sources` | message_id, document_id, chunk_id, page, score |
| `feedback` | message_id, rating (+1/−1), comment |
| `settings` | key, value (LLM model, thresholds, top-k, temperature) |
| `model_runs` | id, algorithm, accuracy, precision, recall, f1, trained_at, is_active |

Chunk text and vectors live in Chroma. SQLite stores only the references.

---

## 7. Features by screen (Material 3)

**Global:** top app bar, navigation rail (desktop) / bottom nav (mobile), theme toggle (light/dark/system, saved per user), M3 colour tokens with a teal seed (matches the report's palette).

1. **Login.** Email + password card. A seeded admin account is created on first run.
2. **Chat (`/`)**
   - Left drawer: conversation history (search, rename, delete), "New chat"
   - Collection selector chips (only the user's allowed collections; "All my collections" option)
   - Message bubbles with streamed tokens, typing indicator, Markdown rendering
   - **Citation chips** under RAG answers (`HR Policy.pdf · p.4`). Click to open a side sheet with the source passage highlighted
   - Badge showing the route (`Intent · greeting 0.94` / `Documents` / `Fallback`), useful in a viva demo
   - 👍/👎 feedback, copy, 🔊 read aloud
   - 🎤 mic FAB: voice input with live transcript; optional "auto-speak replies" toggle
   - Suggested starter questions per collection
3. **Admin → Documents.** Drag-and-drop upload (PDF/DOCX/TXT/MD) or "Add URL", choose collection, live ingestion status (progress, chunk count, errors), re-index, delete (removes vectors too), preview chunks.
4. **Admin → Collections.** Create/edit HR/IT/Sales…, icon and colour, document count.
5. **Admin → Users.** Create users, assign role and collection access.
6. **Admin → Intents.** CRUD for intents, patterns and responses; **Retrain** button.
7. **Admin → Model metrics.** NB vs LR comparison table, confusion-matrix heatmap, per-intent F1, active model switch; RAG eval results (hit-rate@5, MRR).
8. **Admin → Settings.** LLM model dropdown (from installed Ollama models), temperature, top-k, relevance threshold, intent confidence threshold, and an Ollama health check.
9. **Analytics dashboard.** KPI cards (messages, users, avg latency, fallback rate, 👍 ratio), messages over time (line), route split (doughnut), top intents (bar), most-cited documents (bar), **unanswered questions list** (shows which documents are missing), per-collection usage.

---

## 8. REST API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/login`, `/api/auth/logout` | Session auth |
| POST | `/api/chat` | `{message, conversation_id?, collection_id?}` → JSON reply |
| GET | `/api/chat/stream` | SSE stream of tokens + sources |
| GET/DELETE | `/api/conversations[/<id>]` | History |
| POST | `/api/messages/<id>/feedback` | 👍/👎 |
| GET/POST/DELETE | `/api/documents[/<id>]` | Upload / list / delete (admin) |
| POST | `/api/documents/url` | Index a web page (admin) |
| GET | `/api/documents/<id>/status` | Ingestion progress |
| CRUD | `/api/collections`, `/api/users`, `/api/intents` | Admin management |
| POST | `/api/model/train` | Retrain intent classifier |
| GET | `/api/stats` | Analytics data (FR-08) |
| GET | `/api/health` | Flask + Ollama + DB status |

---

## 9. Implementation phases

| # | Phase | Work | Done when |
|---|---|---|---|
| 0 | **Setup** | Install Ollama, pull models; Python 3.11 venv; requirements; NLTK data; vendor Material Web + Chart.js; `git init` | `ollama run qwen2.5:7b-instruct` answers; `flask run` serves a page |
| 1 | **Skeleton + DB + Auth** | App factory, blueprints, schema, seed admin, login/logout, roles, base M3 layout + theme toggle | Admin can log in; light/dark switch works |
| 2 | **Intent engine** | preprocess.py, intents.json (≈25 intents), train NB & LR, compare, save best, predict with confidence | `evaluate.py` prints metrics; F1 ≥ 0.85 on held-out patterns |
| 3 | **RAG ingestion** | Loaders (PDF/DOCX/TXT/MD/URL), chunker, Ollama embeddings, Chroma + BM25 per collection, background job + status | Upload a 30-page PDF and it is "ready" with chunks visible |
| 4 | **RAG answering + router** | Hybrid retrieval + RRF, threshold fallback, grounded prompt with citations, query rewriting for follow-ups, SSE streaming, hybrid router | Asking "how many casual leaves do I get?" returns a cited answer; asking "hi" goes through the intent fast path |
| 5 | **Chat UI** | Chat page, history drawer, collection chips, streaming render, citations side sheet, feedback, route badge | Full chat works end-to-end in the browser |
| 6 | **Voice** | Mic input (SpeechRecognition), read-aloud (speechSynthesis), auto-speak toggle, graceful fallback in unsupported browsers | Ask a question by voice and hear the answer |
| 7 | **Admin panel** | Documents, Collections, Users, Intents (+ retrain), Settings | All CRUD works; access control enforced on retrieval |
| 8 | **Analytics + metrics** | Stats queries, Chart.js dashboard, unanswered questions, metrics page | Dashboard populated from real usage |
| 9 | **Testing + evaluation** | pytest unit/integration; RAG eval on a 40-question gold set; latency measurements; UAT checklist | Results tables ready for the report |
| 10 | **Docs + polish** | README, user manual, screenshots, sample company docs, demo script for viva | One-command start: `python app.py` |

Suggested timing: roughly 7 weeks (phases 0–2: week 1; 3–4: weeks 2–3; 5–6: week 4; 7–8: week 5; 9: week 6; 10: week 7). This lines up with the Gantt chart in the synopsis.

---

## 10. Evaluation (for the report's results chapter)

- **Intent classifier:** accuracy, precision, recall, F1 (macro), confusion matrix; NB vs LR comparison table.
- **Retrieval:** hit-rate@5 and MRR on a hand-written gold set (question → expected document/page); compare vector-only, BM25-only and hybrid.
- **Answers:** manual faithfulness check (does each claim appear in the cited chunk?), plus the fallback rate on out-of-scope questions (it should refuse instead of hallucinating).
- **Performance:** intent-path latency, RAG time-to-first-token and total time, with GPU vs CPU (`llama3.2:3b`).
- **Access control test:** an IT-only user must never receive chunks from HR documents.

---

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| LLM hallucination | Strict "answer only from context, else say you don't know" prompt, relevance threshold, citations, low temperature (0.2) |
| Slow answers on CPU | Run on GPU by default; streaming makes waits feel shorter; 3B model option |
| Scanned PDFs have no text | Detect empty pages and flag the document as "needs OCR" (OCR is a future enhancement) |
| Voice unsupported in Firefox | Hide the mic button and show a tooltip; text chat is unaffected |
| Material Web CDN needs internet | Vendor the bundle into `static/vendor/` once so the app works offline |
| Ollama not running | `/api/health` check, a banner in the UI, and intent-only mode keeps working |

---

## 12. Report sections to update

- Title/abstract: add "with Retrieval-Augmented Generation"
- 1.3 Objectives / 1.4 Scope: document upload, collections, RAG, voice
- 2.2 Comparison table: add a **RAG** row (grounded, local, cites sources; needs a good retriever)
- 3.1 FRs: add FR-09 Document Upload & Indexing, FR-10 Collections & Access Control, FR-11 Source Citations, FR-12 Voice I/O
- 3.2 NFR-01: split into intent latency and RAG latency targets
- 3.3 Architecture / 3.7 ER diagram: add Chroma, Ollama, and the new tables
- 4.2 Methodology: add the RAG pipeline (chunk → embed → hybrid retrieve → generate)
- 4.3 Tech stack: add Ollama, ChromaDB, rank_bm25, pypdf, python-docx, Material Web
- 6.2 Future enhancements: remove voice and context awareness (now implemented); add OCR, re-ranking model, WhatsApp/Telegram integration

---

## 13. Defaults I chose (tell me to change any)

1. Demo company: a fictional mid-size firm with **HR**, **IT Support** and **Sales** collections and 2–3 sample documents each.
2. The intent classifier defaults to whichever of NB/LR scores higher; both are kept for the comparison table.
3. Chunk size 800 chars / 150 overlap; top-k 5; relevance threshold tuned during phase 9.
4. Single admin role plus regular users; no self-sign-up.
5. Plain JavaScript (no React build step), in line with your choice of Flask + Jinja.
