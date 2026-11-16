"""Chapters 1-4."""
from front import ROOT
SS = ROOT / "report" / "screenshots"

STYLE = ("Clean, flat, professional technical diagram on a pure white background, navy (#1F3A68), teal (#006A6A) "
         "and soft grey palette, rounded rectangles, thin dark arrows, Times New Roman or similar serif labels, "
         "all text horizontal and legible, no 3D, no gradients, no people, no watermark, 16:9 landscape, "
         "suitable for printing in an academic project report.")


def ch1(r):
    r.chapter_start("Introduction", first=True)
    r.h2("Overview")
    r.p("Every organisation runs on knowledge written in documents: the employee handbook, the leave policy, the "
        "travel and expense rules, the IT support guide, the information security guidelines and the product price "
        "list. Employees need small pieces of this knowledge many times a day. How many casual leaves do I get? Can I "
        "carry them forward? What is the hotel limit in a metro city? How do I connect to the VPN from home? Who "
        "approves a twenty percent discount? The answers exist, but they are spread across long PDF and Word files, "
        "and finding them means opening the right file, searching for the right keyword and reading several pages.")
    r.p("Conversational agents, or chatbots, offer a natural way to reach such knowledge: the user asks a question "
        "in plain language and receives a direct reply. Early chatbots matched keywords or followed fixed menus. "
        "Machine-learning chatbots improved on this by learning *intents* from labelled example sentences, so that "
        "\"hi\", \"hello there\" and \"good morning\" are all recognised as a greeting. Such intent-based bots work "
        "well for a small, fixed set of questions, but every new answer must be written and every new question "
        "must be added to the training data by hand. They cannot answer questions about the content of a new "
        "40-page policy document.")
    r.p("Large Language Models (LLMs) changed what a chatbot can do. A model such as Qwen2.5 or Llama 3 can read "
        "a passage and answer a question about it in fluent language. On their own, however, LLMs answer from what "
        "they memorised during training: they know nothing about a particular company's policies and may confidently "
        "invent an answer, a problem known as *hallucination*. **Retrieval-Augmented Generation (RAG)** solves this "
        "by first retrieving the passages of the organisation's documents that are relevant to the question and "
        "then asking the model to answer only from those passages, citing them.")
    r.p("**ConvoAI** is an intelligent conversational assistant that combines both approaches. It keeps the "
        "classical NLP pipeline and intent classifier proposed in the project synopsis, which now acts as a fast "
        "first stage for greetings, thanks and questions about the assistant itself. Every other question is "
        "answered by a RAG pipeline over the organisation's own documents, using hybrid semantic and keyword search, "
        "a relevance gate that declines out-of-scope questions, and a language model that runs locally through "
        "Ollama. The application is a Flask web application with a Material 3 interface, streaming answers with "
        "clickable citations, voice input, departmental document collections, an administration panel and analytics. "
        "Everything, including the language model, the search index and speech recognition, runs on one computer, "
        "so no document or question ever leaves the organisation.")
    r.p("For demonstration and evaluation the project uses a fictional mid-sized software company, *Nimbus "
        "Technologies*, with six sample documents in four collections: General, HR, IT Support and Sales. These "
        "include an employee handbook (PDF), a travel and expense policy (Word), an IT support guide (Markdown), "
        "information security guidelines (text) and a product and pricing guide (Word).")

    r.h2("Problem Statement")
    r.p("Organisations and their employees face the following problems when looking for information in internal "
        "documents:")
    r.bullets([
        "Repetitive queries: HR, IT and sales teams answer the same questions every day. Each answer takes a few "
        "minutes of a skilled person's time and is not available outside working hours.",
        "Information buried in long documents: policies run to dozens of pages. Finding one rule means opening the "
        "right file and reading around it, and the answer often depends on conditions in another section.",
        "Keyword search fails on paraphrases: a search for \"carry forward leave\" will not find a sentence that says "
        "\"unused casual leave lapses at the end of the year\".",
        "Rigid rule-based and intent-only chatbots: they answer only questions that someone anticipated and scripted, "
        "and must be retrained whenever the documents change.",
        "Hallucination in generic AI assistants: a general-purpose LLM does not know the company's rules and may "
        "invent plausible but wrong answers without any way for the user to check them.",
        "Privacy and confidentiality: cloud chatbot services require uploading internal documents and questions to "
        "a third party, which many organisations cannot allow.",
    ])
    r.p("The problem addressed by this project is therefore: *to design and build a conversational assistant that "
        "understands natural-language questions, answers them accurately from an organisation's own documents with "
        "verifiable citations, declines questions the documents do not cover, and runs entirely on the "
        "organisation's own hardware.*")

    r.h2("Significance and Relevance of Work")
    r.p("The work is significant for three reasons. First, it addresses a real and common need. Internal help desks "
        "in companies, colleges and government offices spend much of their time on questions whose answers are already "
        "written down. An assistant that answers these instantly and cites the source frees staff for work that needs "
        "judgement, and gives employees answers at any hour.")
    r.p("Second, it shows that modern generative AI can be used responsibly on modest hardware. ConvoAI runs a "
        "7-billion-parameter model on a laptop GPU with 6 GB of memory, keeps all data local, shows the exact passage "
        "behind every statement and refuses rather than guesses. These properties of privacy, transparency and honesty "
        "are what organisations need before they can trust an AI assistant.")
    r.p("Third, the project connects classical NLP with current techniques in a measurable way. The intent "
        "classifier, built from tokenisation, stop-word removal, lemmatisation and TF-IDF, is evaluated with "
        "precision, recall, F1 and a confusion matrix, as proposed in the synopsis. Retrieval is evaluated with "
        "Hit@k and Mean Reciprocal Rank, and complete answers are evaluated for factual correctness, citation "
        "accuracy and grounding. This makes the project useful as a study of where each technique helps and where "
        "it still fails.")

    r.h2("Objectives")
    r.p("The main objective is to build a web-based assistant that answers natural-language questions from an "
        "organisation's own documents, with citations, while keeping all data on the local machine. The specific "
        "objectives are:")
    r.bullets([
        "Natural-language understanding: implement an NLP pipeline (normalisation, tokenisation, stop-word removal, "
        "lemmatisation, TF-IDF) and compare intent classifiers (Multinomial Naive Bayes and Logistic Regression) for "
        "routing messages and answering small talk.",
        "Grounded answering: implement Retrieval-Augmented Generation, covering document ingestion, chunking, "
        "embeddings, hybrid vector and keyword retrieval, and answer generation with a local language model that "
        "must cite its sources.",
        "Honest fallback: decline questions that the documents do not cover instead of guessing, using a tuned "
        "relevance threshold.",
        "Context awareness: understand follow-up questions such as \"and can I carry them forward?\" by rewriting "
        "them into standalone questions using the conversation history.",
        "Usable interface: provide a modern, responsive web interface with streaming answers, conversation history, "
        "light and dark themes, voice input and read-aloud, and a phone layout.",
        "Administration and analytics: let administrators manage documents, collections, intents, users and "
        "settings, and show usage, response times, most-cited documents and unanswered questions.",
        "Privacy: run the language model, embeddings, speech recognition and storage on the local machine.",
        "Evaluation: measure classifier, retrieval and end-to-end answer quality and response time on held-out "
        "test sets.",
    ])

    r.h2("Scope of the Project")
    r.p("The project covers a complete, working assistant for a single organisation: document upload (PDF, DOCX, TXT, "
        "Markdown and web pages by URL); departmental collections with optional per-user access control; the hybrid "
        "intent and RAG pipeline; streaming chat with citations and a sources panel; local speech-to-text and "
        "read-aloud; an administration panel; analytics; a model-metrics page; automated tests and evaluation "
        "scripts; and one-click setup and start scripts for Windows.")
    r.p("The following are outside the scope of this version: optical character recognition (OCR) of scanned PDFs, "
        "answers in languages other than English, integration with external messaging platforms such as Microsoft "
        "Teams or WhatsApp, and multi-server deployment.")

    r.h2("Methodology")
    r.p("The system was developed iteratively in ten phases, from environment setup to documentation, with each "
        "phase ending in a working, tested increment. The methodology of the running system is a pipeline of five "
        "stages, shown in Figure 1.1.")
    r.figure_placeholder("Methodology of ConvoAI",
        "A left-to-right methodology flowchart titled 'ConvoAI Methodology'. Five large numbered rounded boxes "
        "connected by arrows: (1) 'Document Ingestion' with a small document icon and the sub-text 'PDF, DOCX, TXT, "
        "MD, URL -> chunks -> embeddings'; (2) 'Message Classification' with sub-text 'NLP pipeline + TF-IDF + "
        "Logistic Regression'; (3) 'Hybrid Retrieval' with sub-text 'Vector search + BM25 + Reciprocal Rank Fusion'; "
        "(4) 'Relevance Gate' drawn as a diamond with two exits, 'Not found' to the bottom and 'Relevant' to the "
        "right; (5) 'Grounded Answer' with sub-text 'Local LLM (Qwen2.5-7B) + citations'. A branch from box 2 going "
        "down labelled 'Small talk -> Instant reply'. Below the row, a thin dashed rounded band labelled 'Runs "
        "entirely on the local computer'. " + STYLE)
    r.p("**Document ingestion:** administrators upload documents into collections. Each document is converted to "
        "text page by page or heading by heading, split into overlapping chunks of about 800 characters, converted "
        "into 768-dimensional embedding vectors by the nomic-embed-text model and stored in ChromaDB along with its "
        "collection, title, page and heading. A BM25 keyword index is built over the same chunks.", indent_first=False)
    r.p("**Message classification:** each user message passes through the NLP pipeline and the Logistic Regression "
        "intent classifier. If the message is confidently small talk (for example a greeting or thanks), a "
        "predefined response is returned immediately.", indent_first=False)
    r.p("**Hybrid retrieval:** other messages are treated as document questions. Follow-ups are rewritten into "
        "standalone questions by the language model, and the question is searched both by meaning (vector "
        "similarity) and by keywords (BM25). The two rankings are combined with Reciprocal Rank Fusion and the top "
        "five chunks are kept.", indent_first=False)
    r.p("**Relevance gate:** if the best semantic similarity is below a tuned threshold (0.618), the assistant "
        "replies that it could not find the answer, instead of guessing.", indent_first=False)
    r.p("**Grounded answer:** the retrieved chunks are numbered and given to the language model with strict "
        "instructions to answer only from them and to cite each fact as [1], [2] and so on. The answer is streamed "
        "to the browser word by word, and every message is stored with its route, timing and sources.",
        indent_first=False)

    r.h2("Organization of the Report")
    r.p("This report is organised into nine chapters:")
    r.bullets([
        "Chapter 1, Introduction: overview, problem statement, significance, objectives, scope and methodology.",
        "Chapter 2, Literature Survey: a review of research on chatbots, intent classification, retrieval, "
        "Retrieval-Augmented Generation and speech recognition, with the research gap this project addresses.",
        "Chapter 3, System Requirements and Specifications: hardware and software requirements, functional and "
        "non-functional requirements, and the technologies used.",
        "Chapter 4, System Analysis: the existing system and its limitations, the proposed system and its advantages, "
        "and the feasibility study.",
        "Chapter 5, System Design: architecture, use case, data flow, sequence, activity, entity-relationship and "
        "class diagrams, the database design and module design.",
        "Chapter 6, Implementation: the development environment, project structure, the algorithms and the code of "
        "each major module, and the user interface.",
        "Chapter 7, Testing: testing methods, automated tests, evaluation of the classifier, retrieval and answers, "
        "performance, and test cases.",
        "Chapter 8, Novelty in Proposed System and Future Enhancement.",
        "Chapter 9, Findings and Conclusion.",
    ])
    r.p("The report ends with the bibliography and appendices containing screenshots, abbreviations and the user "
        "guide.")


