"""Chapters 7-9, bibliography, appendices."""
from ch1_4 import STYLE, SS
from rb import C, L, J, _font
from docx.shared import Pt

CHART = ("Clean academic chart on white background, Times New Roman labels, light grey gridlines, navy (#1F3A68) "
         "and teal (#2A9D8F) bars, orange (#E07A2F) for the comparison series, value labels on top of each bar, "
         "axis titles, a small legend at the top right, no 3D, no shadows, landscape 16:9, print-friendly.")


def ch7(r):
    r.chapter_start("Testing")
    r.p("Testing verifies that the system meets its requirements and measures how well it performs. ConvoAI was "
        "tested at four levels: automated unit and integration tests for the code, quantitative evaluation of each "
        "AI component on held-out test sets, end-to-end evaluation of complete answers, and manual user acceptance "
        "testing in the browser. All tests were run on the development laptop described in Chapter 3.")

    r.h2("Methods of Testing")
    for name, desc in [
        ("Unit Testing", "Individual functions are tested in isolation: text pre-processing, chunking, Reciprocal "
         "Rank Fusion, citation parsing, each document loader and the settings validator. The language model and "
         "embedding model are replaced with deterministic stand-ins so that tests run quickly and give repeatable "
         "results."),
        ("Integration Testing", "Modules are tested together through the Flask test client: uploading a document "
         "and waiting for it to be indexed, asking a question through the chat API and checking the stored message "
         "and sources, and checking that a user with access only to HR documents never receives IT passages."),
        ("System Testing", "The complete application is tested with the real models through the evaluation scripts, "
         "which send every question in a gold set through the full pipeline and grade the answers automatically."),
        ("Black-Box Testing", "Test cases are designed from the requirements without reference to the code: for "
         "example, an out-of-scope question must be declined, and an invalid setting must be rejected."),
        ("White-Box Testing", "Tests are designed from the code paths, for example the grey-zone branch of the "
         "relevance gate, the error path when Ollama is unavailable and the stop button during streaming. Line "
         "coverage is measured with pytest-cov."),
        ("Performance Testing", "Response times are measured per stage (classification, rewriting, embedding, "
         "retrieval, first token and full answer) and summarised as medians and 90th percentiles."),
        ("User Acceptance Testing", "A checklist of 26 end-to-end scenarios is executed manually in the browser on "
         "desktop and phone widths, in light and dark themes."),
    ]:
        r.h3(name)
        r.p(desc)

    r.h2("Automated Test Results")
    r.p("The automated suite contains 97 tests written with pytest. All 97 pass, in 85 seconds. Table 7.1 shows the "
        "tests per module.")
    r.table("Automated test results", ["Test module", "What it covers", "Tests", "Failed"], [
        ("test_admin", "Collections, users, intents, settings, document move, admin-only access", "13", "0"),
        ("test_analytics", "Dashboard figures, time windows, metrics API", "5", "0"),
        ("test_app", "App factory, schema, sign-in, roles, theme API, health", "9", "0"),
        ("test_chat", "Hybrid retrieval, prompts, router, chat/stream API, conversations, feedback, stop", "19", "0"),
        ("test_nlp", "Pre-processing, responses, router rule, classifier training, predict API", "20", "0"),
        ("test_rag", "Loaders (PDF/DOCX/TXT/MD/URL), chunker, ingestion, document API, retrieval scope", "22", "0"),
        ("test_speech", "Speech API, Whisper on silence, tones and real speech", "5", "0"),
        ("test_ui", "No-sign-in mode, chat page, conversation links", "4", "0"),
        ("**Total**", "", "**97**", "**0**"),
    ], widths=(1.3, 3.6, 0.7, 0.65), size=10.5)
    r.p("Line coverage is 80% of all application code and 89% of the code that runs inside the web application. "
        "The command-line evaluation scripts are exercised by the evaluation runs described below rather than by "
        "unit tests.")
    r.table("Code coverage by package", ["Package", "Statements", "Covered"], [
        ("app / config", "112", "72%"), ("models/", "321", "97%"), ("nlp/", "293", "81%"),
        ("rag/", "877", "64%"), ("services/", "437", "84%"), ("routes/", "751", "89%"),
    ], widths=(2.5, 1.9, 1.85))

    r.h2("Intent Classifier Evaluation")
    r.p("The classifier was trained on 638 patterns across 25 intents and evaluated in two ways: stratified 5-fold "
        "cross-validation on the training patterns, and a separate held-out set of 100 unseen phrasings that includes "
        "off-topic questions which must not receive a canned reply. The metrics used are:")
    r.bullets([
        "Accuracy = correctly classified messages / all messages.",
        "Precision (per intent) = TP / (TP + FP); Recall = TP / (TP + FN).",
        "F1 = 2 x Precision x Recall / (Precision + Recall); macro-F1 is the unweighted mean over intents, so rare "
        "intents count as much as common ones.",
    ])
    r.table("Intent classifier comparison", ["Model", "Tuned setting", "CV accuracy", "CV macro-F1",
                                              "Test accuracy", "Test macro-F1"], [
        ("Multinomial Naive Bayes", "alpha = 0.05", "0.732", "0.724", "0.890", "0.875"),
        ("Logistic Regression (selected)", "C = 5", "0.762", "0.763", "**0.910**", "**0.905**"),
    ], widths=(2.0, 1.1, 0.8, 0.8, 0.8, 0.8), size=10.5)
    r.p("Logistic Regression outperforms Naive Bayes on every measure and was selected. Cross-validation scores are "
        "lower than held-out scores because cross-validation includes the hardest, most overlapping intents with few "
        "examples, while the held-out set reflects realistic messages. At the chosen confidence threshold of 0.35, "
        "90% of held-out messages are routed correctly, 4% receive a wrong quick reply and 6% of small talk is sent to "
        "the documents, where it is answered more slowly but harmlessly. The weakest intents by cross-validation F1 "
        "were help_usage (0.50), frustration (0.55) and bot_capabilities (0.58), which overlap in wording.")
    r.figure_placeholder("Naive Bayes vs Logistic Regression comparison",
        "A grouped vertical bar chart titled 'Intent Classifier Comparison'. X-axis categories: 'CV Accuracy', "
        "'CV Macro-F1', 'Test Accuracy', 'Test Macro-F1'. Two bars per category: 'Multinomial Naive Bayes' (orange) "
        "with values 0.732, 0.724, 0.890, 0.875 and 'Logistic Regression' (navy) with values 0.762, 0.763, 0.910, "
        "0.905. Y-axis 'Score' from 0.6 to 1.0. " + CHART, kind="Chart")
    r.screenshot("Metrics page: model comparison, threshold analysis and per-intent F1", SS / "23-metrics-classifier.png")
    r.screenshot("Confusion matrix of the intent classifier (cross-validation)", SS / "24-confusion-matrix.png")

    r.h2("Retrieval Evaluation")
    r.p("Retrieval was evaluated on 46 questions whose answer passage is known and 15 off-topic questions. Three "
        "search modes were compared. Hit@k is the fraction of questions whose correct passage appears in the top k "
        "results; Mean Reciprocal Rank (MRR) averages 1/rank of the first correct passage, so it rewards putting the "
        "right passage first.")
    r.table("Retrieval evaluation", ["Search mode", "Hit@1", "Hit@5", "MRR@5"], [
        ("Vector (meaning)", "0.891", "0.978", "0.931"),
        ("Keyword (BM25)", "0.848", "0.978", "0.909"),
        ("**Hybrid (used)**", "**0.891**", "**0.978**", "**0.935**"),
    ], widths=(2.5, 1.25, 1.25, 1.25))
    r.p("Hybrid search gives the best MRR. Answerable questions scored between 0.636 and 0.857 in best similarity "
        "and off-topic questions between 0.468 and 0.600, so the threshold of 0.618 separates them with 100% "
        "accuracy on this set. The only retrieval miss was \"Which days do we have to come to the office?\", where the "
        "handbook uses different wording.")
    r.figure_placeholder("Retrieval quality by search mode",
        "A grouped vertical bar chart titled 'Retrieval Quality by Search Mode'. X-axis categories: 'Hit@1', "
        "'Hit@5', 'MRR@5'. Three bars per category: 'Vector' (teal) 0.891, 0.978, 0.931; 'Keyword BM25' (orange) "
        "0.848, 0.978, 0.909; 'Hybrid' (navy) 0.891, 0.978, 0.935. Y-axis from 0.8 to 1.0. " + CHART, kind="Chart")
    r.screenshot("Metrics page: retrieval evaluation and the not-found threshold", SS / "25-metrics-retrieval.png")

    r.h2("End-to-End Answer Evaluation")
    r.p("Every question in a gold set of 41 document questions, plus off-topic questions and small talk, was sent "
        "through the full pipeline (classifier, rewriting, hybrid retrieval and the language model) on a copy of the "
        "database. Answers were graded automatically: the expected fact must appear in the answer; the correct "
        "document must be cited; every number in the answer must appear in a retrieved passage (a check for invented "
        "numbers); off-topic questions must be declined; and small talk must take the fast path. Both language "
        "models were compared.")
    r.table("End-to-end answer evaluation", ["Metric", "qwen2.5:7b-instruct", "llama3.2:3b"], [
        ("Correct fact in answer", "**92.7%**", "90.2%"),
        ("Correct document cited", "**100.0%**", "53.7%"),
        ("Numbers grounded in sources", "97.6%", "100.0%"),
        ("Off-topic questions declined", "100.0%", "100.0%"),
        ("Small talk on fast path", "100.0%", "100.0%"),
        ("First token (median / 90th pct)", "1.62 s / 1.77 s", "1.00 s / 1.12 s"),
        ("Full answer (median / 90th pct)", "3.06 s / 4.20 s", "1.32 s / 1.77 s"),
        ("'Not found' reply (median)", "613 ms", "595 ms"),
        ("Quick reply (median)", "2 ms", "2 ms"),
    ], widths=(2.6, 1.85, 1.8))
    r.p("The 3-billion-parameter model answers about twice as fast, but it left out citations in almost half of its "
        "answers and invented facts in two cases (it gave a Pune per diem of INR 5,000 and called Mysuru a metro city). "
        "The 7-billion-parameter model cited the correct document every time, so it is the default, and the smaller "
        "model remains available for computers without a suitable GPU.")
    r.figure_placeholder("Answer quality and speed of the two language models",
        "A two-panel chart titled 'Qwen2.5-7B vs Llama3.2-3B'. Left panel: horizontal grouped bars for 'Correct "
        "fact' (92.7% vs 90.2%), 'Correct citation' (100% vs 53.7%), 'Grounded numbers' (97.6% vs 100%), 'Off-topic "
        "declined' (100% vs 100%), x-axis 0-100%. Right panel: vertical grouped bars for 'First token median' (1.62 s "
        "vs 1.00 s) and 'Full answer median' (3.06 s vs 1.32 s), y-axis seconds 0-4. Qwen2.5-7B in navy, Llama3.2-3B "
        "in orange. " + CHART, kind="Chart")

    r.h3("Experiments that did not improve results")
    r.p("Two changes were tested on the same 41 questions and not adopted: including the chunks next to the top two "
        "matches (correct facts stayed at 92.7%, answers became slower and one answer got worse), and stricter prompt "
        "rules (no change). Keeping the simpler design was a deliberate, measured decision.")
    r.h3("Error analysis")
    r.p("The three questions that the 7B model still answers wrongly all require combining conditions from different "
        "sections of a document:")
    r.numbered([
        "*\"Per diem for a trip to Pune?\"* The per-diem table says only \"metro cities\"; the list of metro cities, "
        "which includes Pune, is in the hotel section. The model gives the \"other cities\" amount.",
        "*\"How much does the Professional plan cost per agent?\"* The model gives the monthly-billing price and "
        "multiplies it into a yearly total that is not in the guide (the grounding check flags this number).",
        "*\"Who approves a 25 percent discount?\"* The model gives only the non-profit special case (Sales Manager) and "
        "not the general rule for 20-30% (VP Sales).",
    ])
    r.p("These errors point to model size and document structure, not retrieval: in each case the right passages "
        "were retrieved. Remedies are a larger model or writing documents so that each table names its categories.")

    r.h2("Performance Testing")
    r.table("Response time by route (RTX 3060 laptop GPU)", ["Route / stage", "Median", "90th percentile", "Target"], [
        ("Quick reply (intent fast path)", "2 ms", "3 ms", "< 300 ms"),
        ("'Not found' reply (retrieval only)", "586 ms", "-", "< 2 s"),
        ("Document answer: first token", "1.52 s", "1.84 s", "< 2 s"),
        ("Document answer: complete", "3.10 s", "6.35 s", "< 8 s"),
        ("Voice transcription (5-second question)", "about 2 s", "-", "-"),
        ("Indexing a 41-page PDF", "about 6 s", "-", "-"),
    ], widths=(2.7, 1.1, 1.2, 1.25))
    r.figure_placeholder("Breakdown of response time for a document answer",
        "A single horizontal stacked bar chart titled 'Document answer timeline (median of 41 questions)'. One bar "
        "of total length 3.10 seconds with two segments: 'Classify, embed, retrieve and read sources -> first word' "
        "from 0 to 1.52 s (navy) and 'Stream the rest of the answer' from 1.52 s to 3.10 s (orange). A thin marker at "
        "1.52 s labelled 'first words appear' and at 3.10 s labelled 'answer complete'. Below it, a much shorter bar "
        "labelled 'Quick reply (small talk)' of 0.002 s drawn as a tiny grey sliver with the label '2 ms', and a bar "
        "labelled 'Not found reply' of 0.586 s in grey. X-axis 'seconds' from 0 to 3.5. " + CHART, kind="Chart")
    r.h2("Test Cases")
    r.p("Table 7.7 lists the user acceptance test cases executed in the browser. Each was run on desktop (1366-1440 px) "
        "and phone (375 px) widths with the sample documents loaded.")
    r.table("Test cases (user acceptance testing)", ["ID", "Test case", "Expected result", "Status"], [
        ("TC-01", "Start the application and open it", "Chat opens; Overview shows database, Ollama and models as green", "Pass"),
        ("TC-02", "Type \"hi\", then \"thanks!\"", "Instant reply with 'Quick reply' badge, no sources", "Pass"),
        ("TC-03", "Ask \"How many casual leaves do I get per year?\"", "Streams '12 days of casual leave' citing the Employee Handbook p.4", "Pass"),
        ("TC-04", "Follow up: \"and can I carry them forward?\"", "Shows 'Understanding your follow-up'; cited answer about carry-forward", "Pass"),
        ("TC-05", "Ask \"What is the capital of France?\"", "Polite 'couldn't find' reply, 'Not found in documents' badge", "Pass"),
        ("TC-06", "Click a citation number", "Sources panel opens at the passage with question words highlighted", "Pass"),
        ("TC-07", "Give a thumbs-up and reload", "Rating persists and appears in Analytics", "Pass"),
        ("TC-08", "Press stop while an answer streams", "Streaming stops; partial answer saved", "Pass"),
        ("TC-09", "Rename, delete and reopen chats by link", "History updates; links restore the right conversation", "Pass"),
        ("TC-10", "Select 'IT Support' chip, ask an HR question", "Answer limited to IT documents or declined", "Pass"),
        ("TC-11", "Ask by voice and stay silent afterwards", "Recording stops ~1.5 s after speech; text transcribed locally", "Pass*"),
        ("TC-12", "Turn on read-aloud and ask a question", "Answer read aloud without citation numbers", "Pass"),
        ("TC-13", "Upload a 41-page PDF", "Queued, Processing %, Ready in ~6 s; chunks viewable", "Pass"),
        ("TC-14", "Upload the same file again", "Skipped with 'Already in ...'", "Pass"),
        ("TC-15", "Test retrieval for 'who approves discounts above 20 percent'", "Discounts section first in both result lists", "Pass"),
        ("TC-16", "Create and delete a collection", "Card appears; delete asks for confirmation", "Pass"),
        ("TC-17", "Edit an intent, then Retrain", "'Retrain needed' banner appears, clears after training", "Pass"),
        ("TC-18", "Set 'Sources per answer' to 6, then 50", "6 is saved; 50 rejected with field highlighted", "Pass"),
        ("TC-19", "Open Analytics and switch time ranges", "Figures match chat history; table views available", "Pass"),
        ("TC-20", "Re-run evaluation on Metrics page", "Completes in ~10 s; hybrid MRR 0.935", "Pass"),
        ("TC-21", "Repeat TC-02/03/06 at 375 px width", "No sideways scrolling; drawer history; bottom navigation", "Pass"),
        ("TC-22", "Sign-in on; HR-only user asks about VPN", "IT documents never retrieved; admin pages return 403", "Pass"),
    ], widths=(0.6, 2.1, 2.85, 0.7), size=10)
    r.p("*TC-11 was verified with a recorded voice fed in as the microphone; it should be repeated with a live "
        "microphone in Chrome or Edge before the demonstration.", indent_first=False, size=11, italic=True)

    r.h2("Limitations of the Evaluation")
    r.p("The gold test sets were written by the developer for the sample documents, and the not-found and intent "
        "thresholds were tuned on held-out sets that are also used for reporting, so the scores are likely slightly "
        "optimistic for new documents. The automatic grounding check only detects numbers that appear in no retrieved "
        "passage, and fact matching is based on text matching. Answers vary slightly between runs because the model "
        "samples at temperature 0.2. These limits are stated so that the results are read in context.")


