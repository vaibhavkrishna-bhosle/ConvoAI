# Updating the project report

The July 2026 synopsis describes an intent-classification chatbot. The built system keeps that as its first stage and adds Retrieval-Augmented Generation, departmental collections and local voice. Below, for each synopsis section: **what changed** and **ready-to-adapt text or tables**. All figures are measured; see [TEST_REPORT.md](TEST_REPORT.md).

> Write it in your own words where your university requires it; the tables can be used as they are.

---

## Title

*ConvoAI: An Intelligent Conversational Assistant Using Python, Natural Language Processing and Retrieval-Augmented Generation*

## Abstract (new, ~180 words)

> Organisations answer the same policy and support questions repeatedly, while keyword chatbots fail on rephrased questions and cloud assistants send confidential data off-site. ConvoAI is a locally deployed conversational assistant that answers questions from an organisation's own documents. A hybrid router first applies a classical NLP pipeline (tokenisation, stop-word removal, lemmatisation, TF-IDF features) and a Logistic Regression intent classifier to answer small talk instantly. Other questions are rewritten if they are follow-ups, then answered by Retrieval-Augmented Generation: documents (PDF, Word, text, web pages) are chunked and embedded, retrieved by a hybrid of vector and BM25 search fused with Reciprocal Rank Fusion, and passed to a locally hosted 7-billion-parameter language model that must cite its sources. A similarity gate declines out-of-scope questions instead of guessing. The Flask web application provides streaming chat, voice input with on-device Whisper, departmental collections, an administration panel and analytics. On held-out tests the classifier reached 0.905 macro-F1, retrieval found the right passage in the top five for 97.8% of questions, and end-to-end answers were factually correct for 92.7% of questions with 100% correct citations, starting within 1.6 seconds on a laptop GPU.

## Chapter 1: Introduction

**1.3 Objectives:** replace with:

- Build a web-based assistant that answers natural-language questions from an organisation's own documents, with citations.
- Implement an NLP pipeline (tokenisation, stop-word removal, lemmatisation, TF-IDF) and compare intent classifiers (Naive Bayes vs Logistic Regression) for routing and small talk.
- Implement Retrieval-Augmented Generation: document ingestion, chunking, embeddings, hybrid retrieval and grounded generation with a local language model.
- Decline questions the documents do not cover rather than guess.
- Provide a modern web interface with streaming answers, conversation history, voice input/output, an administration panel and analytics.
- Keep all data and processing on the local machine.
- Evaluate classification, retrieval and end-to-end answer quality quantitatively.

**1.4 Scope:** add: document upload (PDF, DOCX, TXT, Markdown, URL), departmental collections with access control, Retrieval-Augmented Generation with a local LLM (Ollama), hybrid search, local speech-to-text (Whisper) and read-aloud, model-metrics page. Out of scope: OCR of scanned PDFs, multi-language answers, external messaging platforms.

**1.6 System overview:** the system now has four tiers: presentation (Jinja2 + Material Web, Chart.js), application (Flask: router, ingestion, analytics), data (SQLite, ChromaDB vector store, uploaded files) and local AI services (Ollama for the LLM and embeddings, faster-whisper for speech).

## Chapter 2: Literature survey

**Table 2.1:** add a row:

| Approach | Advantages | Limitations |
|---|---|---|
| Retrieval-Augmented Generation (RAG) | Answers from current documents without retraining; cites sources; can decline when nothing is retrieved | Quality depends on retrieval and document structure; needs a capable local model for privacy |

**2.3 Research gap:** extend: *"…ConvoAI combines a transparent intent classifier with local RAG, so it handles open-ended questions over private documents with citations, without fine-tuning and without sending data to a cloud service."* Cite Lewis et al. (2020) for RAG, Robertson & Zaragoza (2009) for BM25 and Cormack et al. (2009) for RRF.

## Chapter 3: System analysis and design

**Table 3.1: Functional requirements** (replace):

| ID | Requirement | Description |
|---|---|---|
| FR-01 | Chat interface | Send messages and receive streamed replies in real time |
| FR-02 | Intent classification | Classify each message (TF-IDF + Logistic Regression) to route small talk vs document questions |
| FR-03 | Response selection | Canned responses for small-talk intents; generated answers for document questions |
| FR-04 | Fallback handling | Decline when classifier confidence or retrieval relevance is too low |
| FR-05 | Conversation history | List, search, rename, delete and reopen conversations |
| FR-06 | Admin management | Manage intents (with retraining), collections, documents, users and settings |
| FR-07 | Analytics dashboard | Usage, answer routes, response time, most-cited documents, content gaps, feedback |
| FR-08 | REST API | JSON and streaming (SSE) endpoints for chat, documents, analytics and metrics |
| FR-09 | Document ingestion | Upload PDF/DOCX/TXT/MD or add a URL; chunk, embed and index in the background |
| FR-10 | Collections and access control | Group documents by department; with sign-in on, each user searches only their collections |
| FR-11 | Grounded answers with citations | Answers cite the passages used; users can open the sources |
| FR-12 | Follow-up understanding | Rewrite follow-up questions using the conversation before searching |
| FR-13 | Voice input/output | Local speech-to-text (Whisper) and read-aloud with installed voices |
| FR-14 | Model metrics | Classifier comparison, confusion matrix, threshold analysis, retrieval evaluation |

