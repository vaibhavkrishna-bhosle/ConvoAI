// ConvoAI viva presentation (KSOU academic style). Run from a folder where pptxgenjs, react-icons,
// react, react-dom and sharp are installed:  node make_ppt.js
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const RDS = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const ROOT = "D:/MCA Projects/2026/ConvoAI/report";
const SS = (f) => path.join(ROOT, "screenshots", f);
const LOGO = path.join(ROOT, "assets", "ksou_logo.jpeg");
const OUT = path.join(ROOT, "ConvoAI_Presentation.pptx");

const NAVY = "1F3A68", MAROON = "A01C1C", TEAL = "2A9D8F", TINT = "EEF3FA", INK = "1E1E1E", MUTED = "5A6472", WHITE = "FFFFFF", ORANGE = "E07A2F";
const HF = "Cambria", BF = "Calibri";

async function icon(Comp, color = WHITE, size = 256) {
  const svg = RDS.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
  pres.title = "ConvoAI: An Intelligent Conversational Chatbot Using Python and NLP";
  const W = 13.33;
  let n = 0;

  const footer = (s) => {
    n++;
    s.addText("ConvoAI  |  Shardul  |  MCA, KSOU", { x: 0.5, y: 7.05, w: 6, h: 0.3, fontFace: BF, fontSize: 10, color: MUTED, margin: 0 });
    s.addText(String(n), { x: W - 1.0, y: 7.05, w: 0.5, h: 0.3, fontFace: BF, fontSize: 10, color: MUTED, align: "right", margin: 0 });
  };
  const title = (s, t, sub) => {
    s.addText(t, { x: 0.5, y: 0.35, w: W - 1, h: 0.75, fontFace: HF, fontSize: 32, bold: true, color: NAVY, margin: 0 });
    if (sub) s.addText(sub, { x: 0.5, y: 1.08, w: W - 1, h: 0.4, fontFace: BF, fontSize: 15, italic: true, color: MAROON, margin: 0 });
  };
  const circleIcon = (s, data, x, y, d = 0.62, fill = NAVY) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill } });
    s.addImage({ data, x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52 });
  };
  const card = (s, x, y, w, h, fill = TINT) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill },
      shadow: { type: "outer", color: "000000", blur: 4, offset: 1, angle: 90, opacity: 0.12 } });
  const shot = (s, f, x, y, w, h) => s.addImage({ path: SS(f), x, y, w, h, sizing: { type: "cover", w, h },
    line: { color: "B8C2CF", width: 0.75 } });

  const I = {
    clock: await icon(fa.FaClock), file: await icon(fa.FaFileAlt), search: await icon(fa.FaSearch),
    robot: await icon(fa.FaRobot), ghost: await icon(fa.FaGhost), lock: await icon(fa.FaLock),
    comments: await icon(fa.FaComments), brain: await icon(fa.FaBrain), quote: await icon(fa.FaQuoteRight),
    ban: await icon(fa.FaBan), mic: await icon(fa.FaMicrophone), chart: await icon(fa.FaChartBar),
    server: await icon(fa.FaServer), db: await icon(fa.FaDatabase), cogs: await icon(fa.FaCogs),
    check: await icon(fa.FaCheckCircle), rocket: await icon(fa.FaRocket), shield: await icon(fa.FaShieldAlt),
    layer: await icon(fa.FaLayerGroup), users: await icon(fa.FaUsers), lang: await icon(fa.FaLanguage),
    plug: await icon(fa.FaPlug), eye: await icon(fa.FaEye), bolt: await icon(fa.FaBolt),
  };

  // 1 ── Title ------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: NAVY }; n++;
    s.addShape(pres.shapes.OVAL, { x: 0.6, y: 0.45, w: 1.25, h: 1.25, fill: { color: WHITE }, line: { color: WHITE } });
    s.addImage({ path: LOGO, x: 0.78, y: 0.55, w: 0.9, h: 1.03 });
    s.addText([{ text: "Karnataka State Open University", options: { fontSize: 24, bold: true, breakLine: true } },
               { text: "Department of Studies in Computer Science, Mukthagangothri, Mysuru-570006", options: { fontSize: 14 } }],
      { x: 2.05, y: 0.55, w: 10.5, h: 1.05, fontFace: HF, color: WHITE, margin: 0 });
    s.addText("MCA Major Project", { x: 0.6, y: 2.25, w: 6, h: 0.4, fontFace: BF, fontSize: 16, color: "CADCFC", margin: 0 });
    s.addText("ConvoAI", { x: 0.6, y: 2.65, w: 12, h: 1.0, fontFace: HF, fontSize: 54, bold: true, color: WHITE, margin: 0 });
    s.addText("An Intelligent Conversational Chatbot Using Python and Natural Language Processing",
      { x: 0.6, y: 3.6, w: 12.1, h: 0.95, fontFace: HF, fontSize: 24, color: WHITE, margin: 0, valign: "top" });
    s.addText("A local, retrieval-augmented company assistant that answers from your own documents, with citations",
      { x: 0.6, y: 4.6, w: 12, h: 0.45, fontFace: BF, fontSize: 16, italic: true, color: "CADCFC", margin: 0 });
    s.addText([{ text: "Presented by", options: { fontSize: 13, color: "CADCFC", breakLine: true } },
               { text: "SHARDUL", options: { fontSize: 20, bold: true, breakLine: true } },
               { text: "Roll No: 08P241216900293", options: { fontSize: 14 } }],
      { x: 0.6, y: 5.35, w: 5.5, h: 1.3, fontFace: BF, color: WHITE, margin: 0 });
    s.addText([{ text: "Under the guidance of", options: { fontSize: 13, color: "CADCFC", breakLine: true } },
               { text: "Dr. Naveen Kumar C.G.", options: { fontSize: 20, bold: true, breakLine: true } },
               { text: "Assistant Professor, DoS&R in Computer Science", options: { fontSize: 14 } }],
      { x: 7.0, y: 5.35, w: 5.8, h: 1.3, fontFace: BF, color: WHITE, margin: 0 });
    s.addNotes("Greet the examiners. Introduce yourself, the project title and your guide. One line: ConvoAI answers employees' questions from the organisation's own documents, cites the source, and runs entirely on one computer.");
  }

  // 2 ── Agenda -----------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Agenda");
    const items = ["Introduction", "Problem Statement", "Objectives", "Literature Survey", "Existing vs Proposed System",
      "Requirements", "Methodology", "System Design", "Implementation", "Results and Testing", "Novelty and Future Work", "Conclusion"];
    items.forEach((t, i) => {
      const col = i < 6 ? 0 : 1, row = i % 6;
      const x = 0.8 + col * 6.1, y = 1.55 + row * 0.85;
      s.addShape(pres.shapes.OVAL, { x, y, w: 0.55, h: 0.55, fill: { color: col ? TEAL : NAVY }, line: { color: col ? TEAL : NAVY } });
      s.addText(String(i + 1), { x, y, w: 0.55, h: 0.55, align: "center", valign: "middle", fontFace: BF, fontSize: 16, bold: true, color: WHITE, margin: 0 });
      s.addText(t, { x: x + 0.75, y, w: 4.8, h: 0.55, valign: "middle", fontFace: BF, fontSize: 20, color: INK, margin: 0 });
    });
    footer(s);
  }

  // 3 ── Introduction --------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Introduction", "Knowledge is in documents; people need it in seconds");
    s.addText([
      { text: "Employees ask the same questions daily: leave, travel claims, VPN, pricing, approvals.", options: { bullet: true, breakLine: true } },
      { text: "Intent-based chatbots answer only scripted questions; generic AI chatbots invent answers and send data to the cloud.", options: { bullet: true, breakLine: true } },
      { text: "ConvoAI keeps the NLP intent classifier from the synopsis and adds Retrieval-Augmented Generation (RAG).", options: { bullet: true, breakLine: true } },
      { text: "It answers from the organisation's own PDF, Word, text and web documents, cites every fact, and says so when it can't find an answer.", options: { bullet: true, breakLine: true } },
      { text: "Everything runs on one laptop: language model, search index, speech recognition and data.", options: { bullet: true } },
    ], { x: 0.5, y: 1.7, w: 5.6, h: 4.9, fontFace: BF, fontSize: 17, color: INK, paraSpaceAfter: 12, valign: "top", margin: 0 });
    shot(s, "02-chat-answer.png", 6.45, 1.7, 6.4, 4.0);
    s.addText("Cited answer to a question and its follow-up, from the Nimbus sample documents",
      { x: 6.45, y: 5.8, w: 6.4, h: 0.35, fontFace: BF, fontSize: 11, italic: true, color: MUTED, margin: 0 });
    footer(s);
    s.addNotes("Explain the setting: a fictional company, Nimbus Technologies, with HR, IT Support, Sales and General documents. Point at the screenshot: answer, citation chips, follow-up question.");
  }

  // 4 ── Problem statement ---------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Problem Statement");
    const P = [[I.clock, "Repetitive queries", "HR, IT and sales staff answer the same questions every day, only in office hours."],
      [I.file, "Buried in long documents", "Rules span dozens of pages; one answer can depend on another section."],
      [I.search, "Keyword search fails", "\"Carry forward leave\" does not find \"unused leave lapses at year end\"."],
      [I.robot, "Rigid chatbots", "Intent-only bots answer anticipated questions and need retraining for new content."],
      [I.ghost, "AI hallucination", "Generic LLMs don't know company rules and may invent plausible answers."],
      [I.lock, "Privacy", "Cloud chatbots require sending confidential documents to a third party."]];
    P.forEach(([ic, h, d], i) => {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.5 + col * 4.15, y = 1.55 + row * 2.55;
      card(s, x, y, 3.9, 2.3);
      circleIcon(s, ic, x + 0.3, y + 0.3, 0.62, MAROON);
      s.addText(h, { x: x + 1.1, y: y + 0.3, w: 2.65, h: 0.62, valign: "middle", fontFace: HF, fontSize: 18, bold: true, color: NAVY, margin: 0 });
      s.addText(d, { x: x + 0.3, y: y + 1.1, w: 3.35, h: 1.05, fontFace: BF, fontSize: 14, color: INK, valign: "top", margin: 0 });
    });
    footer(s);
    s.addNotes("Problem in one sentence: build an assistant that understands natural-language questions, answers accurately from the organisation's own documents with verifiable citations, declines what the documents don't cover, and runs on the organisation's own hardware.");
  }

  // 5 ── Objectives -----------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Objectives");
    const O = [[I.brain, "NLP intent classification", "Tokenise, remove stop words, lemmatise, TF-IDF; compare Naive Bayes vs Logistic Regression"],
      [I.quote, "Grounded answers with citations", "RAG: ingestion, chunking, embeddings, hybrid retrieval, local LLM"],
      [I.ban, "Honest fallback", "Decline out-of-scope questions using a tuned relevance threshold"],
      [I.comments, "Context awareness", "Rewrite follow-up questions into standalone ones"],
      [I.mic, "Modern interface", "Streaming chat, history, voice in/out, light/dark, phone layout"],
      [I.chart, "Admin, analytics, evaluation", "Manage documents and intents; measure classifier, retrieval and answers"]];
    O.forEach(([ic, h, d], i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.5 + col * 6.25, y = 1.5 + row * 1.75;
      circleIcon(s, ic, x, y + 0.1, 0.7, col ? TEAL : NAVY);
      s.addText(h, { x: x + 0.95, y, w: 5.1, h: 0.5, fontFace: HF, fontSize: 19, bold: true, color: NAVY, margin: 0 });
      s.addText(d, { x: x + 0.95, y: y + 0.5, w: 5.1, h: 0.85, fontFace: BF, fontSize: 15, color: INK, valign: "top", margin: 0 });
    });
    footer(s);
    s.addNotes("Main objective: answer natural-language questions from the organisation's documents, with citations, keeping all data local. Read out the six specific objectives.");
  }

  // 6 ── Literature survey -------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Literature Survey", "What earlier work offers, and what it leaves open");
    const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontFace: BF, fontSize: 14 } });
    const rows = [
      [hdr("Work"), hdr("Contribution"), hdr("Gap for this project")],
      ["Weizenbaum (1966) ELIZA", "Pattern-matching conversation", "No understanding; scripted answers only"],
      ["Bocklisch et al. (2017) Rasa", "ML intent classification + dialogue", "Answers only anticipated questions"],
      ["Robertson & Zaragoza (2009) BM25", "Strong keyword ranking", "Misses paraphrases and synonyms"],
      ["Karpukhin et al. (2020) DPR", "Dense semantic retrieval", "Misses exact names, codes, numbers"],
      ["Cormack et al. (2009) RRF", "Training-free fusion of rankings", "Cannot tell if anything is relevant"],
      ["Lewis et al. (2020) RAG", "Generate answers from retrieved passages", "Cloud scale; no 'not found' mechanism"],
      ["Ji et al. (2023) Hallucination survey", "Grounding reduces invented content", "Detection still unreliable; citations needed"],
    ];
    s.addTable(rows, { x: 0.5, y: 1.6, w: 12.33, colW: [3.4, 4.3, 4.63], fontFace: BF, fontSize: 13, color: INK,
      border: { type: "solid", pt: 0.5, color: "C9D2DE" }, fill: { color: WHITE }, rowH: 0.52, valign: "middle" });
    card(s, 0.5, 6.0, 12.33, 0.8, "FBEAEA");
    s.addText([{ text: "Research gap: ", options: { bold: true, color: MAROON } },
      { text: "no small, local system combines an interpretable intent classifier with hybrid RAG, a measured 'not found' gate and citations." }],
      { x: 0.75, y: 6.0, w: 11.9, h: 0.8, valign: "middle", fontFace: BF, fontSize: 15, color: INK, margin: 0 });
    footer(s);
    s.addNotes("Eleven works are reviewed in Chapter 2 of the report; these are the key ones. Emphasise the research gap.");
  }

  // 7 ── Existing vs proposed ---------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Existing System vs Proposed System");
    const colx = [0.5, 6.85], w = 5.98;
    [["Existing system", MAROON, ["Search shared folders with Ctrl+F", "Email HR / IT help desk; wait hours", "Static FAQ pages and scripted bots",
      "Paste documents into public AI chatbots", "No source shown; answers vary by person", "No insight into what people ask"]],
     ["Proposed: ConvoAI", TEAL, ["Ask in plain English or by voice; answer in ~3 s", "Understands meaning and follow-up questions",
      "Every fact cited; open the exact passage", "Says \"I couldn't find that\" instead of guessing",
      "Upload a document; searchable in seconds", "100% local; analytics reveal content gaps"]]].forEach(([h, c, items], k) => {
      const x = colx[k];
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w, h: 0.7, rectRadius: 0.08, fill: { color: c }, line: { color: c } });
      s.addText(h, { x, y: 1.5, w, h: 0.7, align: "center", valign: "middle", fontFace: HF, fontSize: 22, bold: true, color: WHITE, margin: 0 });
      card(s, x, 2.35, w, 4.45);
      s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })),
        { x: x + 0.3, y: 2.55, w: w - 0.6, h: 4.1, fontFace: BF, fontSize: 17, color: INK, paraSpaceAfter: 14, valign: "top", margin: 0 });
    });
    footer(s);
    s.addNotes("Contrast how employees find information today with ConvoAI. Mention feasibility: free open-source software, runs on existing hardware, no training needed for users.");
  }

  // 8 ── Requirements ---------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "System Requirements");
    circleIcon(s, I.server, 0.5, 1.5, 0.62, NAVY);
    s.addText("Hardware", { x: 1.3, y: 1.5, w: 4, h: 0.62, valign: "middle", fontFace: HF, fontSize: 22, bold: true, color: NAVY, margin: 0 });
    const hw = [["Processor", "AMD Ryzen 9 5900HS (min. quad-core)"], ["RAM", "39 GB (min. 16 GB)"], ["GPU", "RTX 3060 Laptop, 6 GB (optional)"],
      ["Storage", "SSD, 20 GB free (~7 GB models)"], ["Network", "Only for first-time setup"]];
    s.addTable(hw.map(([a, b]) => [{ text: a, options: { bold: true, color: NAVY } }, b]),
      { x: 0.5, y: 2.35, w: 5.6, colW: [1.5, 4.1], fontFace: BF, fontSize: 15, color: INK, rowH: 0.55,
        border: { type: "solid", pt: 0.5, color: "C9D2DE" }, fill: { color: TINT }, valign: "middle" });
    circleIcon(s, I.cogs, 6.75, 1.5, 0.62, TEAL);
    s.addText("Software", { x: 7.55, y: 1.5, w: 4, h: 0.62, valign: "middle", fontFace: HF, fontSize: 22, bold: true, color: NAVY, margin: 0 });
    const sw = [["Language", "Python 3.11"], ["Web", "Flask 3.1, Jinja2, Material Web, Chart.js"], ["NLP / ML", "NLTK 3.9, scikit-learn 1.7"],
      ["LLM runtime", "Ollama: qwen2.5:7b-instruct, llama3.2:3b"], ["Embeddings", "nomic-embed-text (768-d)"], ["Search", "ChromaDB 1.1 + rank-bm25"],
      ["Speech", "faster-whisper (Whisper small)"], ["Database", "SQLite 3"], ["Testing", "pytest, pytest-cov, Playwright"]];
    s.addTable(sw.map(([a, b]) => [{ text: a, options: { bold: true, color: NAVY } }, b]),
      { x: 6.75, y: 2.35, w: 6.08, colW: [1.6, 4.48], fontFace: BF, fontSize: 14, color: INK, rowH: 0.47,
        border: { type: "solid", pt: 0.5, color: "C9D2DE" }, fill: { color: TINT }, valign: "middle" });
    footer(s);
    s.addNotes("Without a GPU the system still runs; select llama3.2:3b in Settings. All software is free and open-source.");
  }

  // 9 ── Methodology (pipeline) -------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Methodology", "Every message flows through five stages");
    const st = [[I.file, "Ingest", "PDF/DOCX/TXT/MD/URL split into ~800-char chunks, embedded, indexed"],
      [I.brain, "Classify", "NLP pipeline + Logistic Regression; small talk answered in ~2 ms"],
      [I.search, "Retrieve", "Rewrite follow-ups; vector + BM25 search; Reciprocal Rank Fusion"],
      [I.shield, "Gate", "Best similarity < 0.618? Reply \"couldn't find it\""],
      [I.quote, "Answer", "Qwen2.5-7B answers only from top-5 passages, cites [1][2], streams"]];
    st.forEach(([ic, h, d], i) => {
      const x = 0.5 + i * 2.5, y = 1.9;
      card(s, x, y, 2.2, 3.9);
      s.addShape(pres.shapes.OVAL, { x: x + 0.65, y: y + 0.3, w: 0.9, h: 0.9, fill: { color: i === 3 ? MAROON : NAVY }, line: { color: i === 3 ? MAROON : NAVY } });
      s.addImage({ data: ic, x: x + 0.87, y: y + 0.52, w: 0.46, h: 0.46 });
      s.addText(`${i + 1}. ${h}`, { x: x + 0.1, y: y + 1.35, w: 2.0, h: 0.5, align: "center", fontFace: HF, fontSize: 19, bold: true, color: NAVY, margin: 0 });
      s.addText(d, { x: x + 0.2, y: y + 1.95, w: 1.8, h: 1.8, align: "center", valign: "top", fontFace: BF, fontSize: 13.5, color: INK, margin: 0 });
      if (i < 4) s.addShape(pres.shapes.RIGHT_TRIANGLE ? pres.shapes.CHEVRON : pres.shapes.CHEVRON,
        { x: x + 2.24, y: y + 1.75, w: 0.22, h: 0.4, fill: { color: TEAL }, line: { color: TEAL } });
    });
    s.addText("Developed iteratively in 10 phases: setup, intent engine, ingestion, RAG + router, chat UI, voice, admin, analytics, testing, documentation.",
      { x: 0.5, y: 6.1, w: 12.33, h: 0.5, fontFace: BF, fontSize: 14, italic: true, color: MUTED, margin: 0 });
    footer(s);
    s.addNotes("Walk through a question end to end. Stress that the documents are not used to retrain the model: they are retrieved at question time, so new uploads are searchable within seconds.");
  }

  // 10 ── Architecture ------------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "System Architecture", "Four tiers, one computer");
    const tiers = [["Presentation (browser)", NAVY, ["Chat + sources panel", "Voice recorder", "Admin pages", "Charts (Chart.js)"]],
      ["Application (Flask)", TEAL, ["Chat router", "Intent classifier", "Hybrid retriever", "Ingestion worker", "REST + SSE APIs"]],
      ["Data", "4A5A70", ["SQLite: users, chats, messages", "ChromaDB vectors + BM25", "Uploaded files"]],
      ["Local AI services", MAROON, ["Ollama: qwen2.5:7b / llama3.2:3b", "Ollama: nomic-embed-text", "faster-whisper"]]];
    tiers.forEach(([h, c, boxes], i) => {
      const y = 1.6 + i * 1.32;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y, w: 2.6, h: 1.05, rectRadius: 0.08, fill: { color: c }, line: { color: c } });
      s.addText(h, { x: 0.5, y, w: 2.6, h: 1.05, align: "center", valign: "middle", fontFace: HF, fontSize: 15, bold: true, color: WHITE, margin: 4 });
      const bw = (9.5 - (boxes.length - 1) * 0.15) / boxes.length;
      boxes.forEach((b, k) => {
        const x = 3.33 + k * (bw + 0.15);
        s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: 1.05, rectRadius: 0.06, fill: { color: TINT }, line: { color: c, width: 1 } });
        s.addText(b, { x, y, w: bw, h: 1.05, align: "center", valign: "middle", fontFace: BF, fontSize: 13.5, color: INK, margin: 4 });
      });
    });
    s.addText("HTML / JSON / Server-Sent Events between browser and Flask  ·  HTTP on localhost:11434 to Ollama  ·  no internet at run time",
      { x: 0.5, y: 6.95 - 0.35, w: 12.33, h: 0.35, fontFace: BF, fontSize: 12.5, italic: true, color: MUTED, margin: 0 });
    footer(s);
    s.addNotes("Presentation tier in the browser, Flask application tier, data tier (SQLite, ChromaDB, files), and local AI services via Ollama and Whisper. All on localhost.");
  }

  // 11 ── Hybrid retrieval ----------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Core Algorithm: Hybrid Retrieval and Relevance Gate");
    card(s, 0.5, 1.5, 6.0, 5.2);
    s.addText([
      { text: "1. Vector search ", options: { bold: true, color: NAVY } }, { text: "(meaning): top 20 by cosine similarity, filtered to the user's collections", options: { breakLine: true } },
      { text: "2. BM25 search ", options: { bold: true, color: NAVY } }, { text: "(keywords): top 20 over the same chunks", options: { breakLine: true } },
      { text: "3. Reciprocal Rank Fusion ", options: { bold: true, color: NAVY } }, { text: "combines both lists; keep top 5", options: { breakLine: true } },
      { text: "4. Relevance gate ", options: { bold: true, color: MAROON } }, { text: "relevant if best similarity ≥ 0.618, or ≥ 0.57 when BM25 agrees", options: { breakLine: true } },
      { text: "5. Grounded prompt ", options: { bold: true, color: NAVY } }, { text: "numbered sources; rules: cite every fact, never guess" },
    ], { x: 0.8, y: 1.75, w: 5.45, h: 4.7, fontFace: BF, fontSize: 16, color: INK, paraSpaceAfter: 14, valign: "top", margin: 0 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.85, y: 1.5, w: 5.98, h: 1.6, rectRadius: 0.08, fill: { color: NAVY }, line: { color: NAVY } });
    s.addText([{ text: "RRF(d) = Σ 1 / (60 + rankᵢ(d))", options: { fontSize: 26, bold: true, breakLine: true, fontFace: HF } },
      { text: "No score normalisation needed; chunks ranked well by both searches rise to the top", options: { fontSize: 14, color: "CADCFC" } }],
      { x: 7.05, y: 1.5, w: 5.6, h: 1.6, align: "center", valign: "middle", fontFace: BF, color: WHITE, margin: 0 });
    // threshold strip: answerable vs off-topic ranges
    s.addText("Best similarity on the test set (threshold separates them 100%)", { x: 6.85, y: 3.35, w: 5.98, h: 0.4, fontFace: BF, fontSize: 14, bold: true, color: NAVY, margin: 0 });
    const x0 = 6.95, x1 = 12.7, lo = 0.45, hi = 0.9, X = (v) => x0 + (v - lo) / (hi - lo) * (x1 - x0);
    s.addShape(pres.shapes.RECTANGLE, { x: X(0.468), y: 4.0, w: X(0.600) - X(0.468), h: 0.5, fill: { color: ORANGE }, line: { color: ORANGE } });
    s.addText("Off-topic 0.47–0.60", { x: X(0.468) - 0.1, y: 4.55, w: 2.4, h: 0.35, fontFace: BF, fontSize: 12, color: ORANGE, margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: X(0.636), y: 4.0, w: X(0.857) - X(0.636), h: 0.5, fill: { color: TEAL }, line: { color: TEAL } });
    s.addText("Answerable 0.64–0.86", { x: X(0.636), y: 4.55, w: 2.6, h: 0.35, fontFace: BF, fontSize: 12, color: TEAL, margin: 0 });
    s.addShape(pres.shapes.LINE, { x: X(0.618), y: 3.8, w: 0, h: 1.3, line: { color: MAROON, width: 2.5, dashType: "dash" } });
    s.addText("0.618", { x: X(0.618) - 0.5, y: 5.1, w: 1.0, h: 0.35, align: "center", fontFace: BF, fontSize: 13, bold: true, color: MAROON, margin: 0 });
    s.addText("Grey zone added after a real follow-up (\"Can I carry forward the casual leaves?\") scored 0.598 with the right passage ranked first; re-tested on 85 + 18 questions: 0 blocked, 0 let through.",
      { x: 6.85, y: 5.55, w: 5.98, h: 1.1, fontFace: BF, fontSize: 13, italic: true, color: MUTED, margin: 0, valign: "top" });
    footer(s);
    s.addNotes("This is the heart of the project. Explain why both searches are needed, how RRF works, and why the gate makes the assistant honest. The grey-zone rule came from a bug found while testing.");
  }

  // 12 ── Database design --------------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Database Design", "13 SQLite tables; chunk vectors live in ChromaDB");
    const ents = [["users", "id, name, email, role, theme"], ["collections", "id, name, icon, color"], ["user_collections", "user_id, collection_id"],
      ["documents", "id, collection_id, title, type, status, chunks"], ["conversations", "id, user_id, title, updated_at"],
      ["messages", "id, conversation_id, role, content, route, latency"], ["message_sources", "message_id, document_id, page, rank, cited"],
      ["feedback", "message_id, rating, comment"], ["intents / patterns / responses", "tag; example sentences; replies"],
      ["settings · model_runs", "key/value; NB vs LR scores"]];
    ents.forEach(([h, d], i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.5 + col * 4.0, y = 1.6 + row * 1.03;
      card(s, x, y, 3.8, 0.88);
      s.addText([{ text: h, options: { bold: true, color: NAVY, fontSize: 15, breakLine: true } }, { text: d, options: { fontSize: 12, color: MUTED } }],
        { x: x + 0.2, y, w: 3.45, h: 0.88, valign: "middle", fontFace: BF, margin: 0 });
    });
    card(s, 8.7, 1.6, 4.13, 5.0, "FFFFFF");
    s.addText("Key relationships", { x: 8.95, y: 1.75, w: 3.7, h: 0.45, fontFace: HF, fontSize: 18, bold: true, color: MAROON, margin: 0 });
    s.addText([
      "Collection 1–N Documents", "User M–N Collections (access control)", "User 1–N Conversations", "Conversation 1–N Messages",
      "Message 1–N Sources N–1 Document", "Message 1–0..1 Feedback", "Intent 1–N Patterns / Responses",
    ].map((t, i, a) => ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } })),
      { x: 8.95, y: 2.3, w: 3.7, h: 4.1, fontFace: BF, fontSize: 14.5, color: INK, paraSpaceAfter: 9, valign: "top", margin: 0 });
    footer(s);
    s.addNotes("Every answer is stored with its route, timing and sources, which powers analytics. A copy of each cited excerpt is kept so old answers keep their sources after re-indexing.");
  }

  // 13 ── Implementation modules --------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Implementation", "Seven Python packages, ~3,800 lines of application code");
    const M = [[I.brain, "nlp/", "preprocess, classifier (NB vs LR, grid search, threshold), train, evaluate"],
      [I.layer, "rag/", "loaders, chunker, embeddings, Chroma + BM25 store, hybrid retriever, prompts, LLM client"],
      [I.cogs, "services/", "router (chat pipeline), ingestion worker, Whisper speech, analytics"],
      [I.plug, "routes/", "page blueprints + REST and Server-Sent Events APIs"],
      [I.db, "models/", "SQLite schema, migrations, data access"],
      [I.eye, "templates/ static/", "Jinja2 + Material 3 web components, chat.js, voice.js, charts.js"]];
    M.forEach(([ic, h, d], i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.5 + col * 4.1, y = 1.6 + row * 1.7;
      circleIcon(s, ic, x, y, 0.6, col ? TEAL : NAVY);
      s.addText(h, { x: x + 0.8, y, w: 3.1, h: 0.45, fontFace: "Courier New", fontSize: 16, bold: true, color: NAVY, margin: 0 });
      s.addText(d, { x: x + 0.8, y: y + 0.45, w: 3.1, h: 1.1, fontFace: BF, fontSize: 13, color: INK, valign: "top", margin: 0 });
    });
    shot(s, "19-intent-try.png", 8.85, 1.6, 4.0, 2.5);
    s.addText("NLP pipeline shown for a test message", { x: 8.85, y: 4.15, w: 4.0, h: 0.3, fontFace: BF, fontSize: 11, italic: true, color: MUTED, margin: 0 });
    shot(s, "18-chunk-viewer.png", 8.85, 4.55, 4.0, 2.0);
    s.addText("Chunk viewer for an indexed document", { x: 8.85, y: 6.6, w: 4.0, h: 0.3, fontFace: BF, fontSize: 11, italic: true, color: MUTED, margin: 0 });
    footer(s);
    s.addNotes("Mention one-click setup.bat / start.bat. Show the NLP steps: normalise, tokenise, stop words, lemmas, TF-IDF.");
  }

  // 14 ── Screens: chat --------------------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Application Screens: Chat");
    shot(s, "03-sources-panel.png", 0.5, 1.4, 7.6, 4.75);
    s.addText("Click a citation: the sources panel opens at the passage with the question's words highlighted",
      { x: 0.5, y: 6.2, w: 7.6, h: 0.35, fontFace: BF, fontSize: 12, italic: true, color: MUTED, margin: 0 });
    shot(s, "04-routes.png", 8.45, 1.4, 4.38, 2.74);
    s.addText("Three routes: from documents, not found, quick reply", { x: 8.45, y: 4.17, w: 4.38, h: 0.3, fontFace: BF, fontSize: 11, italic: true, color: MUTED, margin: 0 });
    s.addImage({ path: SS("17-mobile-light.png"), x: 8.45, y: 4.6, w: 1.0, h: 2.16, sizing: { type: "cover", w: 1.0, h: 2.16 } });
    s.addText("Phone layout, voice input (on-device Whisper), read-aloud, light and dark themes, history with search and links.",
      { x: 9.6, y: 4.6, w: 3.23, h: 2.1, fontFace: BF, fontSize: 13.5, color: INK, valign: "top", margin: 0 });
    footer(s);
    s.addNotes("If the live demo is ready, switch to the browser here: ask 'How many casual leaves do I get per year?', then 'and can I carry them forward?', then 'What is the capital of France?'.");
  }

  // 15 ── Screens: admin ------------------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Application Screens: Administration and Analytics");
    const g = [["08-documents.png", "Documents: upload, live indexing status, re-index, move"], ["14-test-retrieval.png", "Test retrieval: vector vs keyword results"],
      ["07-admin-overview.png", "Overview: system status and counts"], ["11-analytics.png", "Analytics: routes, response time, content gaps"]];
    g.forEach(([f, c], i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.5 + col * 6.3, y = 1.4 + row * 2.85;
      shot(s, f, x, y, 6.0, 2.35);
      s.addText(c, { x, y: y + 2.38, w: 6.0, h: 0.3, fontFace: BF, fontSize: 12, italic: true, color: MUTED, margin: 0 });
    });
    footer(s);
    s.addNotes("Admins add knowledge by uploading files, no retraining. Analytics shows content gaps: questions the documents could not answer, which tells the organisation what to document next.");
  }

  // 16 ── Results: classifier -----------------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Results: Intent Classifier", "638 patterns, 25 intents; held-out set of 100 unseen phrasings");
    s.addChart(pres.charts.BAR, [
      { name: "Naive Bayes", labels: ["CV accuracy", "CV macro-F1", "Test accuracy", "Test macro-F1"], values: [0.732, 0.724, 0.890, 0.875] },
      { name: "Logistic Regression", labels: ["CV accuracy", "CV macro-F1", "Test accuracy", "Test macro-F1"], values: [0.762, 0.763, 0.910, 0.905] },
    ], { x: 0.5, y: 1.6, w: 7.6, h: 5.1, barDir: "col", barGrouping: "clustered", chartColors: [ORANGE, NAVY],
      showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelFormatCode: "0.000",
      valAxisMinVal: 0.6, valAxisMaxVal: 1.0, valAxisLabelFormatCode: "0.0", valGridLine: { color: "E2E6EC", size: 0.5 }, catGridLine: { style: "none" },
      catAxisLabelFontSize: 13, valAxisLabelFontSize: 11, catAxisLabelColor: MUTED, valAxisLabelColor: MUTED,
      showLegend: true, legendPos: "t", legendFontSize: 13, showTitle: false });
    const stats = [["0.905", "held-out macro-F1 (Logistic Regression, selected)"], ["91%", "held-out accuracy"], ["2 ms", "median quick-reply time"], ["0.35", "routing threshold chosen on held-out data"]];
    stats.forEach(([v, l], i) => {
      const y = 1.6 + i * 1.3;
      s.addText(v, { x: 8.5, y, w: 4.3, h: 0.7, fontFace: HF, fontSize: 36, bold: true, color: i === 0 ? MAROON : NAVY, margin: 0 });
      s.addText(l, { x: 8.5, y: y + 0.68, w: 4.3, h: 0.45, fontFace: BF, fontSize: 14, color: MUTED, margin: 0 });
    });
    footer(s);
    s.addNotes("Both models use word and character TF-IDF features with grid search and 5-fold stratified CV. Logistic Regression wins on every measure. The threshold minimises a cost where a wrong quick reply counts double.");
  }

  // 17 ── Results: retrieval and answers ------------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Results: Retrieval and Answers", "46 retrieval questions; 41 end-to-end document questions");
    const big = [["97.8%", "right passage in top 5", NAVY], ["0.935", "MRR (hybrid search)", NAVY], ["92.7%", "answers with the correct fact", TEAL],
      ["100%", "correct document cited", TEAL], ["100%", "off-topic questions declined", MAROON], ["1.6 s / 3.1 s", "first words / full answer", MAROON]];
    big.forEach(([v, l, c], i) => {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.5 + col * 2.6, y = 1.65 + row * 2.0;
      card(s, x, y, 2.4, 1.75);
      s.addText(v, { x, y: y + 0.2, w: 2.4, h: 0.8, align: "center", fontFace: HF, fontSize: v.length > 6 ? 24 : 32, bold: true, color: c, margin: 0 });
      s.addText(l, { x: x + 0.15, y: y + 1.0, w: 2.1, h: 0.6, align: "center", fontFace: BF, fontSize: 13, color: INK, margin: 0 });
    });
    s.addChart(pres.charts.BAR, [
      { name: "qwen2.5:7b", labels: ["Correct fact", "Correct citation", "Off-topic declined"], values: [92.7, 100, 100] },
      { name: "llama3.2:3b", labels: ["Correct fact", "Correct citation", "Off-topic declined"], values: [90.2, 53.7, 100] },
    ], { x: 8.4, y: 1.55, w: 4.45, h: 4.1, barDir: "col", barGrouping: "clustered", chartColors: [NAVY, ORANGE],
      showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelFormatCode: "0.0",
      valAxisMinVal: 0, valAxisMaxVal: 110, valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
      catAxisLabelFontSize: 11, catAxisLabelColor: MUTED, showLegend: true, legendPos: "t", legendFontSize: 12,
      showTitle: true, title: "Model comparison (%)", titleFontSize: 13, titleColor: NAVY });
    s.addText("The 3B model is 2x faster but omitted citations in almost half its answers, so the 7B model is the default.",
      { x: 8.4, y: 5.75, w: 4.45, h: 0.9, fontFace: BF, fontSize: 12.5, italic: true, color: MUTED, margin: 0, valign: "top" });
    footer(s);
    s.addNotes("Remaining errors (3 of 41) need conditions combined across sections, e.g. Pune per diem: the per-diem table says 'metro cities' while the list of metro cities is in the hotel section. Retrieval found the right passages; the 7B model misread them.");
  }

  // 18 ── Testing -----------------------------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Testing");
    const T = [["97 / 97", "automated pytest tests pass (85 s)"], ["80%", "line coverage (89% of in-app code)"], ["26", "user acceptance test cases, all passed"]];
    T.forEach(([v, l], i) => {
      const x = 0.5 + i * 4.15;
      card(s, x, 1.45, 3.9, 1.45);
      circleIcon(s, I.check, x + 0.25, 1.85, 0.62, TEAL);
      s.addText(v, { x: x + 1.05, y: 1.55, w: 2.75, h: 0.75, fontFace: HF, fontSize: 30, bold: true, color: NAVY, margin: 0 });
      s.addText(l, { x: x + 1.05, y: 2.27, w: 2.75, h: 0.55, fontFace: BF, fontSize: 13, color: INK, margin: 0 });
    });
    const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: NAVY } } });
    s.addTable([[hdr("Test case"), hdr("Expected"), hdr("Result")],
      ["\"hi\", \"thanks!\"", "Instant quick reply, no sources", "Pass"],
      ["Casual leave question + follow-up", "Cited answer; follow-up rewritten", "Pass"],
      ["\"What is the capital of France?\"", "Polite 'couldn't find', no guess", "Pass"],
      ["HR-only user asks about VPN", "IT documents never retrieved", "Pass"],
      ["Upload 41-page PDF", "Ready in ~6 s, chunks viewable", "Pass"],
      ["Setting 'sources per answer' = 50", "Rejected, field highlighted", "Pass"]],
      { x: 0.5, y: 3.2, w: 12.33, colW: [4.2, 6.6, 1.53], fontFace: BF, fontSize: 14, color: INK, rowH: 0.48,
        border: { type: "solid", pt: 0.5, color: "C9D2DE" }, fill: { color: WHITE }, valign: "middle" });
    s.addText("Methods: unit, integration, system, black-box, white-box, performance and user acceptance testing.",
      { x: 0.5, y: 6.6, w: 12.33, h: 0.35, fontFace: BF, fontSize: 13, italic: true, color: MUTED, margin: 0 });
    footer(s);
    s.addNotes("Unit tests use stand-ins for the LLM so they are fast and repeatable; the evaluation scripts exercise the real models end to end.");
  }

  // 19 ── Novelty & future ------------------------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); title(s, "Novelty and Future Enhancements");
    s.addText("What is new", { x: 0.5, y: 1.4, w: 6, h: 0.5, fontFace: HF, fontSize: 22, bold: true, color: MAROON, margin: 0 });
    const nov = [[I.bolt, "Hybrid router: classical NLP fast path + RAG"], [I.search, "Vector + BM25 fusion with a measured 'not found' gate"],
      [I.quote, "Verifiable: every fact cited, passage one click away"], [I.lock, "Fully local on a 6 GB laptop GPU"],
      [I.users, "Department access control inside the vector query"], [I.chart, "Evaluation built into the product (Metrics page)"]];
    nov.forEach(([ic, t], i) => {
      const y = 2.05 + i * 0.78;
      circleIcon(s, ic, 0.5, y, 0.5, NAVY);
      s.addText(t, { x: 1.2, y, w: 5.2, h: 0.5, valign: "middle", fontFace: BF, fontSize: 15, color: INK, margin: 0 });
    });
    card(s, 6.85, 1.4, 5.98, 5.3);
    s.addText("Future work", { x: 7.15, y: 1.6, w: 5.4, h: 0.5, fontFace: HF, fontSize: 22, bold: true, color: TEAL, margin: 0 });
    s.addText(["Larger / fine-tuned models for multi-section rules", "Cross-encoder re-ranking of passages", "OCR for scanned PDFs; table-aware chunking",
      "Kannada and Hindi answers", "Teams / Slack / WhatsApp integration", "Feedback loop to fix documents from content gaps", "GPU server + PostgreSQL + single sign-on"]
      .map((t, i, a) => ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } })),
      { x: 7.15, y: 2.2, w: 5.4, h: 4.3, fontFace: BF, fontSize: 15.5, color: INK, paraSpaceAfter: 10, valign: "top", margin: 0 });
    footer(s);
    s.addNotes("Voice and context awareness were future enhancements in the synopsis; both are now implemented.");
  }

  // 20 ── Conclusion -------------------------------------------------------------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: NAVY }; n++;
    s.addText("Conclusion", { x: 0.6, y: 0.5, w: 12, h: 0.8, fontFace: HF, fontSize: 38, bold: true, color: WHITE, margin: 0 });
    s.addText([
      { text: "ConvoAI keeps the synopsis's NLP intent classifier and extends it with local Retrieval-Augmented Generation.", options: { bullet: true, breakLine: true } },
      { text: "It gives instant small talk, cited answers from private documents and honest refusals, in about 3 seconds on a laptop GPU.", options: { bullet: true, breakLine: true } },
      { text: "Measured: 0.905 classifier macro-F1, 0.935 retrieval MRR, 92.7% correct answers, 100% correct citations.", options: { bullet: true, breakLine: true } },
      { text: "No data leaves the machine; 97 automated tests and a documented evaluation support the results.", options: { bullet: true } },
    ], { x: 0.6, y: 1.55, w: 12.1, h: 3.4, fontFace: BF, fontSize: 19, color: WHITE, paraSpaceAfter: 14, valign: "top", margin: 0 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.25, w: 12.13, h: 1.5, rectRadius: 0.1, fill: { color: WHITE }, line: { color: WHITE } });
    s.addText([{ text: "Thank you", options: { fontSize: 34, bold: true, color: NAVY, fontFace: HF, breakLine: true } },
      { text: "Questions and live demonstration", options: { fontSize: 17, color: MAROON } }],
      { x: 0.6, y: 5.25, w: 12.13, h: 1.5, align: "center", valign: "middle", fontFace: BF, margin: 0 });
    s.addNotes("Close with the one-line conclusion, then offer the live demo: start.bat, ask the three demo questions, open a source, show Documents upload and the Metrics page.");
  }

  await pres.writeFile({ fileName: OUT });
  console.log("wrote", OUT, "slides:", n);
})();
