"""Front matter in the KSOU sample's order."""
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor
from rb import set_widths, _font, C, L, J, R, NAVY, MAROON, GREEN, BLUE, no_borders, shade, cell_borders, page_borders
from pathlib import Path

ROOT = Path(r"D:/MCA Projects/2026/ConvoAI")
LOGO = ROOT / "report" / "assets" / "ksou_logo.jpeg"

STUDENT = "SHARDUL"
REGNO = "08P241216900293"
TITLE = "CONVOAI: AN INTELLIGENT CONVERSATIONAL CHATBOT USING PYTHON AND NATURAL LANGUAGE PROCESSING"
TITLE_Q = "“ConvoAI: An Intelligent Conversational Chatbot Using Python and Natural Language Processing”"
SUBTITLE = "(A Local Retrieval-Augmented Company Assistant)"
GUIDE = "Dr. Naveen Kumar C.G."
GUIDE_Q = "M.Sc., MCA, MBA, Ph.D."
DEGREE = "MASTER OF COMPUTER APPLICATIONS"
DEPT = "Department of Studies in Computer Science"
UNI = "Karnataka State Open University"
PLACE = "Mukthagangothri, Mysuru-570006"
DATE = "[FILL: DD.MM.2026]"


def letterhead(r, dept=True):
    para = r.doc.add_paragraph(); para.alignment = C; para.paragraph_format.space_after = Pt(0)
    para.add_run().add_picture(str(LOGO), width=Inches(0.95))
    r.center(UNI, 22, True, NAVY)
    r.center(PLACE, 13)
    if dept:
        q = r.center(DEPT, 14, True, BLUE)
        from rb import para_border
        para_border(q, "bottom", 12, "1F3A68")
    r.blank(1)


def annex_label(r, label):
    q = r.doc.add_paragraph(); q.alignment = R; q.paragraph_format.space_after = Pt(0)
    run = q.add_run(label); _font(run, 11, color=MAROON); run.underline = True


def cover(r):
    para = r.doc.add_paragraph(); para.alignment = C; para.paragraph_format.space_after = Pt(0)
    para.add_run().add_picture(str(LOGO), width=Inches(1.1))
    r.center(UNI, 24, True, NAVY)
    r.center(PLACE, 14)
    r.blank(1)
    r.center("A MAJOR PROJECT REPORT ON", 14)
    r.center(TITLE, 20, True, GREEN, spacing=1.2)
    r.center(SUBTITLE, 13, False, GREEN, italic=True)
    r.center("Submitted to", 13)
    r.center(f"{UNI} in partial fulfilment of the requirements for the award of the degree of", 13)
    r.blank(1)
    r.center(DEGREE, 15, True, BLUE)
    r.center("Submitted by", 13)
    r.center(STUDENT, 14, True, BLUE)
    r.center(f"Roll No: {REGNO}", 13)
    r.center("[FILL: Semester] - [FILL: Year/Cycle]", 13)
    r.center("Under the Guidance of", 13)
    r.center(f"{GUIDE} {GUIDE_Q}", 13, True)
    r.center("Assistant Professor", 13)
    r.center(f"Department of Studies & Research in Computer Science, {UNI}", 13)
    r.center(PLACE, 13)
    r.center("Carried out at", 13)
    r.center(DEPT, 13, True)
    r.center(f"{UNI}, {PLACE}", 13, True)
    r.center("[FILL: Month-2026]", 15, True, MAROON)


def kv_table(r, rows, widths=(2.2, 0.3, 3.75), size=12):
    t = r.doc.add_table(rows=0, cols=3); no_borders(t)
    for k, v in rows:
        cells = t.add_row().cells
        for i, (txt, w) in enumerate(zip((k, ":", v), widths)):
            cells[i].width = Inches(w)
            pp = cells[i].paragraphs[0]; pp.paragraph_format.line_spacing = 1.15; pp.paragraph_format.space_after = Pt(2)
            r.runs(pp, txt, size, bold=(i == 2 and k.startswith("Proposed")))
    set_widths(t, widths)
    return t


