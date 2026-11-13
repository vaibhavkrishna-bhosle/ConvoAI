"""Turn source documents into text sections with location metadata.

Every loader returns `list[Section]`. A section is a page (PDF), a heading
block (DOCX/Markdown/web page) or the whole file (TXT). The page number and
heading are what citations will show later ("HR Handbook.pdf · p.4").
"""
from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

SUPPORTED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx", ".txt": "txt", ".md": "md", ".markdown": "md"}
MAX_URL_BYTES = 5 * 1024 * 1024


class LoaderError(Exception):
    """A document could not be read; the message is shown to the admin."""


@dataclass
class Section:
    text: str
    page: int | None = None
    heading: str | None = None


@dataclass
class LoadedDocument:
    sections: list[Section]
    title: str | None = None
    page_count: int | None = None

    @property
    def char_count(self) -> int:
        return sum(len(s.text) for s in self.sections)


def source_type_for(filename: str) -> str | None:
    return SUPPORTED_EXTENSIONS.get(Path(filename).suffix.lower())


def clean(text: str) -> str:
    text = text.replace("\x00", "").replace("­", "")       # nulls, soft hyphens
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)                 # re-join hyphenated line breaks
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------- PDF
_DIGITS = re.compile(r"\d+")


def _strip_repeated_margins(pages: list[str]) -> list[str]:
    """Remove running headers/footers: edge lines (first/last 2) that repeat on most pages,
    ignoring page numbers ("Page 3/16" == "Page 4/16")."""
    if len(pages) < 3:
        return pages

    def edge_indexes(nonblank: list[int]) -> list[int]:
        depth = 2 if len(nonblank) >= 6 else 1  # short pages: only the very first/last line
        return nonblank[:depth] + nonblank[-depth:] if len(nonblank) > 2 else []

    counts: dict[str, int] = {}
    for text in pages:
        lines = text.splitlines()
        nonblank = [i for i, l in enumerate(lines) if l.strip()]
        for key in {_DIGITS.sub("#", lines[i].strip()) for i in edge_indexes(nonblank)}:
            counts[key] = counts.get(key, 0) + 1
    repeated = {k for k, n in counts.items() if n >= max(3, len(pages) // 2)}
    if not repeated:
        return pages
    out = []
    for text in pages:
        lines = text.splitlines()
        nonblank = [i for i, l in enumerate(lines) if l.strip()]
        edges = set(edge_indexes(nonblank))
        out.append("\n".join(l for i, l in enumerate(lines)
                             if not (i in edges and _DIGITS.sub("#", l.strip()) in repeated)))
    return out


def _reflow(text: str) -> str:
    """Join lines a PDF broke mid-sentence: a line not ending in punctuation followed by a lowercase start."""
    return re.sub(r"(?<![.:;!?|])\n(?=[a-z(])", " ", text)


def load_pdf(path: Path) -> LoadedDocument:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise LoaderError("PDF is password-protected.") from exc
        raw_pages = [page.extract_text() or "" for page in reader.pages]
        sections = []
        for number, text in enumerate(_strip_repeated_margins(raw_pages), start=1):
            text = _reflow(clean(text))
            if text:
                sections.append(Section(text=text, page=number))
        title = (reader.metadata.title if reader.metadata else None) or None
    except PdfReadError as exc:
        raise LoaderError(f"Could not read PDF: {exc}") from exc

    if not sections:
        raise LoaderError("No text found. This looks like a scanned PDF, which needs OCR (not supported yet).")
    return LoadedDocument(sections, title=title, page_count=len(reader.pages))


# --------------------------------------------------------------------------- DOCX
def load_docx(path: Path) -> LoadedDocument:
    import docx
    from docx.document import Document as _Doc
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document: _Doc = docx.Document(str(path))
    except Exception as exc:  # python-docx raises several types for bad files
        raise LoaderError(f"Could not read Word document: {exc}") from exc

    sections: list[Section] = []
    heading, buffer = None, []

    def flush():
        text = clean("\n".join(buffer))
        if text:
            sections.append(Section(text=text, heading=heading))
        buffer.clear()

    # Walk body elements in order so tables stay next to their heading
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            para = Paragraph(child, document)
            style = (para.style.name if para.style is not None else "") or ""
            text = para.text.strip()
            if not text:
                continue
            if style.lower().startswith(("heading", "title")):
                flush()
                heading = text
            elif style.lower().startswith("list"):
                buffer.append(f"- {text}")
            else:
                buffer.append(text)
        elif tag == "tbl":
            for row in Table(child, document).rows:
                cells = [c.text.strip() for c in row.cells]
                cells = [c for i, c in enumerate(cells) if c and (i == 0 or c != cells[i - 1])]  # merged cells
                if cells:
                    buffer.append(" | ".join(cells))
    flush()

    if not sections:
        raise LoaderError("The Word document has no text.")
    title = document.core_properties.title or None
    return LoadedDocument(sections, title=title)


# --------------------------------------------------------------------------- TXT / Markdown
def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# "3. PHISHING AND SUSPICIOUS EMAILS" / "LEAVE POLICY": short all-caps lines act as headings
_TXT_HEADING = re.compile(r"^(?:\d+[.)]\s+)?[A-Z][A-Z0-9 &/,()'\-]{3,78}$")


def load_txt(path: Path) -> LoadedDocument:
    text = clean(read_text_file(path))
    if not text:
        raise LoaderError("The text file is empty.")
    sections: list[Section] = []
    title, heading, buffer = None, None, []

    def flush():
        body = clean("\n".join(buffer))
        if body:
            sections.append(Section(text=body, heading=heading))
        buffer.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if _TXT_HEADING.match(stripped) and any(c.isalpha() for c in stripped):
            if title is None and not sections and not buffer:
                title = stripped.title()
            flush()
            heading = re.sub(r"^\d+[.)]\s+", "", stripped).capitalize()
        else:
            buffer.append(line)
    flush()
    return LoadedDocument(sections or [Section(text=text)], title=title)


_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def _strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?\n(.*?)```", r"\1", text, flags=re.S)       # keep code block contents
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)              # images → alt text
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)        # links → text (url)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)                    # bold
    text = re.sub(r"(?<!\w)[*_](.+?)[*_](?!\w)", r"\1", text)          # italics
    text = re.sub(r"`([^`]*)`", r"\1", text)                          # inline code
    text = re.sub(r"^\s*>\s?", "", text, flags=re.M)                  # blockquotes
    text = re.sub(r"^\s*[-*+]\s+", "- ", text, flags=re.M)            # bullets
    text = re.sub(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$", "", text, flags=re.M)  # table rules
    text = re.sub(r"^\|(.*)\|\s*$", lambda m: " | ".join(c.strip() for c in m.group(1).split("|")), text, flags=re.M)
    return text


def markdown_sections(markdown: str) -> tuple[list[Section], str | None]:
    sections: list[Section] = []
    title, heading, buffer = None, None, []

    def flush():
        text = clean(_strip_markdown("\n".join(buffer)))
        if text:
            sections.append(Section(text=text, heading=heading))
        buffer.clear()

    for line in markdown.splitlines():
        m = _MD_HEADING.match(line)
        if m:
            flush()
            heading = _strip_markdown(m.group(2)).strip()
            if len(m.group(1)) == 1 and title is None:
                title = heading
        else:
            buffer.append(line)
    flush()
    return sections, title


def load_md(path: Path) -> LoadedDocument:
    sections, title = markdown_sections(read_text_file(path))
    if not sections:
        raise LoaderError("The Markdown file has no text.")
    return LoadedDocument(sections, title=title)


# --------------------------------------------------------------------------- URL
def validate_url(url: str) -> str:
    """http(s) only, and never this machine or the local network (prevents SSRF)."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise LoaderError("Enter a full web address starting with http:// or https://")
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise LoaderError(f"Could not resolve {parsed.hostname}.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise LoaderError("Local and private network addresses are not allowed.")
    return url.strip()


def load_url(url: str) -> LoadedDocument:
    import requests
    import trafilatura

    url = validate_url(url)
    try:
        resp = requests.get(url, timeout=20, stream=True, allow_redirects=True,
                            headers={"User-Agent": "Mozilla/5.0 (compatible; ConvoAI/1.0; local document indexer)"})
        resp.raise_for_status()
        validate_url(resp.url)  # the final address after redirects must also be public
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype and "text" not in ctype:
            raise LoaderError(f"Unsupported content type: {ctype or 'unknown'}")
        body = resp.raw.read(MAX_URL_BYTES + 1, decode_content=True)
        if len(body) > MAX_URL_BYTES:
            raise LoaderError("The page is larger than 5 MB.")
    except requests.RequestException as exc:
        raise LoaderError(f"Could not fetch the page: {exc}") from exc

    html = body.decode(resp.encoding or "utf-8", errors="replace")
    if "html" not in ctype:
        text = clean(html)
        return LoadedDocument([Section(text=text)] if text else [], title=urlparse(url).netloc)

    markdown = trafilatura.extract(html, url=url, output_format="markdown", include_tables=True,
                                   include_links=False, include_comments=False, favor_precision=True)
    if not markdown:
        raise LoaderError("No readable article text was found on that page.")
    sections, md_title = markdown_sections(markdown)
    meta = trafilatura.extract_metadata(html, default_url=url)
    title = (meta.title if meta and meta.title else None) or md_title or urlparse(url).netloc
    if not sections:
        raise LoaderError("No readable article text was found on that page.")
    return LoadedDocument(sections, title=title)


# --------------------------------------------------------------------------- dispatcher
def load(source_type: str, path_or_url: str) -> LoadedDocument:
    if source_type == "url":
        return load_url(path_or_url)
    path = Path(path_or_url)
    if not path.exists():
        raise LoaderError("The uploaded file is missing from data/uploads.")
    loader = {"pdf": load_pdf, "docx": load_docx, "txt": load_txt, "md": load_md}.get(source_type)
    if loader is None:
        raise LoaderError(f"Unsupported document type: {source_type}")
    return loader(path)
