import re, subprocess, sys, shutil
from pathlib import Path
import fitz
from rb import Report, page_borders, page_num_format, C
import front as F
import ch1_4, ch5_6, ch7_9

OUT = F.ROOT / "report"
DOCX = OUT / "ConvoAI_Project_Report.docx"
SOFFICE = r"C:/Program Files/LibreOffice/program/soffice.exe"
TMP = Path(__file__).parent / "pdfout"
HEADER = "ConvoAI: An Intelligent Conversational Chatbot Using Python and NLP"
FOOTER = "Department of Studies in Computer Science, KSOU"


def body(r):
    ch1_4.ch1(r); ch1_4.ch2(r); ch1_4.ch3(r); ch1_4.ch4(r)
    ch5_6.ch5(r); ch5_6.ch6(r)
    ch7_9.ch7(r); ch7_9.ch8(r); ch7_9.ch9(r)
    ch7_9.bibliography(r); ch7_9.appendix(r); ch7_9.placeholders_pages(r)


def build(collected, pages):
    r = Report(pages)
    sec0 = r.doc.sections[0]
    page_borders(sec0)
    F.cover(r)
    s = r.new_section(); page_borders(s); page_num_format(s, "lowerRoman", 1)
    s.header.is_linked_to_previous = False
    s.footer.is_linked_to_previous = False
    from rb import add_field, _font
    fp = s.footer.paragraphs[0]; fp.alignment = C
    run = fp.add_run(); _font(run, 11); add_field(run, "PAGE")
    for fn in (F.proforma, F.guide_cert, F.chair_cert, F.declaration, F.examiner_cert, F.acknowledgement):
        fn(r); r.pagebreak()
    toc, figs, tabs = collected if collected else ([], [], [])
    F.list_of_figures(r, figs, pages); r.pagebreak()
    F.list_of_tables(r, tabs, pages); r.pagebreak()
    F.contents(r, toc, pages); r.pagebreak()
    F.abstract(r)
    s = r.new_section(); page_num_format(s, "decimal", 1)
    # no page border in the main body
    for pb in s._sectPr.xpath('./w:pgBorders'):
        s._sectPr.remove(pb)
    r.set_header_footer(s, HEADER, FOOTER)
    body(r)
    return r


def to_pdf(docx):
    TMP.mkdir(exist_ok=True)
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(TMP), str(docx)],
                   check=True, capture_output=True)
    return TMP / (docx.stem + ".pdf")


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def roman(n):
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s; n -= v
    return out


def find_pages(pdf, r):
    d = fitz.open(pdf)
    texts = [re.sub(r'^[ivxlc\d]+ ', '', norm(p.get_text())) for p in d]
    heads = [t[:400] for t in texts]
    pages = {}
    # front matter
    front_start = next(i for i, t in enumerate(heads) if "PROFORMA FOR PROJECT APPROVAL" in t)
    fronts = {"ANNEX1": "PROFORMA FOR PROJECT APPROVAL", "ANNEX2": "GUIDE CERTIFICATE", "ANNEX3": "CHAIRPERSON",
              "ANNEX4": "DECLARATION", "ANNEX5": "EXTERNAL EXAMINER CERTIFICATE", "ACK": "ACKNOWLEDGEMENT",
              "LOF": "LIST OF FIGURES", "LOT": "LIST OF TABLES", "ABS": "ABSTRACT"}
    for k, s in fronts.items():
        idx = next(i for i, t in enumerate(heads) if i >= front_start and t.startswith(s) or
                   (i >= front_start and k.startswith("ANNEX") and s in t[:300]))
        pages[k] = roman(idx - front_start + 1)
    ch1 = next(i for i, t in enumerate(heads) if "CHAPTER 1 INTRODUCTION" in t)
    label = lambda i: i - ch1 + 1
    cur = ch1
    starts = []
    for level, num, title, key in r.toc:
        if level == 1:
            needle = f"CHAPTER {num} {title}" if num else title
            needle = norm(needle)[:30]
            idx = next(i for i in range(cur, len(heads)) if needle in heads[i])
            starts.append((key, idx))
        else:
            needle = norm(key)[:28]
            idx = next(i for i in range(cur, len(texts)) if needle in texts[i])
        pages[key] = label(idx)
        cur = idx
    for k, (key, idx) in enumerate(starts):
        end = (starts[k + 1][1] - 1) if k + 1 < len(starts) else len(texts) - 1
        pages[key] = f"{label(idx)} - {label(end)}" if end > idx else str(label(idx))
    cur = ch1
    for num, title, cap in sorted(r.figs + r.tabs, key=lambda x: 0):
        pass
    for coll in (r.figs, r.tabs):
        cur = ch1
        for num, title, cap in coll:
            needle = norm(cap)[:len(cap.split(":")[0]) + 1]
            idx = next(i for i in range(cur, len(texts)) if needle in texts[i])
            pages[cap] = label(idx)
            cur = idx
    return pages, len(texts)


def main():
    r0 = build(None, {})                     # collect toc / figures / tables
    collected = (r0.toc, r0.figs, r0.tabs)
    pages = {}
    for attempt in range(3):
        r = build(collected, pages)
        r.save(DOCX)
        pdf = to_pdf(DOCX)
        new_pages, n = find_pages(pdf, r)
        print(f"pass {attempt}: {n} pages")
        if new_pages == pages:
            break
        pages = new_pages
    r = build(collected, pages); r.save(DOCX)
    pdf = to_pdf(DOCX)
    shutil.copy(pdf, OUT / "ConvoAI_Project_Report_preview.pdf")
    # prompts file
    lines = ["# ConvoAI report: image generation prompts", "",
             "Each figure placeholder in the report has the prompt below. Generate the image, insert it in Word "
             "at about 15 cm wide in place of the dashed box, and keep the caption under it.", ""]
    for num, title, kind, prompt in r.prompts:
        lines += [f"## Figure {num}: {title} ({kind.lower()})", "", prompt, ""]
    (OUT / "Image_Generation_Prompts.md").write_text("\n".join(lines), encoding="utf-8")
    print("figures", len(r.figs), "placeholders", len(r.prompts), "tables", len(r.tabs))


if __name__ == "__main__":
    main()