def ch2(r):
    r.chapter_start("Literature Survey")
    r.p("A literature survey reviews earlier research and systems in the field of the project, so that the project "
        "builds on what is known and addresses a real gap. This chapter reviews work in five areas that ConvoAI "
        "combines: conversational agents, text classification for intent detection, information retrieval, "
        "retrieval-augmented language models and speech recognition. For each work, the contribution and the "
        "limitations relevant to this project are noted.")

    papers = [
        ("ELIZA: A Computer Program for the Study of Natural Language Communication between Man and Machine",
         "Joseph Weizenbaum (1966), Communications of the ACM",
         "ELIZA was one of the first chatbots. It matched the user's sentence against keyword patterns and "
         "transformed it into a reply using scripted templates, most famously imitating a psychotherapist. ELIZA "
         "showed that even simple pattern matching can create the impression of conversation.",
         ["It has no understanding of meaning; any sentence outside the scripted patterns gets a generic reply.",
          "All knowledge is hand-written into the script, so it cannot answer factual questions from documents."]),
        ("An Overview of Chatbot Technology",
         "Eleni Adamopoulou and Lefteris Moussiades (2020), Artificial Intelligence Applications and Innovations, Springer",
         "This survey classifies chatbots by knowledge domain, service, goal and response-generation method "
         "(rule-based, retrieval-based and generative). It describes the typical architecture of natural-language "
         "understanding, dialogue management and response generation, and discusses open problems such as context "
         "handling and evaluation.",
         ["Retrieval-based bots in the survey select from predefined responses rather than reading documents.",
          "Generative bots are described as fluent but hard to control, with no mechanism for grounding or citations."]),
        ("Rasa: Open Source Language Understanding and Dialogue Management",
         "Tom Bocklisch, Joey Faulkner, Nick Pawlowski and Alan Nichol (2017), NIPS Workshop on Conversational AI",
         "Rasa is an open-source framework that separates natural-language understanding (intent classification and "
         "entity extraction) from dialogue management. Intents are learned from labelled examples with machine "
         "learning, which made intent-based chatbots practical for organisations.",
         ["Every intent, example and response must be written by hand; a new policy document requires new training data.",
          "It answers only anticipated questions and cannot read unstructured documents."]),
        ("A Comparison of Event Models for Naive Bayes Text Classification",
         "Andrew McCallum and Kamal Nigam (1998), AAAI Workshop on Learning for Text Categorization",
         "This paper compares the multivariate Bernoulli and multinomial event models for Naive Bayes text "
         "classification and shows that the multinomial model performs better, especially with larger vocabularies. "
         "Multinomial Naive Bayes with TF-IDF or count features became a standard baseline for short-text "
         "classification, and it is one of the two classifiers compared in ConvoAI.",
         ["The independence assumption ignores word order and correlations between features.",
          "Probability estimates are often over-confident, which matters when a confidence threshold decides routing."]),
        ("The Probabilistic Relevance Framework: BM25 and Beyond",
         "Stephen Robertson and Hugo Zaragoza (2009), Foundations and Trends in Information Retrieval",
         "The authors explain the probabilistic model behind BM25, the ranking function used by most search engines. "
         "BM25 scores a document by the frequency of query terms, weighted by how rare each term is across the "
         "collection and normalised by document length. It remains a strong baseline for keyword retrieval.",
         ["BM25 matches exact terms only; it misses paraphrases and synonyms (\"leave\" vs \"time off\").",
          "It gives no calibrated relevance score that could decide whether an answer exists at all."]),
        ("Dense Passage Retrieval for Open-Domain Question Answering",
         "Vladimir Karpukhin, Barlas Oguz, Sewon Min and others (2020), EMNLP",
         "Dense Passage Retrieval (DPR) encodes questions and passages into dense vectors with neural encoders and "
         "retrieves passages by vector similarity. It outperformed BM25 on several open-domain question-answering "
         "benchmarks by 9 to 19 percentage points in top-20 accuracy, establishing semantic vector search for "
         "question answering.",
         ["Dense retrieval can miss passages that depend on exact names, codes or numbers that keyword search finds easily.",
          "Training the encoders needs large labelled datasets and GPU resources."]),
        ("Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods",
         "Gordon V. Cormack, Charles L. A. Clarke and Stefan Büttcher (2009), ACM SIGIR",
         "Reciprocal Rank Fusion (RRF) combines several ranked result lists by summing 1/(k + rank) for each "
         "document. It needs no score normalisation and no training, yet it outperformed more complex fusion methods. "
         "ConvoAI uses RRF to combine vector and BM25 rankings.",
         ["RRF uses only ranks, so it cannot tell whether any of the results is actually relevant.",
          "The paper evaluates document retrieval, not passage retrieval for generated answers."]),
        ("Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
         "Patrick Lewis, Ethan Perez, Aleksandra Piktus and others (2020), NeurIPS",
         "This paper introduced Retrieval-Augmented Generation, which combines a retriever over a document index with "
         "a sequence-to-sequence generator. The generator conditions on retrieved passages, producing answers that are "
         "more specific and factual than a model using only its parameters, and the knowledge can be updated by "
         "replacing the index without retraining.",
         ["The original system retrieves from Wikipedia with a model trained end to end; it is not designed for "
          "small private document sets or local hardware.",
          "It provides no mechanism to decline when retrieval finds nothing relevant."]),
        ("Retrieval-Augmented Generation for Large Language Models: A Survey",
         "Yunfan Gao, Yun Xiong, Xinyu Gao and others (2023), arXiv:2312.10997",
         "This survey organises RAG research into naive, advanced and modular RAG. It discusses chunking, "
         "embedding models, hybrid search, query rewriting, re-ranking and evaluation of retrieval and generation. "
         "Several techniques used in ConvoAI, such as query rewriting for follow-ups and hybrid retrieval, follow the "
         "advanced RAG patterns described here.",
         ["Most systems surveyed rely on large cloud-hosted models.",
          "The survey notes that evaluation of grounding and refusal behaviour is still immature."]),
        ("Survey of Hallucination in Natural Language Generation",
         "Ziwei Ji, Nayeon Lee, Rita Frieske and others (2023), ACM Computing Surveys",
         "The authors define hallucination as generated content that is nonsensical or unfaithful to the source, and "
         "review its causes and mitigation methods across summarisation, dialogue and question answering. Grounding "
         "generation in retrieved evidence and verifying outputs against sources are among the recommended "
         "mitigations.",
         ["Mitigation methods are mostly evaluated on benchmarks rather than deployed systems.",
          "Automatic hallucination detection remains unreliable, so user-visible citations remain important."]),
        ("Robust Speech Recognition via Large-Scale Weak Supervision (Whisper)",
         "Alec Radford, Jong Wook Kim, Tao Xu and others (2023), ICML",
         "Whisper is a speech recognition model trained on 680,000 hours of multilingual audio. It approaches human "
         "robustness on many benchmarks without fine-tuning and can run locally. ConvoAI uses the faster-whisper "
         "implementation of the Whisper small model for on-device voice input.",
         ["Larger models need a GPU for real-time use; smaller ones make more errors on uncommon words.",
          "It can produce text for silence or noise, which must be filtered."]),
    ]
    for title, authors, summary, lims in papers:
        r.h2(title)
        r.p(f"*Authors: {authors}*", indent_first=False, space_after=2)
        r.p(summary)
        r.p("**Limitations:**", indent_first=False, space_after=0, keep=True)
        r.bullets(lims)

    r.h2("Comparative Analysis of Existing Approaches")
    r.p("Table 2.1 compares the main approaches to building an organisational question-answering assistant.")
    r.table("Comparison of chatbot approaches", ["Approach", "Advantages", "Limitations"], [
        ("Rule / keyword based (ELIZA, menu bots)", "Simple, fast, predictable", "No understanding; fails on paraphrases; all answers scripted"),
        ("Intent classification (Rasa, NB/LR)", "Learns phrasings from examples; fast; interpretable", "Answers only anticipated questions; retraining needed for new content"),
        ("Keyword search (BM25)", "Exact terms, names and numbers; no training", "Misses synonyms; returns documents, not answers"),
        ("Dense retrieval (DPR, embeddings)", "Finds paraphrases by meaning", "Can miss exact terms; returns passages, not answers"),
        ("Generic LLM chatbot", "Fluent answers to open questions", "Does not know private documents; hallucinates; cloud privacy risk"),
        ("Retrieval-Augmented Generation", "Answers from current documents; cites sources; no retraining", "Quality depends on retrieval; needs a capable model; must handle 'not found'"),
        ("**ConvoAI (proposed)**", "Intent fast path + hybrid RAG + relevance gate + citations, fully local", "7B model can still misread rules spread across sections"),
    ], widths=(1.8, 2.2, 2.25))

    r.h2("Research Gap")
    r.p("The survey shows that intent-based chatbots are fast and interpretable but cannot answer from documents, "
        "while RAG systems can answer from documents but are usually built on cloud models, rarely decline "
        "unanswerable questions in a measured way, and are often evaluated only on public benchmarks. Hybrid "
        "retrieval and query rewriting are well described in the literature but are seldom combined with a "
        "classical NLP stage in one small, deployable application.")
    r.p("ConvoAI addresses this gap by combining a transparent intent classifier with local hybrid RAG, so that it "
        "answers small talk instantly and open-ended questions over private documents with citations, declines "
        "out-of-scope questions using a threshold tuned on held-out data, and does so without fine-tuning and without "
        "sending data to a cloud service. Each stage is evaluated quantitatively on the project's own test sets.")