**Table 3.2: Non-functional requirements** (replace; the *Measured* column is the evidence):

| ID | Requirement | Target | Measured |
|---|---|---|---|
| NFR-01a | Small-talk response time | < 300 ms | ~2 ms (median) |
| NFR-01b | Document answer, first words | < 2 s | 1.5–1.6 s median, 1.8 s 90th percentile (RTX 3060) |
| NFR-01c | Document answer, complete | < 8 s | 3.1 s median, 4–6 s 90th percentile |
| NFR-02 | Usability | No training needed; works on phones | Material 3 UI, phone layout, UAT passed |
| NFR-03 | Portability | Windows/macOS/Linux | Python + Ollama; one-click scripts for Windows |
| NFR-04 | Maintainability | Modular, tested | 7 packages; 97 automated tests, 80% coverage |
| NFR-05 | Scalability | 10,000+ messages, hundreds of documents | SQLite indexes; ChromaDB vector store |
| NFR-06 | Privacy | No data leaves the machine | LLM, embeddings, speech and storage are all local |
| NFR-07 | Accuracy | Answers grounded in documents | 92.7% correct facts, 100% correct citations; off-topic always declined |

**3.3 Architecture:** use the diagram in the README (*How it works*). Components: Flask app → router → (intent classifier | follow-up rewriter → hybrid retriever (ChromaDB + BM25) → relevance gate → LLM via Ollama) → SQLite; ingestion worker (loaders → chunker → embeddings → ChromaDB).

**3.4 DFD Level 1** (new processes): 1.0 Classify message · 2.0 Retrieve passages · 3.0 Generate answer · 4.0 Ingest document · 5.0 Analyse usage. Data stores: D1 SQLite (users, conversations, messages, sources, feedback, intents, settings), D2 ChromaDB (chunk vectors), D3 uploaded files.

**3.7 ER diagram:** the tables are `users`, `collections`, `user_collections`, `documents`, `intents`, `patterns`, `responses`, `conversations`, `messages`, `message_sources`, `feedback`, `settings` and `model_runs` (see `models/schema.sql`). Key relationships: collection 1–N documents; conversation 1–N messages; message 1–N message_sources N–1 document; user N–M collections.

**Table 3.3: Major modules** (replace):

| Module | File(s) | Purpose |
|---|---|---|
| Application | `app.py`, `config.py` | App factory, configuration, background warm-up |
| Database | `models/database.py`, `schema.sql` | SQLite schema, migrations, data access |
| Text preprocessing | `nlp/preprocess.py` | Normalise, tokenise, stop-words, lemmatise |
| Intent classifier | `nlp/classifier.py`, `nlp/train.py` | Train and compare NB/LR, tune the threshold, predict |
| Document loaders | `rag/loaders.py` | PDF/DOCX/TXT/MD/URL to text with page and heading |
| Chunking and embeddings | `rag/chunker.py`, `rag/embeddings.py` | Overlapping chunks; `nomic-embed-text` vectors |
| Vector and keyword store | `rag/store.py` | ChromaDB + BM25 per collection |
| Hybrid retriever | `rag/retriever.py` | Vector + BM25, RRF fusion, relevance gate |
| Prompting and LLM | `rag/prompt.py`, `rag/llm.py` | Grounded prompt, follow-up rewrite, streaming via Ollama |
| Router | `services/router.py` | The full chat pipeline, storing messages and sources |
| Ingestion | `services/ingest.py` | Background indexing worker |
| Speech | `services/speech.py` | Whisper speech-to-text |
| Analytics | `services/analytics.py` | Dashboard statistics |
| Web layer | `routes/*.py`, `templates/`, `static/js/` | Pages and REST/SSE APIs; Material 3 UI |

## Chapter 4: Methodology

**4.2:** keep the NLP pipeline text (it is the intent classifier) and add the RAG pipeline:

1. **Ingestion:** extract text per page or heading → split into ~800-character chunks with 150 characters of overlap → embed with `nomic-embed-text` → store in ChromaDB with collection, document, page and heading metadata, and build a BM25 index.
2. **Query:** classify → rewrite follow-ups → embed the question → vector top-20 + BM25 top-20 → Reciprocal Rank Fusion → top-5 chunks.
3. **Gate:** relevant if the best cosine similarity ≥ 0.618, or ≥ 0.57 when BM25's best chunk is among the top-3 vector chunks; otherwise answer "not found".
4. **Generation:** a prompt with numbered sources; rules: answer only from the sources, cite [n], decline if absent; `qwen2.5:7b-instruct`, temperature 0.2, context 4096, streamed via Server-Sent Events.