def ch8(r):
    r.chapter_start("Novelty in Proposed System and Future Enhancement")
    r.h2("Novelty of the Proposed System")
    r.p("ConvoAI is not the first chatbot or the first RAG system, but it combines several ideas in a way that is new "
        "for a small, deployable assistant, and measures each one:")
    r.bullets([
        "Hybrid router: a classical, interpretable NLP intent classifier answers small talk in milliseconds, and only "
        "real questions reach the more expensive retrieval and language-model pipeline. The classical pipeline from "
        "the synopsis is kept and given a clear job instead of being replaced.",
        "Hybrid retrieval with a measured relevance gate: vector and BM25 search are fused with Reciprocal Rank "
        "Fusion, and the not-found threshold is tuned on held-out data. The grey-zone rule, which accepts a borderline "
        "score only when keyword search independently agrees, was introduced after a real follow-up failure was found "
        "in testing and verified not to let any off-topic question through.",
        "Honest, verifiable answers: every fact carries a citation that opens the exact passage, invalid citation "
        "numbers are removed, and the assistant says when it cannot find an answer.",
        "Fully local and private: the language model, embeddings, speech recognition and data all run on one laptop "
        "with a 6 GB GPU, with no cloud service and no internet connection needed after setup.",
        "Departmental access control enforced inside the vector database query, so restricted passages can never "
        "reach the model.",
        "Built-in measurement: the metrics page shows the classifier comparison, confusion matrix, threshold analysis "
        "and retrieval evaluation inside the product, and analytics reveal content gaps in the documents.",
        "Voice input transcribed locally with Whisper, with automatic end-of-speech detection.",
    ])
    r.h2("Future Enhancements")
    r.bullets([
        "Larger or fine-tuned language models to resolve rules that span several sections, the main remaining error type.",
        "A cross-encoder re-ranking stage after retrieval to improve the order of the top passages.",
        "OCR for scanned PDFs and table-aware chunking for documents with complex tables.",
        "A feedback loop that uses unhelpful answers and content gaps to suggest document improvements automatically.",
        "Answers in Indian languages such as Kannada and Hindi, using multilingual embeddings and models.",
        "Integration with Microsoft Teams, Slack or WhatsApp so employees can ask from tools they already use.",
        "Production deployment on a GPU server with PostgreSQL and single sign-on for larger organisations.",
        "Automatic re-indexing when documents in a shared folder or intranet change.",
    ])


