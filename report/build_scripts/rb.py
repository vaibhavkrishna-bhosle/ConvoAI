"""Report builder helpers on python-docx (KSOU format: TNR, 16/14/12 pt, 1.5 spacing, justified)."""
import re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, Inches, RGBColor, Emu

FONT = "Times New Roman"
NAVY = RGBColor(0x1F, 0x3A, 0x68)
MAROON = RGBColor(0xA0, 0x1C, 0x1C)
GREEN = RGBColor(0x0B, 0x6E, 0x3C)
BLUE = RGBColor(0x1A, 0x4F, 0xA0)
J, C, L, R = WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT


def _font(run, size=None, bold=None, italic=None, color=None, name=FONT):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if italic is not None: run.italic = italic
    if color is not None: run.font.color.rgb = color


def _style_font(style, size, bold=False, color=RGBColor(0, 0, 0)):
    style.font.name = FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = False
    style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]


def set_widths(table, widths_in):
    """Fix column widths in the table grid and every cell (LibreOffice and Word both honour this)."""
    table.autofit = False
    tblPr = table._tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    grid = table._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths_in):
        gc.set(qn("w:w"), str(int(w * 1440)))
    for row in table.rows:
        for c, w in zip(row.cells, widths_in):
            c.width = Inches(w)


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def cell_borders(cell, sz=8, color="000000", val="single"):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), val); e.set(qn("w:sz"), str(sz)); e.set(qn("w:color"), color)
        b.append(e)
    tcPr.append(b)


def no_borders(table):
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:val"), "nil"); b.append(e)
    tblPr.append(b)


def para_border(p, side="bottom", sz=6, color="1F3A68"):
    pPr = p._p.get_or_add_pPr()
    pb = OxmlElement("w:pBdr")
    e = OxmlElement(f"w:{side}")
    e.set(qn("w:val"), "single"); e.set(qn("w:sz"), str(sz)); e.set(qn("w:space"), "1"); e.set(qn("w:color"), color)
    pb.append(e); pPr.append(pb)


def add_field(run, instr):
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "1"
    f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
    for e in (f1, it, f2, t, f3):
        run._r.append(e)


def page_borders(section, color="1F3A68"):
    sp = section._sectPr
    pb = OxmlElement("w:pgBorders"); pb.set(qn("w:offsetFrom"), "page")
    for side in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "double"); e.set(qn("w:sz"), "6"); e.set(qn("w:space"), "24"); e.set(qn("w:color"), color)
        pb.append(e)
    # pgBorders must come after pgMar / before cols etc.; append then reorder is fine for Word & LO
    pgMar = sp.find(qn("w:pgMar"))
    pgMar.addnext(pb)


def page_num_format(section, fmt="decimal", start=1):
    sp = section._sectPr
    pg = sp.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType"); sp.append(pg)
    pg.set(qn("w:fmt"), fmt); pg.set(qn("w:start"), str(start))