def ch3(r):
    r.chapter_start("System Requirements and Specifications")
    r.p("This chapter lists the hardware and software needed to develop and run ConvoAI, the functional and "
        "non-functional requirements of the system, and a short description of each technology used.")
    r.h2("Hardware Requirements")
    r.p("ConvoAI runs the language model, embedding model and speech model on the local computer, so the hardware "
        "requirements are higher than for a typical web application. Table 3.1 lists the minimum configuration and "
        "the configuration used for development and testing.")
    r.table("Hardware requirements", ["Component", "Minimum", "Used for development and testing"], [
        ("Processor", "64-bit quad-core (Intel Core i5 / AMD Ryzen 5)", "AMD Ryzen 9 5900HS (8 cores, 16 threads)"),
        ("Memory (RAM)", "16 GB", "39 GB"),
        ("Graphics (GPU)", "Optional; NVIDIA GPU with 6 GB VRAM recommended", "NVIDIA GeForce RTX 3060 Laptop GPU, 6 GB"),
        ("Storage", "20 GB free (about 7 GB for models)", "Solid-state drive (SSD)"),
        ("Display", "1366 x 768 or higher", "1920 x 1080"),
        ("Audio", "Microphone for voice input (optional)", "Built-in laptop microphone"),
        ("Network", "Only for the first-time download of packages and models", "Not needed at run time"),
    ], widths=(1.5, 2.4, 2.35))
    r.p("Without a GPU the system still works, more slowly; in that case the smaller `llama3.2:3b` model can be "
        "selected in Settings.")

    r.h2("Software Requirements")
    r.table("Software requirements", ["Category", "Software", "Version"], [
        ("Operating system", "Windows 10/11 (also runs on Linux and macOS)", "Windows 11 Pro"),
        ("Programming language", "Python", "3.11"),
        ("Web framework", "Flask, Flask-Login, Flask-WTF", "3.1.2, 0.6.3, 1.2.2"),
        ("NLP and machine learning", "NLTK, scikit-learn, NumPy, joblib", "3.9.1, 1.7.2, 2.2.6, 1.5.2"),
        ("LLM runtime", "Ollama", "0.40"),
        ("Language models", "qwen2.5:7b-instruct (default), llama3.2:3b (fallback)", "Q4 quantised"),
        ("Embedding model", "nomic-embed-text (768 dimensions)", "v1.5"),
        ("Vector database", "ChromaDB", "1.1.1"),
        ("Keyword search", "rank-bm25", "0.2.2"),
        ("Document parsing", "pypdf, python-docx, trafilatura, markdown", "6.1.1, 1.2.0, 2.0.0, 3.9"),
        ("Speech-to-text", "faster-whisper (Whisper small)", "1.2.0"),
        ("Database", "SQLite", "3 (bundled with Python)"),
        ("Front end", "HTML5, CSS3, JavaScript, Material Web, Chart.js, Marked", "Material Web 2.4, Chart.js 4.5"),
        ("Testing", "pytest, pytest-cov, Playwright", "8.4.2, 6.2.1"),
        ("Browser", "Google Chrome or Microsoft Edge", "Latest"),
        ("Editor / tools", "Visual Studio Code, Git", "Latest"),
    ], widths=(1.7, 2.9, 1.65))

    r.h2("Functional Requirements")
    r.p("Functional requirements describe what the system must do. Table 3.3 lists them with identifiers that are "
        "used again in the testing chapter.")
    r.table("Functional requirements", ["ID", "Requirement", "Description"], [
        ("FR-01", "Chat interface", "Send messages and receive streamed replies in real time"),
        ("FR-02", "Intent classification", "Classify each message (TF-IDF + Logistic Regression) to route small talk vs document questions"),
        ("FR-03", "Response selection", "Predefined responses for small-talk intents; generated answers for document questions"),
        ("FR-04", "Fallback handling", "Decline when classifier confidence or retrieval relevance is too low"),
        ("FR-05", "Conversation history", "List, search, rename, delete and reopen conversations"),
        ("FR-06", "Admin management", "Manage intents (with retraining), collections, documents, users and settings"),
        ("FR-07", "Analytics dashboard", "Usage, answer routes, response time, most-cited documents, content gaps, feedback"),
        ("FR-08", "REST API", "JSON and streaming (Server-Sent Events) endpoints for chat, documents, analytics and metrics"),
        ("FR-09", "Document ingestion", "Upload PDF/DOCX/TXT/MD or add a URL; chunk, embed and index in the background"),
        ("FR-10", "Collections and access control", "Group documents by department; with sign-in on, each user searches only permitted collections"),
        ("FR-11", "Grounded answers with citations", "Answers cite the passages used; users can open the sources"),
        ("FR-12", "Follow-up understanding", "Rewrite follow-up questions using the conversation before searching"),
        ("FR-13", "Voice input/output", "Local speech-to-text (Whisper) and read-aloud with installed voices"),
        ("FR-14", "Model metrics", "Classifier comparison, confusion matrix, threshold analysis, retrieval evaluation"),
    ], widths=(0.7, 1.8, 3.75))

    r.h2("Non-Functional Requirements")
    r.table("Non-functional requirements", ["ID", "Requirement", "Target", "Measured"], [
        ("NFR-01a", "Small-talk response time", "< 300 ms", "about 2 ms (median)"),
        ("NFR-01b", "Document answer, first words", "< 2 s", "1.5-1.6 s median, 1.8 s 90th percentile"),
        ("NFR-01c", "Document answer, complete", "< 8 s", "3.1 s median, 4-6 s 90th percentile"),
        ("NFR-02", "Usability", "No training needed; works on phones", "Material 3 UI, phone layout, UAT passed"),
        ("NFR-03", "Portability", "Windows/macOS/Linux", "Python + Ollama; one-click scripts for Windows"),
        ("NFR-04", "Maintainability", "Modular and tested", "7 packages; 97 automated tests, 80% coverage"),
        ("NFR-05", "Scalability", "10,000+ messages, hundreds of documents", "Indexed SQLite tables; ChromaDB vector store"),
        ("NFR-06", "Privacy", "No data leaves the machine", "LLM, embeddings, speech and storage all local"),
        ("NFR-07", "Accuracy", "Answers grounded in documents", "92.7% correct facts, 100% correct citations"),
        ("NFR-08", "Security", "Protect admin functions and forms", "Role checks, CSRF tokens, hashed passwords"),
    ], widths=(0.8, 1.6, 1.8, 2.05))

    r.h2("Technologies Used")
    techs = [
        ("Python", "Python is a high-level, general-purpose programming language with a very large ecosystem for "
         "machine learning and NLP. ConvoAI is written in Python 3.11, chosen because the wheels for ChromaDB, NLTK and "
         "scikit-learn are stable on that version."),
        ("Flask", "Flask is a lightweight Python web framework. ConvoAI uses Flask's application factory and blueprints "
         "to separate pages from JSON APIs, Flask-Login for optional user sessions and Flask-WTF for CSRF protection. "
         "Answers are streamed with Server-Sent Events using Flask's streaming responses."),
        ("NLTK", "The Natural Language Toolkit provides tokenisers, stop-word lists and the WordNet lemmatizer used in "
         "the text pre-processing pipeline."),
        ("scikit-learn", "scikit-learn provides the TF-IDF vectorisers, the Multinomial Naive Bayes and Logistic "
         "Regression classifiers, grid search with stratified cross-validation, and the evaluation metrics."),
        ("Ollama", "Ollama is a local runtime for open language models. It downloads quantised models, runs them on "
         "the GPU or CPU and exposes an HTTP API on the local machine. ConvoAI uses it for both answer generation and "
         "embeddings."),
        ("Qwen2.5-7B-Instruct and Llama 3.2 3B", "Qwen2.5-7B-Instruct is an instruction-tuned open language model with "
         "7 billion parameters. In 4-bit quantised form it needs about 4.7 GB and fits a 6 GB laptop GPU. It follows "
         "the instruction to answer only from sources and cite them reliably. Llama 3.2 3B is a smaller, faster "
         "alternative for computers without a suitable GPU."),
        ("nomic-embed-text", "nomic-embed-text is an open text-embedding model that maps text to 768-dimensional "
         "vectors so that passages with similar meaning have similar vectors. It supports search prefixes for queries "
         "and documents."),
        ("ChromaDB", "ChromaDB is an open-source vector database. It stores each chunk's embedding, text and metadata "
         "(collection, document, page, heading) on disk and answers nearest-neighbour queries with metadata filters, "
         "which ConvoAI uses for collection-level access control."),
        ("rank-bm25", "rank-bm25 implements the BM25 ranking function in Python. ConvoAI builds a BM25 index over the "
         "same chunks for keyword search."),
        ("pypdf, python-docx, trafilatura", "These libraries extract text from PDF files (page by page), Word files "
         "(with headings and tables) and web pages (main content without menus and advertisements)."),
        ("faster-whisper", "faster-whisper is an efficient implementation of OpenAI's Whisper speech recognition "
         "model. It transcribes the user's recorded question on the local computer, with voice activity detection to "
         "ignore silence."),
        ("SQLite", "SQLite is a serverless relational database stored in a single file. It holds users, collections, "
         "documents, intents, conversations, messages, sources, feedback, settings and model runs."),
        ("Material Web and Chart.js", "Material Web provides Google's Material 3 components (buttons, text fields, "
         "dialogs, chips) as web components. Chart.js draws the analytics and metrics charts. Both are bundled locally "
         "so the interface works without internet access."),
        ("pytest and Playwright", "pytest runs the 97 automated tests with coverage measurement. Playwright drives "
         "Microsoft Edge to capture the screenshots of the user interface."),
    ]
    for name, desc in techs:
        r.h3(name)
        r.p(desc)