def ch9(r):
    r.chapter_start("Findings and Conclusion")
    r.h2("Findings")
    r.bullets([
        "Logistic Regression with word and character TF-IDF features is a better intent classifier than Multinomial "
        "Naive Bayes on this data (held-out macro-F1 0.905 vs 0.875), and its probabilities are reliable enough to "
        "route messages with a threshold.",
        "Hybrid retrieval gives the best ranking (MRR 0.935) and finds the right passage in the top five for 97.8% of "
        "questions. Vector and keyword search each have strengths that fusion combines.",
        "A similarity threshold tuned on held-out questions separated every answerable question from every off-topic "
        "one, so the assistant declined all off-topic questions instead of guessing.",
        "With grounded prompting, a 7-billion-parameter local model answered 92.7% of document questions correctly and "
        "cited the right document 100% of the time; a 3-billion-parameter model was faster but much less reliable "
        "with citations.",
        "Answers start in about 1.6 seconds and complete in about 3 seconds on a laptop GPU, meeting the response-time "
        "requirements; small talk is answered in about 2 milliseconds.",
        "The remaining errors come from the language model combining conditions across sections, not from retrieval.",
    ])
    r.h2("Conclusion")
    r.p("This project set out to build an intelligent conversational chatbot using Python and Natural Language "
        "Processing that could answer an organisation's questions accurately and privately. ConvoAI meets this aim. It "
        "keeps the NLP pipeline and intent classifier proposed in the synopsis and extends them with "
        "Retrieval-Augmented Generation, so that the assistant can answer open-ended questions about an organisation's "
        "own documents, which an intent-only chatbot cannot do.")
    r.p("Combining a lightweight, interpretable intent classifier with local Retrieval-Augmented Generation produced "
        "a practical assistant: instant small talk, cited answers from private documents and honest refusals, at about "
        "three seconds per answer on a laptop GPU, with no data leaving the machine. The application is complete and "
        "usable, with streaming chat, voice input, departmental collections, administration, analytics and model "
        "metrics, and it is supported by 97 automated tests and a documented evaluation.")
    r.p("The evaluation showed that retrieval is reliable and that the remaining errors arise when the language model "
        "must combine rules from different sections. This points to model size and document structure as the next "
        "areas for improvement. Overall, the project shows that trustworthy, private AI assistance over organisational "
        "knowledge is achievable today with open-source tools and modest hardware.")


