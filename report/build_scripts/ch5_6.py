"""Chapters 5-6."""
from ch1_4 import STYLE, SS
from rb import C
UML = ("Standard UML notation, black lines on white background with light navy (#E3EAF5) fill for shapes, clear "
       "sans-serif or Times New Roman labels, all text horizontal and fully legible, no 3D, no shadows, no "
       "decorative elements, landscape layout suitable for an A4 academic report.")


def ch5(r):
    r.chapter_start("System Design")
    r.p("System design converts the requirements into a blueprint for implementation. This chapter presents the "
        "architecture of ConvoAI, the UML and data flow diagrams that describe its behaviour, the database design and "
        "the design of each module.")

    r.h2("System Architecture")
    r.p("ConvoAI follows a four-tier architecture, shown in Figure 5.1. The **presentation tier** runs in the "
        "browser: Jinja2 templates rendered with Material Web components, Chart.js charts and plain JavaScript that "
        "streams answers and records voice. The **application tier** is the Flask application: the chat router, the "
        "ingestion worker, the analytics service and the page and API blueprints. The **data tier** consists of "
        "SQLite for structured data, ChromaDB for chunk vectors and the folder of uploaded files. The **local AI "
        "services tier** contains Ollama, which serves the language models and the embedding model, and "
        "faster-whisper for speech recognition. All four tiers run on the same computer and communicate over "
        "localhost.")
    r.figure_placeholder("Four-tier system architecture of ConvoAI",
        "A layered architecture diagram with four horizontal tiers stacked top to bottom, each a wide rounded "
        "rectangle with a label on its left edge. Tier 1 'Presentation (Browser)': small boxes 'Chat page', 'Sources "
        "panel', 'Voice recorder', 'Admin pages', 'Analytics charts (Chart.js)', with a caption 'Jinja2 + Material Web "
        "(Material 3)'. Tier 2 'Application (Flask)': boxes 'Auth & roles', 'Chat Router', 'Intent Classifier "
        "(scikit-learn)', 'Hybrid Retriever', 'Ingestion Worker', 'Analytics Service', 'REST + SSE APIs'. Tier 3 "
        "'Data': three cylinders 'SQLite (users, chats, messages, settings)', 'ChromaDB (chunk vectors + metadata) + "
        "BM25 index', 'Uploaded files'. Tier 4 'Local AI Services': boxes 'Ollama: qwen2.5:7b-instruct / llama3.2:3b', "
        "'Ollama: nomic-embed-text', 'faster-whisper (speech-to-text)'. Vertical double-headed arrows between tiers "
        "labelled 'HTML / JSON / Server-Sent Events' (1-2), 'SQL / vector queries' (2-3), 'HTTP localhost:11434' (2-4). "
        + STYLE)

    r.h2("Use Case Diagram")
    r.p("The use case diagram in Figure 5.2 shows the two actors and what each can do. An **Employee (User)** can "
        "ask questions by text or voice, view cited sources, continue a conversation with follow-ups, manage "
        "conversation history, give feedback and switch the theme. The **Administrator** can do everything a user "
        "can, and also upload and manage documents, manage collections, edit intents and retrain the classifier, "
        "manage users and their collection access, change settings, and view analytics and model metrics.")
    r.figure_placeholder("Use case diagram",
        "A UML use case diagram. A system boundary rectangle labelled 'ConvoAI'. Left actor stick figure "
        "'Employee'; right actor stick figure 'Administrator', with a generalisation arrow (hollow triangle) from "
        "Administrator to Employee. Use case ovals inside the boundary connected to Employee: 'Ask question (text)', "
        "'Ask question (voice)', 'View cited sources', 'Ask follow-up question', 'Manage chat history', 'Give "
        "feedback', 'Switch theme'. Use case ovals connected to Administrator: 'Upload / add URL document', 'Manage "
        "collections', 'Edit intents & retrain', 'Manage users & access', 'Change settings', 'View analytics', 'View "
        "model metrics', 'Test retrieval'. Show '<<include>>' dashed arrows from 'Ask question (text)' to 'Classify "
        "intent' and 'Retrieve passages', and from 'Upload / add URL document' to 'Index document'. " + UML)

    r.h2("Data Flow Diagrams")
    r.p("Data flow diagrams (DFDs) show how data moves through the system. Figure 5.3 is the context-level "
        "(Level 0) diagram, in which ConvoAI is a single process exchanging data with the two external entities and "
        "the local AI service.")
    r.figure_placeholder("Data flow diagram, Level 0 (context diagram)",
        "A Level 0 context data flow diagram using Gane-Sarson or Yourdon notation. A single central circle "
        "labelled '0.0 ConvoAI System'. External entity rectangles: 'Employee' (left), 'Administrator' (right), "
        "'Ollama Local AI Service' (bottom). Labelled data-flow arrows: Employee -> system 'question (text / audio)', "
        "'feedback'; system -> Employee 'answer + citations', 'conversation history'; Administrator -> system "
        "'documents, URLs, intents, settings, users'; system -> Administrator 'indexing status, analytics, metrics'; "
        "system -> Ollama 'prompt, text to embed'; Ollama -> system 'generated tokens, embedding vectors'. " + UML)
    r.p("Figure 5.4 expands the system into its five main processes and three data stores. Process 1.0 classifies "
        "each message, 2.0 retrieves passages, 3.0 generates the answer, 4.0 ingests documents and 5.0 analyses "
        "usage. Data store D1 is the SQLite database, D2 the ChromaDB vector store and D3 the uploaded files.")
    r.figure_placeholder("Data flow diagram, Level 1",
        "A Level 1 data flow diagram. External entities 'Employee' (left) and 'Administrator' (right). Five process "
        "circles: '1.0 Classify message', '2.0 Retrieve passages', '3.0 Generate answer', '4.0 Ingest document', "
        "'5.0 Analyse usage'. Three open-ended data store rectangles: 'D1 SQLite (users, conversations, messages, "
        "sources, feedback, intents, settings)', 'D2 ChromaDB (chunk vectors + metadata)', 'D3 Uploaded files'. Flows: "
        "Employee -> 1.0 'message'; 1.0 -> Employee 'quick reply' (small talk); 1.0 -> 2.0 'document question'; "
        "2.0 <-> D2 'query vector / top chunks'; 2.0 -> Employee 'not found' (below threshold); 2.0 -> 3.0 'relevant "
        "chunks'; 3.0 -> Employee 'streamed answer + citations'; 3.0 -> D1 'message, route, sources, latency'; "
        "Administrator -> 4.0 'file / URL'; 4.0 -> D3 'original file'; 4.0 -> D2 'chunks + embeddings'; 4.0 -> D1 "
        "'document status'; D1 -> 5.0 'messages, feedback'; 5.0 -> Administrator 'analytics, content gaps'. " + UML)

    r.h2("Sequence Diagram")
    r.p("Figure 5.5 shows the sequence of interactions when a user asks a document question. The browser posts the "
        "question to the streaming endpoint; the router classifies it, rewrites it if it is a follow-up, embeds it, "
        "retrieves and fuses passages, checks relevance, and then streams the model's answer back as Server-Sent "
        "Events before saving the message and its sources.")
    r.figure_placeholder("Sequence diagram for answering a document question",
        "A UML sequence diagram with lifelines left to right: 'User', 'Browser (chat.js)', 'Flask /api/chat/stream', "
        "'Router', 'Intent Classifier', 'Ollama LLM', 'Embedder (nomic)', 'ChromaDB + BM25', 'SQLite'. Messages in "
        "order: 1 User->Browser 'type question'; 2 Browser->Flask 'POST question'; 3 Flask->Router 'handle()'; "
        "4 Router->SQLite 'save user message'; 5 Router->Intent Classifier 'classify(text)'; 6 return 'doc_query, "
        "0.82'; 7 Router->Ollama LLM 'rewrite follow-up' (in an 'opt' frame labelled 'if follow-up'); 8 Router->Embedder "
        "'embed_query()'; 9 Router->ChromaDB + BM25 'vector top-20 + BM25 top-20'; 10 return 'fused top-5 chunks, "
        "best score'; 11 'alt' frame: [score < threshold] Router->Browser 'not found'; [else] Router->Browser "
        "'sources event', Router->Ollama LLM 'stream(prompt with sources)', loop frame 'tokens' Ollama->Router->"
        "Browser 'token events'; 12 Router->SQLite 'save answer, route, sources, latency'; 13 Browser->User 'answer "
        "with citations'. " + UML)

    r.h2("Activity Diagram")
    r.p("The activity diagram in Figure 5.6 shows the decision logic applied to every chat message, including the "
        "three possible routes: intent (quick reply), rag (answer from documents) and fallback (not found or error).")
    r.figure_placeholder("Activity diagram of chat message handling",
        "A UML activity diagram, top to bottom. Start node -> 'Receive message' -> 'Save user message' -> "
        "'Pre-process text (normalise, tokenise, remove stop words, lemmatise)' -> 'Predict intent with Logistic "
        "Regression' -> decision diamond 'Small-talk intent AND confidence >= 0.35?' -> [yes] 'Return predefined "
        "response (route: intent)' -> end. [no] -> decision 'User has collection access?' [no] -> 'Explain no access "
        "(route: fallback)' -> end. [yes] -> decision 'Looks like a follow-up?' [yes] -> 'Rewrite into standalone "
        "question with LLM' -> merge; [no] -> merge -> 'Embed question' -> fork bar into two parallel actions "
        "'Vector search (top 20)' and 'BM25 keyword search (top 20)' -> join bar -> 'Reciprocal Rank Fusion, keep top "
        "5' -> decision 'Best similarity >= 0.618, or >= 0.57 with keyword agreement?' [no] -> 'Reply: couldn't "
        "find it (route: fallback)' -> end. [yes] -> 'Build prompt with numbered sources' -> 'Stream answer from LLM' "
        "-> 'Validate citations' -> 'Save answer, sources, latency (route: rag)' -> end node. " + UML)

    r.h2("Document Ingestion Workflow")
    r.p("Uploaded documents are processed by a background worker so that the interface stays responsive. Figure 5.7 "
        "shows the steps. The document's status moves from *queued* to *processing* (with a percentage) to *ready*, "
        "or to *failed* with an error message, and the documents page updates live.")
    r.figure_placeholder("Document ingestion workflow",
        "A horizontal pipeline diagram titled 'Document Ingestion'. Left: four small file icons labelled 'PDF', "
        "'DOCX', 'TXT / MD', 'URL'. Arrow into 'Upload & duplicate check (SHA-256)'. Then boxes in sequence: 'Background "
        "queue (status: queued)', 'Loader: extract text by page / heading, strip headers & footers', 'Chunker: ~800 "
        "chars, 150 overlap, keeps page & heading', 'Embedder: nomic-embed-text, 768-d vectors (GPU)', 'Store: "
        "ChromaDB + rebuild BM25 index', 'Status: ready (n chunks)'. A small progress bar icon above the embedder box "
        "labelled 'progress %'. A red side branch from the loader labelled 'no text / password protected -> status: "
        "failed'. " + STYLE)

    r.h2("Entity-Relationship Diagram")
    r.p("The ER diagram in Figure 5.8 shows the entities stored in SQLite and their relationships. A collection "
        "contains many documents; a user may access many collections and a collection may be shared by many users "
        "(through `user_collections`); a user has many conversations; a conversation has many messages; a bot message "
        "has many sources, each pointing to a document; a message may have one feedback rating; and an intent has "
        "many patterns and responses.")
    r.figure_placeholder("Entity-relationship diagram",
        "An entity-relationship diagram in crow's-foot notation with 13 entity boxes, each listing its primary key "
        "(PK) and main attributes: USERS (id PK, name, email, password_hash, role, theme, is_active); COLLECTIONS (id PK, "
        "name, description, icon, color); USER_COLLECTIONS (user_id FK, collection_id FK); DOCUMENTS (id PK, "
        "collection_id FK, title, source_type, status, chunk_count, file_hash); CONVERSATIONS (id PK, user_id FK, "
        "collection_id FK, title, updated_at); MESSAGES (id PK, conversation_id FK, role, content, route, intent_tag, "
        "confidence, latency_ms); MESSAGE_SOURCES (message_id FK, document_id FK, chunk_id, page, score, rank, cited); "
        "FEEDBACK (message_id PK/FK, rating, comment); INTENTS (id PK, tag, description, is_active); PATTERNS (id PK, "
        "intent_id FK, text); RESPONSES (id PK, intent_id FK, text); SETTINGS (key PK, value); MODEL_RUNS (id PK, "
        "algorithm, accuracy, f1, test_f1, is_active). Relationships: USERS 1-N CONVERSATIONS; USERS M-N COLLECTIONS "
        "via USER_COLLECTIONS; COLLECTIONS 1-N DOCUMENTS; CONVERSATIONS 1-N MESSAGES; MESSAGES 1-N MESSAGE_SOURCES; "
        "DOCUMENTS 1-N MESSAGE_SOURCES; MESSAGES 1-0..1 FEEDBACK; INTENTS 1-N PATTERNS; INTENTS 1-N RESPONSES. "
        "SETTINGS and MODEL_RUNS stand alone. " + UML)

    r.h2("Database Design")
    r.p("The database has thirteen tables. Chunk text and vectors are stored in ChromaDB; SQLite stores only "
        "references to chunks, plus a copy of each cited excerpt so that old answers still show their sources after a "
        "document is re-indexed. The most important tables are described below.")
    W = (1.5, 1.3, 1.1, 2.35)
    H = ["Field", "Type", "Constraint", "Description"]
    r.table("users", H, [
        ("id", "INTEGER", "PK, auto", "Unique user identifier"),
        ("name", "TEXT", "NOT NULL", "Display name"),
        ("email", "TEXT", "UNIQUE", "Login e-mail (case-insensitive)"),
        ("password_hash", "TEXT", "NOT NULL", "Salted password hash (Werkzeug)"),
        ("role", "TEXT", "admin / user", "Access level"),
        ("theme", "TEXT", "light / dark / system", "Preferred theme"),
        ("is_active", "INTEGER", "default 1", "Account enabled"),
        ("created_at, last_login_at", "TEXT", "", "Timestamps"),
    ], W, 10.5)
    r.table("collections and user_collections", H, [
        ("id", "INTEGER", "PK", "Collection identifier"),
        ("name", "TEXT", "UNIQUE", "Department name (HR, IT Support, Sales)"),
        ("description, icon, color", "TEXT", "", "Shown on chips and cards"),
        ("user_id", "INTEGER", "FK users", "user_collections: user"),
        ("collection_id", "INTEGER", "FK collections", "user_collections: collection the user may search"),
    ], W, 10.5)
    r.table("documents", H, [
        ("id", "INTEGER", "PK", "Document identifier"),
        ("collection_id", "INTEGER", "FK collections", "Owning collection"),
        ("title", "TEXT", "NOT NULL", "Title shown in citations"),
        ("source_type", "TEXT", "pdf/docx/txt/md/url", "File type"),
        ("path_or_url", "TEXT", "NOT NULL", "Stored file path or web address"),
        ("status", "TEXT", "queued/processing/ready/failed", "Ingestion state"),
        ("progress", "INTEGER", "0-100", "Percent complete while processing"),
        ("chunk_count, page_count, char_count", "INTEGER", "", "Indexing statistics"),
        ("file_hash", "TEXT", "", "SHA-256, used to skip duplicate uploads"),
        ("error", "TEXT", "", "Reason when status is failed"),
    ], W, 10.5)
    r.table("conversations and messages", H, [
        ("conversations.id", "INTEGER", "PK", "Conversation identifier"),
        ("conversations.user_id", "INTEGER", "FK users", "Owner"),
        ("conversations.title", "TEXT", "", "Shown in history; editable"),
        ("messages.id", "INTEGER", "PK", "Message identifier"),
        ("messages.conversation_id", "INTEGER", "FK conversations", "Parent conversation"),
        ("messages.role", "TEXT", "user / bot", "Who wrote the message"),
        ("messages.content", "TEXT", "NOT NULL", "Message text (Markdown for answers)"),
        ("messages.route", "TEXT", "intent / rag / fallback", "How the answer was produced"),
        ("messages.intent_tag, confidence", "TEXT, REAL", "", "Classifier output"),
        ("messages.latency_ms", "INTEGER", "", "Total response time"),
    ], W, 10.5)
    r.table("message_sources and feedback", H, [
        ("message_id", "INTEGER", "FK messages", "Answer that used the source"),
        ("document_id", "INTEGER", "FK documents", "Source document"),
        ("chunk_id, page, heading", "TEXT, INTEGER", "", "Location of the passage"),
        ("score, rank, cited", "REAL, INTEGER", "", "Retrieval score, source number, whether cited"),
        ("excerpt", "TEXT", "", "Passage text at answer time"),
        ("feedback.rating", "INTEGER", "-1 or +1", "Thumbs down / up"),
        ("feedback.comment", "TEXT", "", "Optional comment"),
    ], W, 10.5)
    r.table("intents, patterns, responses, settings and model_runs", H, [
        ("intents.tag", "TEXT", "UNIQUE", "Intent name, e.g. greeting"),
        ("patterns.text", "TEXT", "FK intents", "Training example sentence"),
        ("responses.text", "TEXT", "FK intents", "Reply chosen at random for the intent"),
        ("settings.key / value", "TEXT", "PK", "Model names, thresholds, top-k, chunk size, voice"),
        ("model_runs.algorithm", "TEXT", "", "naive_bayes / logistic_regression"),
        ("model_runs.accuracy, f1, test_f1", "REAL", "", "Cross-validation and held-out scores"),
        ("model_runs.details", "TEXT (JSON)", "", "Per-class report, confusion matrix"),
    ], W, 10.5)

    r.h2("Class Diagram")
    r.p("Although much of ConvoAI is organised as Python modules of functions, the core components are classes. "
        "Figure 5.9 shows the main classes and their relationships.")
    r.figure_placeholder("Class diagram of core components",
        "A UML class diagram with these classes (name, key attributes, key methods): 'IntentClassifier' (pipeline, "
        "algorithm, labels; predict(text), load(path)); 'VectorStore' (collection, model; add_document(), "
        "search(embedding, collection_ids, k), delete_document()); 'KeywordIndex' (bm25, hits; for_collections(), "
        "search(query, k)); 'Hit' (id, doc_id, title, page, heading, text, score); 'Retrieval' (query, hits, "
        "best_vector, relevant, threshold); 'OllamaEmbedder' (host, model; embed_query(), embed_documents()); "
        "'OllamaLLM' (host, model, temperature; stream(messages), complete(messages)); 'Transcriber' (model, device; "
        "transcribe(audio)); 'IngestWorker' (queue; submit(doc_id), run()); 'Router' module drawn as a class with "
        "handle(user, request) and _run(). Associations: Router uses IntentClassifier, OllamaEmbedder, VectorStore, "
        "KeywordIndex, OllamaLLM; Retrieval aggregates many Hit; VectorStore and KeywordIndex return Hit; "
        "IngestWorker uses VectorStore and OllamaEmbedder. " + UML)

    r.h2("Module Design")
    r.p("The source code is divided into seven packages. Table 5.7 lists the modules and their responsibilities.")
    r.table("Major modules", ["Module", "File(s)", "Purpose"], [
        ("Application", "app.py, config.py", "App factory, configuration, background warm-up"),
        ("Database", "models/database.py, schema.sql", "SQLite schema, migrations, data access"),
        ("Text pre-processing", "nlp/preprocess.py", "Normalise, tokenise, remove stop words, lemmatise"),
        ("Intent classifier", "nlp/classifier.py, nlp/train.py", "Train and compare NB/LR, tune threshold, predict"),
        ("Document loaders", "rag/loaders.py", "PDF/DOCX/TXT/MD/URL to text with page and heading"),
        ("Chunking and embeddings", "rag/chunker.py, rag/embeddings.py", "Overlapping chunks; nomic-embed-text vectors"),
        ("Vector and keyword store", "rag/store.py", "ChromaDB + BM25 per collection"),
        ("Hybrid retriever", "rag/retriever.py", "Vector + BM25, RRF fusion, relevance gate"),
        ("Prompting and LLM", "rag/prompt.py, rag/llm.py", "Grounded prompt, follow-up rewrite, streaming via Ollama"),
        ("Router", "services/router.py", "Full chat pipeline; stores messages and sources"),
        ("Ingestion", "services/ingest.py", "Background indexing worker"),
        ("Speech", "services/speech.py", "Whisper speech-to-text"),
        ("Analytics", "services/analytics.py", "Dashboard statistics"),
        ("Web layer", "routes/*.py, templates/, static/js/", "Pages and REST/SSE APIs; Material 3 UI"),
    ], widths=(1.6, 2.2, 2.45), size=10.5)

    r.h2("User Interface Design")
    r.p("The interface follows Google's Material 3 design system with a teal colour scheme, light and dark themes and "
        "a responsive layout. On desktop a navigation rail on the left links the chat and the administration pages; "
        "on phones it becomes a bottom navigation bar and the history becomes a slide-out drawer. The chat page has "
        "three areas: the conversation history, the conversation itself with collection filter chips and the message "
        "box, and a sources panel that opens beside the conversation when a citation is clicked. Each answer shows a "
        "route badge (*From documents*, *Quick reply* or *Not found in documents*) and its response time, which makes "
        "the internal pipeline visible during a demonstration. The interface screens are shown in Chapter 6 and "
        "Appendix A.")