def ch4(r):
    r.chapter_start("System Analysis")
    r.p("System analysis studies how the problem is handled today, identifies the weaknesses of current methods and "
        "defines how the proposed system improves on them. It also checks whether the proposed system is feasible.")
    r.h2("Existing System")
    r.p("In most organisations, employees find policy and procedure information in one of the following ways:")
    r.bullets([
        "Manual search: opening shared folders or an intranet, finding the right PDF or Word file and searching it "
        "with Ctrl+F.",
        "Asking a colleague or help desk: sending an email or chat message to HR, IT support or a sales manager and "
        "waiting for a reply.",
        "Ticketing systems and FAQ pages: raising a ticket, or reading a static FAQ page that covers only common "
        "questions.",
        "Rule-based or intent-based chatbots: bots that recognise a fixed list of intents and return a scripted "
        "answer for each.",
        "Public AI chatbots: copying parts of documents into a cloud chatbot and asking it questions.",
    ])
    r.figure_placeholder("Existing system: manual and help-desk based information access",
        "An illustration of the existing information-access process in an office. On the left, an employee icon "
        "with a question bubble 'How many casual leaves do I get?'. Three paths fan out to the right: (a) 'Search "
        "shared folders' leading to a pile of PDF and Word document icons with a magnifying glass and a red label "
        "'slow, keyword-only'; (b) 'Email HR / IT help desk' leading to a help-desk icon with an hourglass and a "
        "red label 'hours to reply'; (c) 'Scripted FAQ bot' leading to a simple robot icon with a red label "
        "'only fixed questions'. Use muted grey for the paths and small red warning labels. " + STYLE)
    r.h3("Limitations of the Existing System")
    r.bullets([
        "Time-consuming: finding one rule in a long document takes minutes, and waiting for a help desk can take "
        "hours or days.",
        "Keyword dependence: Ctrl+F and intranet search find only exact words, not the meaning of the question.",
        "Inconsistent answers: different staff members may answer the same question differently.",
        "Limited availability: human help is available only during working hours.",
        "Rigid bots: intent-based bots answer only questions that were anticipated, and must be retrained whenever a "
        "policy changes.",
        "Privacy risk: pasting confidential documents into public AI services sends them outside the organisation.",
        "No verification: neither a busy colleague nor a generic chatbot shows exactly where the answer came from.",
        "No insight: the organisation does not learn which questions are asked often or which ones its documents "
        "fail to answer.",
    ])

    r.h2("Proposed System")
    r.p("The proposed system, ConvoAI, is a local web application through which employees ask questions in natural "
        "language, by typing or speaking, and receive answers drawn from the organisation's own documents with "
        "citations. Administrators maintain the knowledge simply by uploading documents into departmental "
        "collections; no retraining is needed for new content. The proposed system model is shown in Figure 4.2.")
    r.figure_placeholder("Proposed system model",
        "A system model diagram for 'ConvoAI - Proposed System'. Top-left: an 'Employee' figure icon sending "
        "'Question (text or voice)' into a large central rounded box labelled 'ConvoAI (Flask web application)'. "
        "Inside the central box, four stacked sub-boxes in a vertical flow: 'Intent Classifier', 'Follow-up "
        "Rewriter', 'Hybrid Retriever + Relevance Gate', 'Local LLM Answer Generator'. On the right side, three "
        "cylinder icons: 'SQLite (chats, users, settings)', 'ChromaDB + BM25 (document chunks)', and 'Ollama models "
        "(Qwen2.5-7B, nomic-embed-text)'. Bottom-left: an 'Administrator' figure icon with an arrow 'Upload documents "
        "into HR / IT / Sales collections' into the central box. An arrow back to the employee labelled 'Answer with "
        "citations [1][2]'. A dashed border around everything labelled 'Organisation's own computer - no cloud'. "
        + STYLE)
    r.p("The main features of the proposed system are:")
    r.bullets([
        "A hybrid router that answers small talk instantly through the intent classifier and sends other questions "
        "to retrieval-augmented generation.",
        "Hybrid search combining semantic vector search and BM25 keyword search with Reciprocal Rank Fusion.",
        "A relevance gate that declines questions the documents cannot answer.",
        "Grounded, streamed answers with numbered citations and a sources panel that highlights the passage.",
        "Follow-up understanding by rewriting questions using the conversation history.",
        "Voice input transcribed on the local computer and optional read-aloud of answers.",
        "Departmental collections with optional per-user access control.",
        "An administration panel for documents, collections, intents, users and settings, plus analytics and a "
        "model-metrics page.",
    ])
    r.h3("Advantages of the Proposed System")
    r.bullets([
        "Instant answers at any time, in about 3 seconds for document questions and 2 milliseconds for small talk.",
        "Understands meaning, not just keywords, and handles paraphrases and follow-up questions.",
        "Verifiable: every fact is cited, and the user can open the exact passage.",
        "Honest: says \"I couldn't find that\" instead of inventing an answer.",
        "Always up to date: uploading a new document makes it searchable within seconds, with no retraining.",
        "Private: all processing happens on the organisation's computer.",
        "Insightful: analytics reveal frequent questions, slow answers and content gaps in the documents.",
        "Low cost: uses only free, open-source software and models on existing hardware.",
    ])

    r.h2("Feasibility Study")
    r.p("A feasibility study checks whether the proposed system can be built and used successfully. Three aspects "
        "were studied.")
    r.h3("Technical Feasibility")
    r.p("All components are mature open-source software: Flask, NLTK, scikit-learn, ChromaDB, Ollama and Whisper. "
        "The development laptop's RTX 3060 GPU with 6 GB of memory runs the quantised 7-billion-parameter model at "
        "interactive speed, and the system also runs on CPU with a smaller model. The developer has the required "
        "skills in Python, web development and machine learning. The project is technically feasible.")
    r.h3("Economic Feasibility")
    r.p("No licence fees or cloud subscriptions are needed; all software and models are free to use. The system runs "
        "on hardware the organisation already owns. The main cost is development time, which is small compared with "
        "the staff time saved on repeated questions. The project is economically feasible.")
    r.h3("Operational Feasibility")
    r.p("Users interact through a familiar chat interface in a web browser and need no training. Administrators "
        "maintain the knowledge by uploading files, which requires no programming. One-click setup and start scripts "
        "make installation simple. User acceptance testing (Chapter 7) confirmed that all main tasks work as "
        "expected. The project is operationally feasible.")