BIB = [
    "Weizenbaum, J. (1966). ELIZA: A computer program for the study of natural language communication between man and machine. *Communications of the ACM*, 9(1), 36-45.",
    "Adamopoulou, E., & Moussiades, L. (2020). An overview of chatbot technology. In *Artificial Intelligence Applications and Innovations (AIAI 2020)*, IFIP AICT 584, 373-383. Springer.",
    "Bocklisch, T., Faulkner, J., Pawlowski, N., & Nichol, A. (2017). Rasa: Open source language understanding and dialogue management. *NIPS 2017 Conversational AI Workshop*. arXiv:1712.05181.",
    "McCallum, A., & Nigam, K. (1998). A comparison of event models for Naive Bayes text classification. *AAAI-98 Workshop on Learning for Text Categorization*, 41-48.",
    "Jurafsky, D., & Martin, J. H. (2024). *Speech and Language Processing* (3rd ed. draft). Stanford University.",
    "Bird, S., Klein, E., & Loper, E. (2009). *Natural Language Processing with Python*. O'Reilly Media.",
    "Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research*, 12, 2825-2830.",
    "Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to Information Retrieval*. Cambridge University Press.",
    "Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond. *Foundations and Trends in Information Retrieval*, 3(4), 333-389.",
    "Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. *Proceedings of ACM SIGIR '09*, 758-759.",
    "Karpukhin, V., Oguz, B., Min, S., Lewis, P., Wu, L., Edunov, S., Chen, D., & Yih, W. (2020). Dense passage retrieval for open-domain question answering. *Proceedings of EMNLP 2020*, 6769-6781.",
    "Lewis, P., Perez, E., Piktus, A., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems*, 33, 9459-9474.",
    "Gao, Y., Xiong, Y., Gao, X., et al. (2023). Retrieval-augmented generation for large language models: A survey. arXiv:2312.10997.",
    "Ji, Z., Lee, N., Frieske, R., et al. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys*, 55(12), 1-38.",
    "Vaswani, A., et al. (2017). Attention is all you need. *Advances in Neural Information Processing Systems*, 30.",
    "Qwen Team (2024). Qwen2.5 technical report. arXiv:2412.15115.",
    "Nussbaum, Z., Morris, J. X., Duderstadt, B., & Mulyar, A. (2024). Nomic Embed: Training a reproducible long context text embedder. arXiv:2402.01613.",
    "Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2023). Robust speech recognition via large-scale weak supervision. *Proceedings of ICML 2023*.",
    "Grinberg, M. (2018). *Flask Web Development* (2nd ed.). O'Reilly Media.",
    "Flask documentation (2026). https://flask.palletsprojects.com",
    "Ollama documentation (2026). https://github.com/ollama/ollama",
    "Chroma documentation (2026). https://docs.trychroma.com",
    "Material Design 3 guidelines (2026). https://m3.material.io",
]