def ch6(r):
    r.chapter_start("Implementation")
    r.p("This chapter describes how ConvoAI was implemented: the development environment, the project structure, "
        "and the algorithms and code of each major module, followed by the screens of the finished application. "
        "Code listings are shortened for readability; the complete source code accompanies this report.")
    r.h2("Development Environment and Setup")
    r.p("Development was done on Windows 11 using Python 3.11 in a virtual environment and Visual Studio Code. "
        "Ollama was installed as a Windows service and the three models were downloaded once. Two batch files make "
        "installation repeatable: `setup.bat` creates the virtual environment, installs the Python packages, downloads "
        "the NLTK data and the models, trains the intent classifier and loads the sample documents; `start.bat` "
        "starts Ollama if needed, starts the Flask server and opens the browser at http://127.0.0.1:5000.")
    r.code("""ollama pull qwen2.5:7b-instruct      # answer generation (~4.7 GB)
ollama pull llama3.2:3b              # faster fallback model (~2 GB)
ollama pull nomic-embed-text         # embeddings (~270 MB)

python -m venv .venv
.venv\\Scripts\\pip install -r requirements.txt
.venv\\Scripts\\python -m nlp.train            # train and compare the intent classifiers
.venv\\Scripts\\python tools/load_sample_docs.py
.venv\\Scripts\\python app.py                  # http://127.0.0.1:5000""", "Listing 6.1: Setting up the environment")

    r.h2("Project Structure")
    r.code("""ConvoAI/
|-- app.py, config.py      application factory and configuration
|-- models/                SQLite schema (schema.sql) and data access (database.py)
|-- nlp/                   preprocess.py, classifier.py, train.py, evaluate.py, responder.py
|-- rag/                   loaders.py, chunker.py, embeddings.py, store.py, retriever.py,
|                          prompt.py, llm.py, evaluate.py, answer_eval.py
|-- services/              router.py (chat pipeline), ingest.py, speech.py, analytics.py
|-- routes/                chat, chat_api, documents, admin, admin_api, analytics_api, speech_api
|-- templates/             base.html, chat.html, login.html, admin/*.html (Jinja2)
|-- static/                css/, js/ (chat.js, voice.js, documents.js, charts.js ...), vendor/
|-- data/                  intents.json, evaluation sets, sample documents
|-- tests/                 97 pytest tests
|-- tools/                 sample documents, screenshots, test report
`-- setup.bat, start.bat   one-click setup and start""", "Listing 6.2: Project structure")

    r.h2("Text Pre-processing Module")
    r.p("Short chat messages need careful pre-processing. Generic stop-word lists remove words such as *who*, *you* "
        "and *not*, which are exactly the words that distinguish \"who are you\" from \"how are you\", so ConvoAI keeps "
        "question words, pronouns and negations. The pipeline normalises Unicode and case, expands contractions "
        "(\"what's\" to \"what is\") and chat shorthand (\"thx\" to \"thanks\", \"pls\" to \"please\"), shortens "
        "repeated letters (\"hiiii\" to \"hii\"), tokenises with NLTK, removes the remaining stop words and lemmatises "
        "each token with WordNet, trying the verb form first and then the noun form.")
    r.code("""def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().replace("’", "'")
    for word, full in CONTRACTIONS.items():          # "what's" -> "what is"
        text = text.replace(word, full)
    text = _REPEATS.sub(r"\\1\\1", text)              # "hiiii" -> "hii"
    text = _NON_WORD.sub(" ", text)
    words = [SLANG.get(w, w) for w in text.split()]  # "thx" -> "thanks"
    return " ".join(words).strip()

def lemmatize(token: str) -> str:
    verb = _lemmatizer.lemmatize(token, wordnet.VERB)
    return verb if verb != token else _lemmatizer.lemmatize(token, wordnet.NOUN)

def preprocess(text: str) -> str:
    tokens = remove_stop_words(nltk.word_tokenize(normalise(text)))
    return " ".join(lemmatize(t) for t in tokens)""", "Listing 6.3: Text pre-processing (nlp/preprocess.py)")
    r.p("For example, *\"Hiiii, what's ur name??\"* becomes the token sequence *hii what is your name*, which is then "
        "converted into TF-IDF features.")

    r.h2("Intent Classification Module")
    r.p("The knowledge base `data/intents.json` defines 25 intents with 638 example patterns. Twenty-four are small-talk "
        "and assistant intents (greeting, goodbye, thanks, bot_identity, bot_capabilities, help_usage, joke, privacy, "
        "voice_help and others); the special intent `doc_query` holds examples of document questions so that the "
        "classifier learns what *not* to answer itself. Features combine word unigrams and bigrams with character "
        "2-4-grams, which makes the classifier robust to spelling mistakes. Two classifiers are trained with grid "
        "search over their main hyper-parameter using stratified 5-fold cross-validation, scored by macro-F1, then "
        "evaluated on a separate held-out set of 100 new phrasings. The better one is saved and activated.")
    r.code("""def build_pipeline(algorithm: str) -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)),
    ])
    if algorithm == "naive_bayes":
        clf = MultinomialNB()                                   # alpha tuned by grid search
    else:
        clf = LogisticRegression(max_iter=5000, class_weight="balanced")   # C tuned
    return Pipeline([("features", features), ("clf", clf)])

def predict(self, text: str) -> dict:
    proba = self.pipeline.predict_proba([preprocess(text)])[0]
    best = int(np.argmax(proba))
    return {"intent": self.pipeline.classes_[best], "confidence": float(proba[best])}""",
           "Listing 6.4: Intent classifier pipeline (nlp/classifier.py)")
    r.p("A message goes to the fast path only when the predicted intent is a small-talk intent and its confidence is "
        "at least the router threshold. The training script chooses this threshold (0.35) on the held-out set by "
        "minimising a cost in which a wrong quick reply counts twice as much as sending small talk to the documents, "
        "because a wrong canned reply is more confusing for the user than a slightly slower document search.")

    r.h2("Document Loading and Chunking Module")
    r.p("Each loader returns a list of *sections*, each with its text, page number and heading. The PDF loader reads "
        "page by page with pypdf and removes running headers and footers that repeat on most pages. The Word loader "
        "walks paragraphs and tables in order and starts a new section at each heading style. Markdown is split at "
        "headings, and web pages are cleaned with trafilatura to keep only the main article text.")
    r.p("The chunker splits each section recursively, preferring paragraph breaks, then line breaks, then sentence "
        "ends, then spaces, and packs the pieces greedily into chunks of up to 800 characters. The last 150 characters "
        "of each chunk are repeated at the start of the next one, so a sentence that falls on a boundary is still "
        "found. Before embedding, the document title and heading are prefixed to the chunk text, which gives short "
        "chunks the context they need.")
    r.code("""def _merge(pieces: list[str], size: int, overlap: int) -> list[str]:
    \"\"\"Greedily pack pieces up to `size`, carrying ~`overlap` chars into the next chunk.\"\"\"
    chunks, current = [], ""
    for piece in pieces:
        if current and len(current) + len(piece) > size:
            chunks.append(current.strip())
            tail = current[-overlap:]
            current = tail[tail.find(" ") + 1:]     # start the overlap at a word boundary
        current += piece
    if current.strip():
        chunks.append(current.strip())
    return chunks

def embedding_text(title: str, chunk: Chunk) -> str:
    context = " > ".join(p for p in (title, chunk.heading) if p)
    return f"{context}\\n{chunk.text}" if context else chunk.text""", "Listing 6.5: Chunking (rag/chunker.py)")

    r.h2("Vector Store and Keyword Index")
    r.p("All chunks are stored in one ChromaDB collection per embedding model, using cosine distance. Each chunk "
        "carries metadata: collection, document, title, page, heading and chunk index. Restricting a search to the "
        "collections a user may access is a metadata filter, so access control is enforced inside the database query "
        "itself. The BM25 index is built lazily from the same chunks for each set of collections and cached until a "
        "document is added, moved or deleted.")
    r.code("""def search(self, embedding, collection_ids, k=20) -> list[Hit]:
    res = self.collection.query(
        query_embeddings=[embedding], n_results=k,
        where={"collection_id": {"$in": list(collection_ids)}},     # access control
        include=["documents", "metadatas", "distances"])
    return [_hit(i, d, m, 1.0 - dist) for i, d, m, dist in
            zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])]""",
           "Listing 6.6: Collection-filtered vector search (rag/store.py)")

    r.h2("Hybrid Retrieval and Relevance Gate")
    r.p("Vector search finds passages with the same meaning even when the words differ, while BM25 finds exact "
        "terms such as plan names, amounts and product codes. ConvoAI runs both, takes the top 20 from each and "
        "combines them with Reciprocal Rank Fusion:")
    r.p("**RRF(d) = Σ 1 / (k + rank_i(d)),  with k = 60**", align=C, indent_first=False)
    r.p("where rank_i(d) is the position of chunk d in result list i. RRF needs no score normalisation, so a chunk "
        "that both methods rank highly rises to the top. Near-duplicate chunks are removed and the top five are kept. "
        "Figure 6.1 illustrates the process.")
    r.figure_placeholder("Hybrid retrieval with Reciprocal Rank Fusion",
        "An explanatory diagram. At the top, a query box: 'Can I carry forward the casual leaves?'. Two arrows down "
        "to two side-by-side ranked lists. Left list titled 'Vector search (meaning)' with five rows: '1. Leave "
        "policy - casual leave (0.60)', '2. Leave policy - earned leave', '3. Holidays', '4. Sick leave', '5. "
        "Work from home'. Right list titled 'BM25 (keywords)' with rows '1. Leave policy - casual leave', '2. Sick "
        "leave', '3. Leave encashment', '4. Earned leave', '5. Travel policy'. Coloured lines connect the same "
        "chunks across the two lists. Both lists feed into a box 'Reciprocal Rank Fusion: score = sum 1/(60 + rank)' "
        "which outputs 'Fused top 5' with 'Leave policy - casual leave' highlighted in teal at the top. Then a "
        "diamond 'Relevance gate: best similarity >= 0.618 or (>= 0.57 and keyword agrees)' with a green arrow 'pass "
        "-> LLM' and a red arrow 'fail -> not found'. " + STYLE)
    r.p("The relevance gate decides whether the documents contain an answer at all. It uses the best cosine "
        "similarity from vector search, which is comparable across queries. The threshold of 0.618 was chosen during "
        "evaluation because it separates every answerable test question from every off-topic one. During testing a "
        "real follow-up question, rewritten as \"Can I carry forward the casual leaves?\", scored 0.598 although the "
        "right passage was ranked first, so a grey zone was added: a score between 0.57 and 0.618 also passes when "
        "the keyword search independently ranks one of the top three vector passages first.")
    r.code("""def retrieve(store, query_vector, query, collection_ids, top_k=5,
             threshold=0.618, floor=0.57) -> Retrieval:
    vector_hits = store.search(query_vector, collection_ids, 20)
    keyword_hits = KeywordIndex.for_collections(store, collection_ids).search(query, 20)
    ranked = rrf_fuse([vector_hits, keyword_hits])

    best_vector = max((h.score for h in vector_hits), default=0.0)
    agrees = bool(keyword_hits) and keyword_hits[0].id in {h.id for h in vector_hits[:3]}
    relevant = best_vector >= threshold or (best_vector >= floor and agrees)
    return Retrieval(query, _dedupe(ranked)[:top_k], best_vector, relevant, threshold)

def rrf_fuse(result_lists, k=60):
    scores, by_id = {}, {}
    for hits in result_lists:
        for rank, hit in enumerate(hits, start=1):
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (k + rank)
            by_id.setdefault(hit.id, hit)
    return [by_id[i] for i in sorted(scores, key=scores.get, reverse=True)]""",
           "Listing 6.7: Hybrid retrieval and relevance gate (rag/retriever.py)")

    r.h2("Prompt Construction and Answer Generation")
    r.p("The retrieved chunks are numbered [1] to [5] and placed in the prompt with their document title, page and "
        "heading. The system prompt instructs the model to answer only from these sources, cite every fact, decline "
        "when the sources do not contain the answer, list each case when an answer depends on conditions, and quote "
        "numbers exactly. The last two exchanges of the conversation are included so that answers to follow-ups read "
        "naturally. Generation uses temperature 0.2 and a context window of 4,096 tokens, and the answer is streamed "
        "token by token. After generation, citation numbers that do not match a source are removed and the sources "
        "actually cited are marked.")
    r.code("""SYSTEM_PROMPT = \"\"\"You are ConvoAI, a helpful assistant for employees. Today is {today}.
Answer the user's question using ONLY the numbered sources provided. Follow these rules:
1. Cite every fact with its source number in square brackets right after it, like [1] or [2][3].
2. If the sources do not contain the answer, say "I couldn't find that in the documents you
   have access to." ... Never guess or use outside knowledge.
3. Be concise and direct. Start with the answer itself. ...
4. If the answer depends on conditions (approval levels, grades, cities, plans, durations),
   briefly list each case instead of giving only the largest or smallest value.
5. Quote numbers, amounts, dates and names exactly as they appear in the sources.
6. Do not mention "the sources" or "the context"; just answer naturally with citations.\"\"\"

def build_messages(question, hits, history):
    sources = "\\n\\n".join(f"[{i}] {source_label(h)}\\n{h.text}" for i, h in enumerate(hits, 1))
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(today=...)}]
    messages += last_two_exchanges(history)
    messages.append({"role": "user", "content": f"Sources:\\n{sources}\\n\\nQuestion: {question}"})
    return messages""", "Listing 6.8: Grounded prompt (rag/prompt.py)")

    r.h2("Follow-up Question Rewriting")
    r.p("A follow-up such as \"and can I carry them forward?\" cannot be searched on its own because *them* has no "
        "meaning without the conversation. When a message contains reference words (it, that, them, what about, "
        "also and so on) and there is earlier conversation, the language model is asked to rewrite it as a single "
        "standalone question without adding any facts. In the example the rewrite is \"Can I carry forward the casual "
        "leaves?\", which retrieves the right passage. The interface shows the status \"Understanding your "
        "follow-up...\" while this happens.")

    r.h2("Chat Router and Streaming API")
    r.p("The router in `services/router.py` ties all stages together. It is written as a Python generator that "
        "yields events: *start*, *status*, *sources*, *token*, *done* and *error*. The same generator serves the "
        "plain JSON endpoint and the streaming endpoint, which sends each event to the browser as a Server-Sent "
        "Event. Every user and bot message is saved with its route, intent, confidence, latency, per-stage timings "
        "and sources, which feeds the analytics dashboard.")
    r.code("""def _run(user, req, turn):
    user_message_id = db.add_message(conversation_id, "user", text)
    intent = classify(text, user.name)                       # 1. intent fast path
    if intent["route"] == "intent":
        yield finish(intent["reply"], "intent", intent=intent["intent"])
        return
    query = text
    if P.needs_rewrite(text, history):                       # 2. follow-up rewriting
        yield {"type": "status", "text": "Understanding your follow-up..."}
        query = llm.complete(P.rewrite_messages(text, history), max_tokens=80)
    vector = get_embedder(app).embed_query(query)            # 3. hybrid retrieval
    result = retrieve(store, vector, query, req["scope_ids"], top_k=5,
                      threshold=0.618, floor=0.57)
    if not result.relevant:
        yield finish("I couldn't find anything about that in your documents. ...", "fallback")
        return
    yield {"type": "sources", "sources": sources}
    for token in llm.stream(P.build_messages(query, result.hits, history)):   # 4. generate
        yield {"type": "token", "text": token}
    answer = P.remove_invalid_citations("".join(parts), len(sources))
    yield finish(answer, "rag", sources=sources)

@bp.post("/chat/stream")
def chat_stream():
    req = _parse_request()
    events = (f"data: {json.dumps(e)}\\n\\n" for e in router.handle(current_user, req))
    return Response(stream_with_context(events), mimetype="text/event-stream")""",
           "Listing 6.9: Chat router and streaming endpoint (services/router.py, routes/chat_api.py)")

    r.h2("Voice Input and Output")
    r.p("Voice input is recorded in the browser with the MediaRecorder API. The recorder measures the sound level and "
        "stops automatically about 1.5 seconds after the user stops speaking, or after 8 seconds of silence. The audio "
        "is posted to `/api/speech/transcribe`, where faster-whisper (Whisper small, int8 on the CPU) transcribes it "
        "with voice activity detection, beam size 1 and a vocabulary hint built from document titles and collection "
        "names. Segments that Whisper itself rates as probably not speech are dropped. The text is placed in the "
        "message box and sent. Answers can be read aloud with the speech synthesis voices installed on the computer; "
        "citation numbers are removed before speaking.")
    r.code("""segments, info = model.transcribe(
    io.BytesIO(audio), language="en", beam_size=1, vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500},
    condition_on_previous_text=False, initial_prompt=hint)
kept = [s.text.strip() for s in segments if s.no_speech_prob < 0.6]""",
           "Listing 6.10: Local speech-to-text (services/speech.py)")

    r.h2("Administration, Analytics and Metrics")
    r.p("The administration pages are built from Jinja2 templates and small JavaScript modules that call the REST "
        "API. The Documents page supports drag-and-drop upload, adding a URL, live status, viewing chunks, renaming, "
        "moving between collections, re-indexing, deleting and a *Test retrieval* panel that shows vector and keyword "
        "results side by side. The Intents page lists the knowledge base, offers an editor for patterns and "
        "responses, a *Try a message* box that shows every NLP pipeline stage, and a Retrain button. Settings are "
        "validated against a schema, so invalid values (for example 50 sources per answer) are rejected with the "
        "field highlighted. The Analytics page shows questions asked, the share answered from documents, response "
        "times, the most-cited documents, questions by collection, content gaps (questions the documents could not "
        "answer) and answers marked unhelpful. The Metrics page shows the classifier comparison, confusion matrix, "
        "threshold analysis and retrieval evaluation, with a button to re-run the evaluation.")

    r.h2("Screens of the Application")
    r.p("The following screenshots, taken from the running application with the Nimbus Technologies sample documents, "
        "show the main screens. Further screens are included in Appendix A.")
    r.screenshot("Chat home page with suggested questions", SS / "01-chat-home.png")
    r.screenshot("Answer with citations and a follow-up question", SS / "02-chat-answer.png")
    r.screenshot("Sources panel showing the cited passage", SS / "03-sources-panel.png")
    r.screenshot("Three answer routes: from documents, not found, quick reply", SS / "04-routes.png")
    r.screenshot("Step-by-step answer from the IT Support Guide", SS / "15-chat-vpn-light.png")
    r.screenshot("Admin overview with system status", SS / "07-admin-overview.png")
    r.screenshot("Documents page with upload area and library", SS / "08-documents.png")
    r.screenshot("Chunk viewer showing how a document was split", SS / "18-chunk-viewer.png")
    r.screenshot("Intents page with the NLP pipeline for a test message", SS / "19-intent-try.png")
