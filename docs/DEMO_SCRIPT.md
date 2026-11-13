# Viva demo script (about 12 minutes)

A tested walkthrough that shows every part of the synopsis (NLP pipeline, intent classification, analytics, REST API) and the RAG extension, in an order that tells a story: *small talk → document answers with proof → no guessing → voice → new knowledge in seconds → measured quality.*

## Before the viva (do this 15 minutes early)

- [ ] Laptop on charger. Close Chrome tabs, games and other GPU or heavy apps. The chat model needs about 5 GB of GPU memory.
- [ ] Double-click **`start.bat`**, wait for the browser, open **Admin → Overview**: Database, Ollama and both models should be green.
- [ ] **Warm up:** ask one question in the chat, so the model is loaded (the first answer after a restart takes about 15 s).
- [ ] Click 🎤 once and **allow the microphone**; check the level meter moves when you speak.
- [ ] Keep **`tools/demo_docs/Cafeteria and Wellness Guide.md`** ready in File Explorer for the live upload (step 6).
- [ ] Zoom the browser to 110–125% so the examiners can read it. Pick light theme for a projector.
- [ ] Optional: start a **New chat** so the history panel looks tidy.

If anything fails, see *If something goes wrong* at the end.

## The walkthrough

### 1. Problem and idea (1 min, talk only)

> "Employees ask the same policy questions every day. Keyword bots break when the wording changes, and cloud chatbots send company data outside. ConvoAI keeps everything on this laptop. A classic NLP intent classifier handles small talk instantly, and Retrieval-Augmented Generation answers from the company's own documents, with citations, and refuses when the documents don't say."

Show the diagram at the top of `README.md` (*How it works*).

### 2. Small talk: the classic NLP part (1 min)

Type **`hi`** and then **`thx u r great`**.

Point out the **Quick reply** badge and the time of about 0.0 s. *"The intent classifier answered this, without searching or using the large model."*

Open **Admin → Intents → Try a message**, type `thx u r great`, and show the steps: normalised (`thanks you are great`), tokens, stop-words removed, lemmas, then TF-IDF and Logistic Regression. *"That's chapter 4 of the synopsis: tokenisation, stop-word removal, lemmatisation, TF-IDF, classification."*

### 3. A document answer with proof (2 min)

Back in **Chat**: click the suggestion **"How many casual leaves do I get per year?"**

- The status steps flash by (*Searching your documents… Writing the answer…*); the answer streams in: *12 days*.
- Click the citation **2**: the **Sources** panel opens at the handbook passage on page 4 with "casual" highlighted. *"Every fact can be checked."*

Then ask the follow-up **"and can I carry them forward?"**. *"It rewrote that into a full question about carrying forward casual leave before searching."* The answer: no, it lapses on 31 December.

### 4. It doesn't guess (1 min)

Ask **"What is the capital of France?"**: *Not found in documents*. *"A normal chatbot would answer from general knowledge. Ours is deliberately restricted to the documents. A similarity threshold, tuned on test questions, decides when nothing relevant was found."*

### 5. Voice (1 min)

Click 🎤 and say **"How do I connect to the VPN from home?"**. Recording stops by itself; the text appears; the answer is read aloud. *"Speech recognition is Whisper running on this laptop's CPU; the voice is a Windows voice, so no audio leaves the machine."*

### 6. New knowledge in seconds (2 min)

**Admin → Documents** → collection **General** → drag in **`Cafeteria and Wellness Guide.md`**. It goes *Processing → Ready* in a few seconds. Click ☰ to show its chunks.

Back to **Chat**: **"Which day is millet day in the cafeteria?"** → *Friday*, cited from the new document.

> "No retraining: the document was split, embedded and indexed. That's the main advantage of RAG over training a model on the documents."

(Optional: delete it afterwards with 🗑.)

### 7. Measured quality (2–3 min)

- **Admin → Analytics:** questions, share answered from documents, response times, and **Content gaps** (*"questions people asked that the documents couldn't answer: the admin's to-do list"*).
- **Admin → Metrics:**
  - Naive Bayes vs **Logistic Regression** (0.890 vs **0.910** accuracy on 100 unseen phrasings).
  - The **confusion matrix**.
  - The strip plot: *"every answerable test question is right of the line and every off-topic one left. That's how the 'not found' threshold of 0.618 was chosen."*
- Mention the end-to-end results from `docs/TEST_REPORT.md`: **92.7% correct facts, 100% correct citations, all off-topic questions declined, first words in 1.6 s**.

### 8. Close (30 s)