def proforma(r):
    annex_label(r, "Annexure-I")
    letterhead(r)
    r.center("PROFORMA FOR PROJECT APPROVAL", 15, True, MAROON, space_after=8)
    # photo box
    t = r.doc.add_table(rows=1, cols=2); no_borders(t)
    left, right = t.rows[0].cells
    left.width = Inches(4.9); right.width = Inches(1.3)
    pp = right.paragraphs[0]; pp.alignment = C
    cell_borders(right, 8, "1F3A68")
    run = pp.add_run("\n\n[FILL: Passport photo]\n\n"); _font(run, 9, color=MAROON)
    set_widths(t, [4.9, 1.3])
    left.paragraphs[0].text = ""
    r.runs(left.paragraphs[0], f"Register No  :  {REGNO}", 12)
    q = left.add_paragraph(); r.runs(q, f"Name of the Student  :  {STUDENT}", 12)
    kv_table(r, [
        ("Address", "[FILL: Full postal address with PIN code]"),
        ("Mobile No", "[FILL: Student mobile number]"),
        ("Name of the Guide", f"{GUIDE} {GUIDE_Q}"),
        ("Designation", "Assistant Professor, Department of Computer Science"),
        ("Office Address", f"{UNI}, Science Bhavan, {PLACE}"),
        ("Mobile No", "[FILL: Guide mobile number]"),
        ("Proposed Title of the Project", "CONVOAI: AN INTELLIGENT CONVERSATIONAL CHATBOT USING PYTHON AND NATURAL LANGUAGE PROCESSING"),
    ], size=11.5)
    r.blank(1)
    sig = r.doc.add_table(rows=2, cols=2); no_borders(sig)
    for i, (a, b) in enumerate((("Signature of the Student", "Signature of the Guide"), (f"Date: {DATE}", f"Date: {DATE}"))):
        for j, txt in enumerate((a, b)):
            pp = sig.rows[i].cells[j].paragraphs[0]; pp.alignment = L if j == 0 else R
            r.runs(pp, txt, 12, bold=True)
    set_widths(sig, [3.1, 3.1])
    r.blank(1)
    r.center("For office use only", 12, True, italic=True, space_after=4)
    ot = r.doc.add_table(rows=3, cols=2); ot.style = "Table Grid"; ot.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, (a, b) in enumerate((("Project Topic", ""), ("Approved", ""), ("Not Approved", ""))):
        for j, txt in enumerate((a, b)):
            c = ot.rows[i].cells[j]; c.width = Inches(1.8)
            pp = c.paragraphs[0]; pp.paragraph_format.line_spacing = 1.0
            run = pp.add_run(txt); _font(run, 11, True)
    set_widths(ot, [1.8, 1.8])
    r.blank(1)
    r.p("**Suggestions:**", L, indent_first=False)


def cert_page(r, label, heading, body_paras, sign_lines, place=True):
    annex_label(r, label)
    letterhead(r)
    r.center(heading, 15, True, MAROON, space_after=14)
    for b in body_paras:
        r.p(b, J, 12.5)
    r.blank(1)
    if place:
        r.p("Place : Mysuru", L, indent_first=False, space_after=0)
        r.p(f"Date  : {DATE}", L, indent_first=False)
    r.blank(2)
    for i, (txt, bold) in enumerate(sign_lines):
        q = r.doc.add_paragraph(); q.alignment = R; q.paragraph_format.space_after = Pt(0); q.paragraph_format.line_spacing = 1.15
        r.runs(q, txt, 12, bold=bold)