def bibliography(r):
    r.unnumbered_chapter("Bibliography", "BIB")
    for i, b in enumerate(BIB, 1):
        para = r.doc.add_paragraph(); para.alignment = J
        pf = para.paragraph_format; pf.left_indent = Pt(28); pf.first_line_indent = Pt(-28); pf.space_after = Pt(4)
        r.runs(para, f"[{i}]  {b}")


ABBR = [("AI", "Artificial Intelligence"), ("API", "Application Programming Interface"), ("BM25", "Best Matching 25 (ranking function)"),
        ("CPU", "Central Processing Unit"), ("CRUD", "Create, Read, Update, Delete"), ("CSRF", "Cross-Site Request Forgery"),
        ("CV", "Cross-Validation"), ("DFD", "Data Flow Diagram"), ("DOCX", "Microsoft Word document format"),
        ("ER", "Entity-Relationship"), ("FR / NFR", "Functional / Non-Functional Requirement"), ("GPU", "Graphics Processing Unit"),
        ("HTML", "HyperText Markup Language"), ("JSON", "JavaScript Object Notation"), ("LLM", "Large Language Model"),
        ("LR", "Logistic Regression"), ("ML", "Machine Learning"), ("MRR", "Mean Reciprocal Rank"), ("NB", "Naive Bayes"),
        ("NLP", "Natural Language Processing"), ("NLTK", "Natural Language Toolkit"), ("OCR", "Optical Character Recognition"),
        ("PDF", "Portable Document Format"), ("RAG", "Retrieval-Augmented Generation"), ("REST", "Representational State Transfer"),
        ("RRF", "Reciprocal Rank Fusion"), ("SQL", "Structured Query Language"), ("SSE", "Server-Sent Events"),
        ("TF-IDF", "Term Frequency-Inverse Document Frequency"), ("UAT", "User Acceptance Testing"), ("UI", "User Interface"),
        ("UML", "Unified Modeling Language"), ("URL", "Uniform Resource Locator"), ("VRAM", "Video Random Access Memory")]