> "Limitations: a 7-billion-parameter model on a laptop GPU still misreads rules split across two sections, and quality depends on how documents are written. Next steps: a larger model, OCR for scanned PDFs, and WhatsApp/Teams integration."

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Answers say Ollama can't be reached | Small talk and the admin pages still work. Start Ollama from the Start menu (or `ollama serve`) and ask again |
| First answer very slow | The model is loading; say so ("loading 4.7 GB onto the GPU") and continue. That's why you warm up beforehand |
| Microphone doesn't work | Skip step 5, or type the question and click 🔊 on the answer to show read-aloud |
| Projector or laptop problem | Walk through `docs/screenshots/` and `docs/TEST_REPORT.md` |

---

## Likely viva questions

**Why RAG instead of training (fine-tuning) a model on the documents?**
Fine-tuning needs a GPU, hours of training and redoing whenever a policy changes, and it still can't show where an answer came from. With RAG, new documents can be searched in seconds, every answer cites its source, and the model is told to answer only from those sources, which limits hallucination.

**Then why keep the intent classifier?**
It makes small talk instant (about 2 ms instead of about 3 s), works even when Ollama is down, keeps the synopsis's NLP pipeline (tokenise, stop-words, lemmatise, TF-IDF, classify), and routes messages. Its `doc_query` class marks real document questions.

**Why did Logistic Regression beat Naive Bayes?**
NB assumes features are independent and its probabilities are poorly calibrated. LR learns weights for overlapping word and character n-grams and gives better-calibrated confidence, which the router's threshold depends on. Measured: test macro-F1 0.905 vs 0.875.

**Why are cross-validation scores (0.76) lower than the test scores (0.91)?**
Several intents have fewer than 20 examples, and 5-fold CV holds out 20% of an already small class. The held-out phrasings are typical everyday messages. Both are reported; neither was used to pick the final model's hyper-parameters except through CV.

**How does hybrid search work? What is RRF?**
Two rankings: cosine similarity of `nomic-embed-text` vectors (meaning) and BM25 (keywords). Reciprocal Rank Fusion scores each chunk as Σ 1/(60 + rank) across both lists, so chunks ranked well by both rise. It needs no score normalisation. Hybrid had the best MRR (0.935).

**What are hit@k and MRR?**
Hit@k: was the right passage in the top k? MRR: the average of 1/rank of the first correct passage (1 if first, 0.5 if second…). Hybrid: hit@5 0.978, MRR 0.935.

**How do you stop the model from making things up?**
(1) A relevance gate: if no passage is similar enough, it answers "not found" without asking the model; (2) the prompt says to use only the numbered sources and to say when they don't contain the answer; (3) citations on every fact, which the user can open; (4) low temperature (0.2). Measured: all off-topic questions declined, and 97.6% of answers contained only numbers present in the sources.

**How was the 0.618 threshold chosen? What is the floor?**
46 answerable and 15 off-topic test questions: answerable scored 0.636–0.857, off-topic up to 0.600. 0.618 is midway. Real follow-ups can score just below it, so between 0.57 and 0.618 a question still passes if keyword search independently finds the same passage. Measured on 85 answerable and 18 off-topic questions: none blocked, none let through.

**Why a local model instead of ChatGPT or Claude?**
Privacy (policies, salaries and customer data stay on the machine), no running cost, and it works offline. The trade-off is a smaller model (7B), measured honestly in the report.

**Why chunks of 800 characters with 150 overlap?**
Small enough that five fit the 4096-token context with room for the answer, large enough to hold a full rule. Overlap stops a sentence being cut between chunks. Chunks never cross a page or heading, so citations stay exact.

**How are follow-ups handled?**
If a message is short or uses words like "it" or "what about", the model first rewrites it into a standalone question using the last two exchanges. The rewrite (not the original) is searched.

**What about security?**
CSRF tokens on every form and API call; the model's output is rendered as Markdown with raw HTML escaped (no XSS); URL documents refuse local and private network addresses (SSRF); uploads are size- and type-checked and stored under random names; with sign-in on, every search is filtered to the user's collections and admin APIs return 403 to users.

**How would it scale to a real company?**
Swap SQLite for PostgreSQL and the Flask dev server for a production server, run Ollama (or vLLM) on a GPU server, and keep the same pipeline. ChromaDB handles hundreds of thousands of chunks. The single ingestion worker would become a job queue.

**What were the hardest problems?**
(1) Speed: `localhost` on Windows added 2 s per call (IPv6 first), and model reloads caused by changing context sizes; fixed by using 127.0.0.1 and one context size (first token went from 8 s to 1.6 s). (2) A follow-up wrongly answered "not found", found while taking screenshots; fixed with the keyword-agreement grey zone. (3) Choosing thresholds from data instead of guessing.