def guide_cert(r):
    cert_page(r, "Annexure-II", "GUIDE CERTIFICATE", [
        f"This is to certify that the project report entitled **{TITLE_Q}** is submitted by **{STUDENT}** bearing "
        f"**Register No: {REGNO}** to the {DEPT}, {UNI}, Mukthagangothri, Mysuru during the academic year "
        f"[FILL: 2025-26]. The work done under my guidance is satisfactory and is recommended for consideration as a "
        f"part of partial fulfilment for the award of the degree of Master of Computer Applications."],
        [("Signature of the Guide with Seal", True), (f"{GUIDE} {GUIDE_Q}", True),
         ("Assistant Professor, Dept. of Computer Science", False), (UNI + ",", False),
         ("Science Bhavan, Mukthagangothri,", False), ("Mysuru-570006", False)])


def chair_cert(r):
    cert_page(r, "Annexure-III", "CHAIRPERSON’S CERTIFICATE", [
        f"This is to certify that **{STUDENT}** bearing **Register No: {REGNO}** has successfully completed the "
        f"project work on **{TITLE_Q}** in partial fulfilment of the requirements for the award of the degree of "
        f"Master of Computer Applications by {UNI}, Mukthagangothri, Mysuru, during the academic year "
        f"[FILL: 2025-26], under the guidance of **{GUIDE}**, Assistant Professor, {DEPT}, {UNI}."],
        [("Chairperson", True), ("[FILL: Name of the Chairperson]", False),
         ("DoS & R in Computer Science", False), (UNI + ",", False),
         ("Science Bhavan, Mukthagangothri, Mysuru-570006", False)])


def declaration(r):
    cert_page(r, "Annexure-IV", "DECLARATION", [
        f"I, **{STUDENT}**, hereby declare that the project report entitled **{TITLE_Q}** is submitted to the "
        f"{DEPT}, {UNI}, Mukthagangothri, Mysuru, in partial fulfilment of the requirements for the award of the "
        f"degree of Master of Computer Applications. This is a record of original work carried out by me under the "
        f"guidance of **{GUIDE}**, Assistant Professor, {DEPT}, {UNI}, during the academic year [FILL: 2025-26].",
        "I further declare that the work reported in this project has not been submitted, either in part or in full, "
        "for the award of any other degree or diploma in this university or any other institution."],
        [("Signature of the Student", True), (STUDENT, True), (f"Register No: {REGNO}", True)])


def examiner_cert(r):
    annex_label(r, "Annexure-V")
    letterhead(r)
    r.center("EXTERNAL EXAMINER CERTIFICATE", 15, True, MAROON, space_after=14)
    r.p(f"This is to certify that **{STUDENT}** bearing **Register No: {REGNO}** has successfully completed the "
        f"project work on **{TITLE_Q}** and has presented and defended the same at the viva-voce examination held "
        f"on [FILL: date of viva], in partial fulfilment of the requirements for the award of the degree of Master of "
        f"Computer Applications by {UNI}, Mukthagangothri, Mysuru.", J, 12.5)
    r.blank(1)
    r.p("Place : Mysuru", L, indent_first=False, space_after=0)
    r.p(f"Date  : {DATE}", L, indent_first=False)
    r.blank(1)
    r.center("External Examiners / Viva", 13, True, space_after=10)
    t = r.doc.add_table(rows=3, cols=2); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (a, b) in enumerate((("Name of the External Examiner", "Signature with Date"), ("1.", ""), ("2.", ""))):
        for j, txt in enumerate((a, b)):
            c = t.rows[i].cells[j]; c.width = Inches(3.1)
            if i == 0: shade(c, "1F3A68")
            pp = c.paragraphs[0]; pp.paragraph_format.line_spacing = 2.2 if i else 1.2
            run = pp.add_run(txt); _font(run, 12, True, color=RGBColor(255, 255, 255) if i == 0 else None)
    set_widths(t, [3.1, 3.1])