def appendix(r):
    r.unnumbered_chapter("Appendix", "APP")
    r.appendix_prefix = "A"
    r.fig_n = 0
    r.h2("Appendix A: Screenshots", numbered=False)
    for title, f, w in [
        ("Sign-in page (when sign-in is switched on)", "22-login.png", 6.0),
        ("Answer from the Travel and Expense Policy", "16-chat-travel.png", 6.0),
        ("Chat on a phone (390 px wide)", "17-mobile-light.png", 2.9),
        ("Collections page", "09-collections.png", 6.0),
        ("Intents knowledge base and model summary", "10-intents.png", 6.0),
        ("Intent editor dialog", "20-intent-editor.png", 6.0),
        ("Test retrieval: vector and keyword results side by side", "14-test-retrieval.png", 6.0),
        ("Users and collection access", "21-users.png", 6.0),
        ("Settings page", "13-settings.png", 5.2),
        ("Analytics dashboard", "11-analytics.png", 4.6),
    ]:
        r.screenshot(title, SS / f, w)
    r.pagebreak()
    r.h2("Appendix B: Abbreviations", numbered=False)
    from docx.shared import Inches
    from rb import no_borders
    from rb import set_widths
    t = r.doc.add_table(rows=0, cols=2); no_borders(t)
    for a, b in ABBR:
        cells = t.add_row().cells
        cells[0].width = Inches(1.4); cells[1].width = Inches(4.8)
        for c, txt, bold in ((cells[0], a, True), (cells[1], ": " + b, False)):
            pp = c.paragraphs[0]; pp.paragraph_format.line_spacing = 1.15; pp.paragraph_format.space_after = Pt(1)
            run = pp.add_run(txt); _font(run, 12, bold)
    set_widths(t, [1.4, 4.8])
    r.pagebreak()
    r.h2("Appendix C: User Guide", numbered=False)
    r.p("**Installation (Windows).** Install Python 3.11 (tick *Add python.exe to PATH*) and Ollama. Double-click "
        "`setup.bat`; the first run takes about 20 minutes because it installs packages, downloads about 7 GB of models, "
        "trains the classifier and loads the sample documents. Then double-click `start.bat`; ConvoAI opens in the "
        "browser at http://127.0.0.1:5000.", indent_first=False)
    r.p("**Asking questions.** Type a question and press Enter, or click a suggested question. Choose a collection chip "
        "(All, General, HR, IT Support, Sales) to limit the search. Click a citation number or source chip to open the "
        "passage. Use the microphone button to ask by voice and the speaker button to have answers read aloud. Use "
        "thumbs up or down to rate an answer.", indent_first=False)
    r.p("**Adding documents.** Open Documents, choose the collection, and drag files into the upload area or click "
        "*Add URL*. The status changes to Ready when the document is searchable. Use *Test retrieval* to check what a "
        "question finds.", indent_first=False)
    r.p("**Administration.** Collections creates departments; Intents edits small-talk replies and retrains the "
        "classifier; Users (when sign-in is on) manages accounts and collection access; Settings changes the models, "
        "thresholds, chunking and voice options; Analytics and Metrics show usage and model quality.", indent_first=False)
    r.p("**Troubleshooting.** If the Overview shows Ollama as not reachable, start the Ollama app. If answers are slow, "
        "close other programs using the GPU or select `llama3.2:3b` in Settings. Scanned PDFs cannot be read because OCR "
        "is not supported.", indent_first=False)


def placeholders_pages(r):
    r.unnumbered_chapter("Research Paper Publication Details", "PAPER")
    for txt in ["[ PLACEHOLDER: Research paper publication details ]",
                "Insert the published or submitted research paper here (journal name, volume, issue, ISSN, "
                "acceptance letter and the paper pages), as in the department's format.",
                "[FILL: Paper title, journal, date of publication]"]:
        r.center(txt, 12, txt.startswith("[ "), space_after=10, spacing=1.5)
    r.unnumbered_chapter("Plagiarism Check Similarity Report", "PLAG")
    for txt in ["[ PLACEHOLDER: Plagiarism check similarity report ]",
                "Insert the similarity report generated by the university's plagiarism-check tool (for example "
                "Turnitin, Urkund/Ouriginal or DrillBit) here, with the overall similarity percentage and the "
                "certificate page.",
                "[FILL: Similarity percentage and date of check]"]:
        r.center(txt, 12, txt.startswith("[ "), space_after=10, spacing=1.5)
