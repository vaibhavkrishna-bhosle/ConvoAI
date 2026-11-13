"""Build the sample company documents (fictional "Nimbus Technologies").

    .venv\\Scripts\\python tools/build_sample_docs.py

Converts the Markdown sources in tools/sample_docs_src/ into the formats
ConvoAI ingests, so every loader is exercised:
  HR/Nimbus Employee Handbook.pdf   (PDF, ~15 pages)
  HR/Travel and Expense Policy.docx (Word)
  Sales/NimbusDesk Product and Pricing Guide.docx (Word)
The Markdown and text samples in data/sample_docs/ are hand-written.
Requires fpdf2 (dev dependency): pip install fpdf2
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "sample_docs_src"
OUT = ROOT / "data" / "sample_docs"

ASCII = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...",
         " ": " "}


def ascii_text(s: str) -> str:
    for k, v in ASCII.items():
        s = s.replace(k, v)
    return s


def parse(md: str):
    """Yield blocks: ('h', level, text) | ('p', text) | ('ul', [items]) | ('ol', [items]) | ('table', rows)."""
    lines = ascii_text(md).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if m := re.match(r"^(#{1,3})\s+(.*)", line):
            yield ("h", len(m.group(1)), m.group(2).strip())
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            yield ("table", rows)
        elif re.match(r"^\s*-\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*-\s+", lines[i]):
                items.append(re.sub(r"^\s*-\s+", "", lines[i]).strip())
                i += 1
            yield ("ul", items)
        elif re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip())
                i += 1
            yield ("ol", items)
        else:
            para = [line.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||\s*-\s|\s*\d+\.\s)", lines[i]):
                para.append(lines[i].strip())
                i += 1
            yield ("p", " ".join(para))


# --------------------------------------------------------------------------- PDF
def to_pdf(md_path: Path, out_path: Path, title: str) -> int:
    from fpdf import FPDF
    from fpdf.fonts import FontFace

    class Doc(FPDF):
        def header(self):
            if self.page_no() > 1:
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(110)
                self.cell(0, 6, title, align="R")
                self.ln(10)

        def footer(self):
            self.set_y(-14)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(110)
            self.cell(0, 8, f"Nimbus Technologies - Internal - Page {self.page_no()}/{{nb}}", align="C")

    pdf = Doc(format="A4")
    pdf.set_title(title)
    pdf.set_author("Nimbus Technologies People Operations")
    pdf.set_margins(22, 20, 22)
    pdf.set_auto_page_break(True, margin=22)
    pdf.add_page()
    teal = (0, 106, 106)

    for block in parse(md_path.read_text(encoding="utf-8")):
        kind = block[0]
        if kind == "h":
            level, text = block[1], block[2]
            if level == 1:
                pdf.set_font("Helvetica", "B", 24)
                pdf.set_text_color(*teal)
                pdf.multi_cell(0, 11, text)
                pdf.ln(4)
            elif level == 2:
                if pdf.get_y() > 60:
                    pdf.add_page()  # each chapter starts on a new page
                pdf.set_font("Helvetica", "B", 16)
                pdf.set_text_color(*teal)
                pdf.multi_cell(0, 9, text)
                pdf.ln(2)
            else:
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 12.5)
                pdf.set_text_color(30)
                pdf.multi_cell(0, 7, text)
                pdf.ln(1)
        elif kind == "p":
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(25)
            pdf.multi_cell(0, 6.2, block[1], markdown=True)
            pdf.ln(3)
        elif kind in ("ul", "ol"):
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(25)
            for n, item in enumerate(block[1], start=1):
                marker = "-" if kind == "ul" else f"{n}."
                pdf.set_x(pdf.l_margin + 4)
                pdf.cell(7, 6.2, marker)
                pdf.multi_cell(0, 6.2, item, markdown=True)
                pdf.ln(1)
            pdf.ln(2)
        elif kind == "table":
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(25)
            with pdf.table(headings_style=FontFace(emphasis="BOLD", color=255, fill_color=teal),
                           line_height=5.6, padding=1.6, text_align="LEFT") as table:
                for row in block[1]:
                    r = table.row()
                    for cell in row:
                        r.cell(cell)
            pdf.ln(4)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return pdf.page_no()


# --------------------------------------------------------------------------- DOCX
def to_docx(md_path: Path, out_path: Path, title: str) -> None:
    import docx
    from docx.shared import Pt, RGBColor

    document = docx.Document()
    document.core_properties.title = title
    document.core_properties.author = "Nimbus Technologies"
    document.styles["Normal"].font.name = "Calibri"
    document.styles["Normal"].font.size = Pt(11)

    def add_runs(paragraph, text):
        for part in re.split(r"(\*\*[^*]+\*\*)", text):
            if part.startswith("**") and part.endswith("**"):
                paragraph.add_run(part[2:-2]).bold = True
            elif part:
                paragraph.add_run(part)

    for block in parse(md_path.read_text(encoding="utf-8")):
        kind = block[0]
        if kind == "h":
            document.add_heading(block[2], level=0 if block[1] == 1 else block[1] - 1)
        elif kind == "p":
            add_runs(document.add_paragraph(), block[1])
        elif kind == "ul":
            for item in block[1]:
                add_runs(document.add_paragraph(style="List Bullet"), item)
        elif kind == "ol":
            for item in block[1]:
                add_runs(document.add_paragraph(style="List Number"), item)
        elif kind == "table":
            rows = block[1]
            table = document.add_table(rows=len(rows), cols=len(rows[0]))
            table.style = "Light Grid Accent 1"
            for r, row in enumerate(rows):
                for c, text in enumerate(row):
                    cell = table.cell(r, c)
                    cell.text = text
                    if r == 0:
                        for run in cell.paragraphs[0].runs:
                            run.bold = True
                            run.font.color.rgb = RGBColor(0, 0x50, 0x50)
            document.add_paragraph()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(out_path))


def main() -> None:
    pages = to_pdf(SRC / "employee_handbook.md", OUT / "HR" / "Nimbus Employee Handbook.pdf",
                   "Nimbus Technologies Employee Handbook")
    print(f"HR/Nimbus Employee Handbook.pdf  ({pages} pages)")
    to_docx(SRC / "travel_expense_policy.md", OUT / "HR" / "Travel and Expense Policy.docx", "Travel and Expense Policy")
    print("HR/Travel and Expense Policy.docx")
    to_docx(SRC / "pricing_guide.md", OUT / "Sales" / "NimbusDesk Product and Pricing Guide.docx",
            "NimbusDesk Product and Pricing Guide")
    print("Sales/NimbusDesk Product and Pricing Guide.docx")


if __name__ == "__main__":
    main()