def acknowledgement(r):
    r.center("ACKNOWLEDGEMENT", 16, True, space_after=14)
    paras = [
        "The successful completion of any project depends on the guidance, support and encouragement of many people. "
        "I take this opportunity to express my sincere gratitude to everyone who helped me complete this project.",
        f"I express my heartfelt thanks to the Vice-Chancellor and the Registrar of {UNI}, Mukthagangothri, Mysuru, "
        "for providing an excellent academic environment and the opportunity to pursue the Master of Computer "
        "Applications programme.",
        f"I extend my sincere gratitude to [FILL: Name of the Chairperson], Chairperson, {DEPT}, {UNI}, for "
        "the constant encouragement and for the facilities provided by the department during this work.",
        f"I am deeply grateful to my project guide, **{GUIDE}**, Assistant Professor, {DEPT}, {UNI}, for "
        "the valuable guidance, timely suggestions and patient reviews at every stage of this project. The "
        "direction given at the synopsis stage, especially on evaluating the system with measurable results, shaped "
        "the final form of this work.",
        f"I thank all the faculty members and the non-teaching staff of the {DEPT} for their co-operation and help "
        "throughout the course.",
        "I also acknowledge the open-source communities behind Python, Flask, NLTK, scikit-learn, ChromaDB, Ollama, "
        "Whisper and the Qwen and Nomic models, whose freely available work made a fully local assistant possible.",
        "Last but not least, I am thankful to my parents, family and friends for their encouragement, patience and "
        "support throughout my studies.",
    ]
    for t in paras:
        r.p(t, J, 12)
    r.blank(1)
    r.p("Place : Mysuru", L, indent_first=False, space_after=0)
    r.p(f"Date  : {DATE}", L, indent_first=False)
    q = r.doc.add_paragraph(); q.alignment = R; q.paragraph_format.space_after = Pt(0)
    r.runs(q, STUDENT, 13, True)
    q = r.doc.add_paragraph(); q.alignment = R
    r.runs(q, f"Register No: {REGNO}", 12, True)