**Table 4.1: Technology stack** (replace):

| Component | Technology | Purpose |
|---|---|---|
| Language | Python 3.11 | Implementation |
| Web framework | Flask 3.1, Flask-Login, Flask-WTF | Routing, sessions, CSRF |
| NLP / ML | NLTK 3.9, scikit-learn 1.7, NumPy 2.2 | Preprocessing, TF-IDF, NB/LR classifiers |
| LLM runtime | Ollama 0.40 | Local inference |
| Language models | qwen2.5:7b-instruct (default), llama3.2:3b (fallback) | Answer generation, follow-up rewriting |
| Embeddings | nomic-embed-text (768-d) | Semantic search |
| Vector store | ChromaDB 1.1 | Vector index with metadata filters |
| Keyword search | rank-bm25 | BM25 ranking |
| Document parsing | pypdf, python-docx, trafilatura | PDF, Word, web pages |
| Speech | faster-whisper 1.2 (Whisper small, CPU) | Local speech-to-text |
| Database | SQLite 3 | Users, conversations, messages, settings |
| Frontend | HTML5, CSS, JavaScript, Material Web 2.4 (Material 3), Marked | Interface |
| Charts | Chart.js 4.5 | Analytics and metrics |
| Testing | pytest, pytest-cov, Playwright (screenshots) | Automated tests, coverage |

## Chapter 5: Implementation and testing

**Table 5.1: Schedule as executed:**

| Phase | Work |
|---|---|
| 0–1 | Environment, Ollama and models; Flask skeleton, database, Material 3 interface |
| 2 | NLP pipeline and intent classifier (NB vs LR, threshold tuning) |
| 3 | Document ingestion: loaders, chunking, embeddings, ChromaDB + BM25 |
| 4 | Hybrid retrieval, relevance gate, grounded generation, follow-up rewriting, streaming API |
| 5 | Chat interface: streaming, citations, sources panel, history, feedback |
| 6 | Voice: local Whisper and read-aloud |
| 7 | Administration: collections, intents editor, settings, users |
| 8 | Analytics dashboard and model-metrics page |
| 9 | Testing and evaluation (unit, retrieval, end-to-end answers, UAT) |
| 10 | Documentation, setup scripts, polish |

**5.2 Testing:** summarise [TEST_REPORT.md](TEST_REPORT.md): automated tests per module and coverage; classifier (Table: NB vs LR); retrieval (hit@1, hit@5, MRR per mode); end-to-end answers (correct fact, citation, grounding, off-topic declined, latency, qwen vs llama); the experiments that did not help; UAT ([UAT.md](UAT.md)). Good figures to include: the threshold sweep, the confusion matrix and the strip plot from **Admin → Metrics** (screenshots in `docs/screenshots/12-metrics.png`).

## Chapter 6: Results and future work

**6.1:** replace "expected outcomes" with measured results (the README *Results* table) and the screenshots.

**6.2 Future enhancements:** remove *Voice interaction* and *Context awareness* (both implemented). Add:

- Larger or fine-tuned models for multi-section reasoning (the main remaining error type).
- OCR for scanned PDFs; table-aware chunking.
- Answer feedback loop: use 👎 answers and content gaps to suggest document fixes automatically.
- Multi-language answers (Hindi, Kannada).
- Integration with Microsoft Teams, Slack or WhatsApp; a production deployment (PostgreSQL, a GPU server).

## Chapter 7: Conclusion

Add: *"Combining a lightweight, interpretable intent classifier with local Retrieval-Augmented Generation gave a practical assistant: instant small talk, cited answers from private documents, and honest refusals, at about 3 seconds per answer on a laptop GPU, with no data leaving the machine. Evaluation showed retrieval is reliable (MRR 0.935); the remaining errors come from the language model combining rules across sections, which points to model size and document structure as the next levers."*

## Additional references

11. Lewis, P., Perez, E., Piktus, A., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems*, 33.
12. Robertson, S., & Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. *Foundations and Trends in Information Retrieval*, 3(4), 333–389.
13. Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods. *Proceedings of SIGIR '09*.
14. Nussbaum, Z., Morris, J. X., Duderstadt, B., & Mulyar, A. (2024). Nomic Embed: Training a Reproducible Long Context Text Embedder. arXiv:2402.01613.
15. Qwen Team (2024). Qwen2.5 Technical Report. arXiv:2412.15115.
16. Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2023). Robust Speech Recognition via Large-Scale Weak Supervision. *Proceedings of ICML 2023*.
17. Ollama documentation (2026). https://github.com/ollama/ollama
18. Chroma documentation (2026). https://docs.trychroma.com