class Report:
    def __init__(self, pages=None):
        self.doc = Document()
        self.pages = pages or {}          # key -> page label from previous pass
        self.figs, self.tabs, self.toc = [], [], []   # (num, title, key)
        self.chapter = 0
        self.fig_n = self.tab_n = 0
        self.prompts = []                 # (fig num, title, prompt) for the prompts appendix file
        self._setup()

    # ------------------------------------------------------------------ setup
    def _setup(self):
        d = self.doc
        st = d.styles
        n = st["Normal"]
        _style_font(n, 12)
        n.paragraph_format.line_spacing = 1.5
        n.paragraph_format.space_after = Pt(6)
        n.paragraph_format.alignment = J
        h1 = st["Heading 1"]; _style_font(h1, 16, True)
        h1.paragraph_format.alignment = C; h1.paragraph_format.space_before = Pt(0); h1.paragraph_format.space_after = Pt(18)
        h1.paragraph_format.line_spacing = 1.5; h1.paragraph_format.keep_with_next = True
        h2 = st["Heading 2"]; _style_font(h2, 14, True)
        h2.paragraph_format.space_before = Pt(12); h2.paragraph_format.space_after = Pt(6); h2.paragraph_format.line_spacing = 1.5
        h2.paragraph_format.alignment = L
        h3 = st["Heading 3"]; _style_font(h3, 12, True)
        h3.paragraph_format.space_before = Pt(8); h3.paragraph_format.space_after = Pt(4); h3.paragraph_format.line_spacing = 1.5
        h3.paragraph_format.alignment = L
        for s in ("List Bullet", "List Bullet 2"):
            _style_font(st[s], 12)
            st[s].paragraph_format.line_spacing = 1.5
            st[s].paragraph_format.alignment = J
            st[s].paragraph_format.space_after = Pt(3)
        cap = st["Caption"]; _style_font(cap, 12, True)
        cap.paragraph_format.alignment = C; cap.paragraph_format.space_before = Pt(4); cap.paragraph_format.space_after = Pt(12)
        sec = d.sections[0]
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        self._margins(sec)

    def _margins(self, sec):
        sec.left_margin = Inches(1.25); sec.right_margin = Inches(1.0)
        sec.top_margin = Inches(1.0); sec.bottom_margin = Inches(1.0)
        sec.header_distance = Inches(0.45); sec.footer_distance = Inches(0.45)

    def new_section(self):
        s = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self._margins(s)
        return s

    def set_header_footer(self, sec, header_text=None, footer_text=None, page=True):
        sec.header.is_linked_to_previous = False
        sec.footer.is_linked_to_previous = False
        hp = sec.header.paragraphs[0]; hp.text = ""
        fp = sec.footer.paragraphs[0]; fp.text = ""
        if header_text:
            r = hp.add_run(header_text); _font(r, 10, italic=True, color=NAVY)
            hp.alignment = L
            para_border(hp, "bottom")
        if footer_text or page:
            ts = fp.paragraph_format.tab_stops
            ts.add_tab_stop(Inches(3.25), WD_TAB_ALIGNMENT.CLEAR)
            ts.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.CLEAR)
            ts.add_tab_stop(Inches(6.0), WD_TAB_ALIGNMENT.RIGHT)
            if footer_text:
                r = fp.add_run(footer_text); _font(r, 10, color=NAVY)
            if page:
                r = fp.add_run("\t"); _font(r, 10)
                r = fp.add_run(); _font(r, 10, bold=True); add_field(r, "PAGE")
            para_border(fp, "top")

    # ------------------------------------------------------------------ text
    def runs(self, p, text, size=12, bold=False, italic=False, color=None):
        """**bold**, *italic*, `code`, [FILL ...] highlighted."""
        tokens = re.split(r"(\*\*.+?\*\*|`[^`]+`|\[FILL[^\]]*\]|(?<!\*)\*[^*\s][^*]*?\*(?!\*))", text)
        for t in tokens:
            if not t:
                continue
            if t.startswith("**") and t.endswith("**"):
                r = p.add_run(t[2:-2]); _font(r, size, True, italic, color)
            elif t.startswith("`") and t.endswith("`"):
                r = p.add_run(t[1:-1]); _font(r, size - 1, bold, italic, color, name="Consolas")
            elif t.startswith("[FILL"):
                r = p.add_run(t); _font(r, size, True, italic, MAROON); r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            elif t.startswith("*") and t.endswith("*") and len(t) > 2:
                r = p.add_run(t[1:-1]); _font(r, size, bold, True, color)
            else:
                r = p.add_run(t); _font(r, size, bold, italic, color)
        return p

    def p(self, text, align=J, size=12, bold=False, italic=False, color=None, indent_first=True, space_after=6,
          spacing=1.5, keep=False):
        para = self.doc.add_paragraph()
        para.alignment = align
        pf = para.paragraph_format
        pf.line_spacing = spacing
        pf.space_after = Pt(space_after)
        if keep: pf.keep_with_next = True
        if indent_first and align == J:
            pf.first_line_indent = Inches(0.5)
        self.runs(para, text, size, bold, italic, color)
        return para

    def center(self, text, size=12, bold=False, color=None, space_after=0, italic=False, spacing=1.15):
        return self.p(text, C, size, bold, italic, color, False, space_after, spacing)

    def blank(self, n=1, size=12):
        for _ in range(n):
            q = self.doc.add_paragraph(); q.paragraph_format.space_after = Pt(0)
            q.paragraph_format.line_spacing = 1.0
            r = q.add_run(""); _font(r, size)

    def bullets(self, items, level=1):
        style = "List Bullet" if level == 1 else "List Bullet 2"
        for it in items:
            para = self.doc.add_paragraph(style=style)
            para.alignment = J
            m = re.match(r"^([^:]{2,60}):\s(.+)$", it)
            if m and not it.startswith("**"):
                self.runs(para, f"**{m.group(1)}:** {m.group(2)}")
            else:
                self.runs(para, it)

    def numbered(self, items):
        for i, it in enumerate(items, 1):
            para = self.doc.add_paragraph()
            para.alignment = J
            pf = para.paragraph_format
            pf.left_indent = Inches(0.5); pf.first_line_indent = Inches(-0.3); pf.space_after = Pt(3)
            self.runs(para, f"{i}.  " + it)

    def pagebreak(self):
        para = self.doc.add_paragraph(); para.paragraph_format.space_after = Pt(0)
        para.add_run().add_break(WD_BREAK.PAGE)

    # ------------------------------------------------------------------ structure
    def chapter_start(self, title, first=False):
        self.chapter += 1
        self.fig_n = self.tab_n = 0
        if not first:
            self.pagebreak()
        h = self.doc.add_heading(level=1)
        r = h.add_run(f"CHAPTER {self.chapter}"); _font(r, 16, True, color=RGBColor(0, 0, 0))
        r.add_break()
        r = h.add_run(title.upper()); _font(r, 16, True, color=RGBColor(0, 0, 0))
        key = f"CH{self.chapter}"
        self.toc.append((1, str(self.chapter), title.upper(), key))
        self.sub = 0

    def unnumbered_chapter(self, title, key, pagebreak=True):
        if pagebreak:
            self.pagebreak()
        h = self.doc.add_heading(level=1)
        r = h.add_run(title.upper()); _font(r, 16, True, color=RGBColor(0, 0, 0))
        self.toc.append((1, "", title.upper(), key))

    def h2(self, title, numbered=True, toc=True):
        if numbered:
            self.sub += 1; self.subsub = 0
            label = f"{self.chapter}.{self.sub} {title}"
        else:
            label = title
        h = self.doc.add_heading(level=2)
        r = h.add_run(label); _font(r, 14, True, color=RGBColor(0, 0, 0))
        if toc:
            self.toc.append((2, f"{self.chapter}.{self.sub}" if numbered else "", title, label))

    def h3(self, title, numbered=True):
        if numbered:
            self.subsub += 1
            label = f"{self.chapter}.{self.sub}.{self.subsub} {title}"
        else:
            label = title
        h = self.doc.add_heading(level=3)
        r = h.add_run(label); _font(r, 12, True, color=RGBColor(0, 0, 0))

    # ------------------------------------------------------------------ figures and tables
    def _caption(self, text):
        cp = self.doc.add_paragraph(style="Caption")
        r = cp.add_run(text); _font(r, 12, True, color=RGBColor(0, 0, 0))
        return cp

    def figure_placeholder(self, title, prompt, kind="Diagram", height_lines=3):
        self.fig_n += 1
        num = f"{self.chapter}.{self.fig_n}" if self.chapter else f"A.{self.fig_n}"
        cap = f"Figure {num}: {title}"
        t = self.doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.rows[0].cells[0]
        cell.width = Inches(6.0)
        shade(cell, "EEF3FA"); cell_borders(cell, 12, "1F3A68", "dashed")
        p0 = cell.paragraphs[0]; p0.alignment = C
        p0.paragraph_format.line_spacing = 1.15; p0.paragraph_format.space_before = Pt(8)
        r = p0.add_run(f"[ {kind.upper()} PLACEHOLDER: Figure {num} ]"); _font(r, 12, True, color=NAVY)
        q = cell.add_paragraph(); q.alignment = C; q.paragraph_format.line_spacing = 1.15
        r = q.add_run("Replace this box with the generated image (insert at about 15 cm wide), then delete this box."); _font(r, 10, italic=True, color=RGBColor(0x55, 0x55, 0x55))
        q = cell.add_paragraph(); q.alignment = L; q.paragraph_format.line_spacing = 1.15
        q.paragraph_format.left_indent = Inches(0.1); q.paragraph_format.right_indent = Inches(0.1)
        r = q.add_run("Image generation prompt: "); _font(r, 10.5, True, color=MAROON)
        r = q.add_run(prompt); _font(r, 10.5, color=RGBColor(0x22, 0x22, 0x22))
        q.paragraph_format.space_after = Pt(8)
        q.alignment = J
        set_widths(t, [6.0])
        trPr = t.rows[0]._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); trPr.append(cs)
        for cp_ in cell.paragraphs:
            cp_.paragraph_format.keep_with_next = True
        self._caption(cap)
        self.figs.append((num, title, cap))
        self.prompts.append((num, title, kind, prompt))
        return num

    def screenshot(self, title, path, width_in=6.0, crop_height=None):
        self.fig_n += 1
        num = f"{self.chapter}.{self.fig_n}" if self.chapter else f"A.{self.fig_n}"
        if self.appendix_prefix:
            num = f"{self.appendix_prefix}.{self.fig_n}"
        cap = f"Figure {num}: {title}"
        para = self.doc.add_paragraph(); para.alignment = C
        para.paragraph_format.keep_with_next = True; para.paragraph_format.space_after = Pt(0)
        para.paragraph_format.line_spacing = 1.0
        run = para.add_run()
        pic = run.add_picture(str(path), width=Inches(width_in))
        # thin border around the picture
        spPr = pic._inline.graphic.graphicData.pic.spPr
        ln = OxmlElement("a:ln"); ln.set("w", "9525")
        sf = OxmlElement("a:solidFill"); clr = OxmlElement("a:srgbClr"); clr.set("val", "9AA5B1"); sf.append(clr); ln.append(sf)
        spPr.append(ln)
        self._caption(cap)
        self.figs.append((num, title, cap))
        return num

    appendix_prefix = None

    def table(self, title, header, rows, widths=None, size=11, align_first_center=False):
        self.tab_n += 1
        num = f"{self.chapter}.{self.tab_n}"
        cap = f"Table {num}: {title}"
        cp = self._caption(cap)
        cp.paragraph_format.keep_with_next = True; cp.paragraph_format.space_after = Pt(4)
        t = self.doc.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
        total = 6.25
        widths = widths or [total / len(header)] * len(header)
        scale = total / sum(widths)
        widths = [w * scale for w in widths]
        for i, h in enumerate(header):
            c = t.rows[0].cells[i]; c.width = Inches(widths[i]); shade(c, "1F3A68")
            pp = c.paragraphs[0]; pp.alignment = C; pp.paragraph_format.line_spacing = 1.15; pp.paragraph_format.space_after = Pt(2)
            r = pp.add_run(h); _font(r, size, True, color=RGBColor(0xFF, 0xFF, 0xFF))
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        # repeat header row
        trPr = t.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for i, v in enumerate(row):
                c = cells[i]; c.width = Inches(widths[i])
                if ri % 2 == 1: shade(c, "EEF3FA")
                pp = c.paragraphs[0]; pp.alignment = L
                pp.paragraph_format.line_spacing = 1.15; pp.paragraph_format.space_after = Pt(2)
                self.runs(pp, str(v), size)
        set_widths(t, widths)
        sp = self.doc.add_paragraph(); sp.paragraph_format.space_after = Pt(6); sp.paragraph_format.line_spacing = 1.0
        self.tabs.append((num, title, cap))
        return t

    def code(self, text, title=None):
        if title:
            q = self.doc.add_paragraph(); q.paragraph_format.keep_with_next = True; q.paragraph_format.space_after = Pt(2)
            r = q.add_run(title); _font(r, 11, True, italic=True, color=NAVY)
        t = self.doc.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.rows[0].cells[0]; c.width = Inches(6.25); shade(c, "F5F5F5"); cell_borders(c, 4, "B0B0B0")
        lines = text.strip("\n").split("\n")
        first = True
        for ln in lines:
            pp = c.paragraphs[0] if first else c.add_paragraph()
            first = False
            pp.alignment = L
            pp.paragraph_format.line_spacing = 1.0; pp.paragraph_format.space_after = Pt(0)
            r = pp.add_run(ln if ln else " "); _font(r, 9, name="Consolas")
        set_widths(t, [6.25])
        sp = self.doc.add_paragraph(); sp.paragraph_format.space_after = Pt(4); sp.paragraph_format.line_spacing = 1.0

    def page_of(self, key):
        return self.pages.get(key, "")

    def save(self, path):
        self.doc.save(path)