def _list_table(r, header, rows, widths):
    t = r.doc.add_table(rows=1, cols=len(header)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    no_borders(t)
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.width = Inches(widths[i])
        pp = c.paragraphs[0]; pp.alignment = C if i != 1 else L
        run = pp.add_run(h); _font(run, 12, True, color=MAROON)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            c = cells[i]; c.width = Inches(widths[i])
            pp = c.paragraphs[0]; pp.paragraph_format.line_spacing = 1.15; pp.paragraph_format.space_after = Pt(2)
            pp.alignment = C if i != 1 else L
            run = pp.add_run(v); _font(run, 11.5)
    set_widths(t, widths)
    return t


def list_of_figures(r, figs, pages):
    r.center("LIST OF FIGURES", 16, True, space_after=12)
    _list_table(r, ["Figure No.", "Name of the Figure", "Page No."],
                [(f"Figure {n}", t, str(pages.get(cap, ""))) for n, t, cap in figs], (1.2, 4.2, 0.85))


def list_of_tables(r, tabs, pages):
    r.center("LIST OF TABLES", 16, True, space_after=12)
    _list_table(r, ["Table No.", "Table Name", "Page No."],
                [(f"Table {n}", t, str(pages.get(cap, ""))) for n, t, cap in tabs], (1.2, 4.2, 0.85))


FRONT_KEYS = [("Annexure-I", "PROFORMA FOR PROJECT APPROVAL", "ANNEX1"),
              ("Annexure-II", "GUIDE CERTIFICATE", "ANNEX2"),
              ("Annexure-III", "CHAIRPERSON’S CERTIFICATE", "ANNEX3"),
              ("Annexure-IV", "DECLARATION", "ANNEX4"),
              ("Annexure-V", "EXTERNAL EXAMINER CERTIFICATE", "ANNEX5"),
              ("", "ACKNOWLEDGEMENT", "ACK"),
              ("", "LIST OF FIGURES", "LOF"),
              ("", "LIST OF TABLES", "LOT"),
              ("", "ABSTRACT", "ABS")]


def contents(r, toc, pages):
    r.center("CONTENTS", 16, True, space_after=12)
    t = r.doc.add_table(rows=1, cols=3); t.alignment = WD_TABLE_ALIGNMENT.CENTER; no_borders(t)
    widths = (1.2, 4.25, 0.8)
    for i, h in enumerate(("Chapter No", "Chapter Title", "Page No")):
        c = t.rows[0].cells[i]; c.width = Inches(widths[i])
        pp = c.paragraphs[0]; pp.alignment = C if i != 1 else L
        run = pp.add_run(h); _font(run, 12, True, color=MAROON)

    def row(a, b, pg, bold, indent=0, size=12):
        cells = t.add_row().cells
        for i, v in enumerate((a, b, pg)):
            c = cells[i]; c.width = Inches(widths[i])
            pp = c.paragraphs[0]; pp.paragraph_format.line_spacing = 1.1; pp.paragraph_format.space_after = Pt(1)
            pp.alignment = C if i != 1 else L
            if i == 1 and indent: pp.paragraph_format.left_indent = Inches(0.25 * indent)
            run = pp.add_run(v); _font(run, size, bold)

    for lab, title, key in FRONT_KEYS:
        row(lab, title, str(pages.get(key, "")), False, size=11.5)
    row("", "", "", False, size=6)
    for level, num, title, key in toc:
        if level == 1:
            row("", "", "", False, size=4)
            row(num, title, str(pages.get(key, "")), True)
        else:
            row("", f"{num} {title}".strip(), str(pages.get(key, "")), False, indent=1, size=11.5)
    set_widths(t, widths)


ABSTRACT = [
    "Organisations answer the same questions about leave, travel claims, VPN access, pricing and procedures again and "
    "again. The answers already exist in policy documents, but employees cannot find them quickly, keyword search "
    "fails when a question is phrased differently, and cloud chatbots would send confidential documents outside the "
    "organisation. This project presents **ConvoAI**, an intelligent conversational assistant built with Python and "
    "Natural Language Processing (NLP) that answers questions from an organisation's own documents and runs entirely "
    "on a single computer.",
    "ConvoAI uses a hybrid design. A classical NLP pipeline (normalisation, tokenisation, stop-word removal, "
    "lemmatisation and TF-IDF features) feeds an intent classifier; Logistic Regression was selected after comparison "
    "with Multinomial Naive Bayes and answers greetings and small talk in about 2 milliseconds. All other questions "
    "are answered by Retrieval-Augmented Generation (RAG): uploaded PDF, Word, text, Markdown and web documents are "
    "split into overlapping chunks, embedded with nomic-embed-text and indexed in ChromaDB and a BM25 keyword index. "
    "At question time follow-up questions are rewritten into standalone questions, both indexes are searched and the "
    "results are fused with Reciprocal Rank Fusion. A relevance gate declines questions the documents do not cover, "
    "and a locally hosted 7-billion-parameter language model (Qwen2.5-7B-Instruct via Ollama) writes a streamed "
    "answer that cites its sources. The Flask web application provides a Material 3 chat interface, voice input with "
    "on-device Whisper, departmental collections with access control, an administration panel, usage analytics and a "
    "model-metrics page.",
    "On held-out tests the intent classifier reached 91.0% accuracy and 0.905 macro-F1, hybrid retrieval placed the "
    "correct passage in the top five results for 97.8% of questions (MRR 0.935), and complete answers were "
    "factually correct for 92.7% of questions with 100% correct citations, while every off-topic question was "
    "declined. Answers begin within 1.6 seconds and finish in about 3 seconds on a laptop GPU, and no data leaves the "
    "machine. The 97 automated tests pass with 80% line coverage.",
    "**Keywords:** Chatbot, Natural Language Processing, Intent Classification, Retrieval-Augmented Generation, "
    "Large Language Model, Hybrid Search, BM25, Vector Database, Flask, Speech Recognition.",
]


def abstract(r):
    r.center("ABSTRACT", 16, True, space_after=14)
    for t in ABSTRACT:
        r.p(t, J, 12)
