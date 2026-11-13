"""Split sections into overlapping chunks for embedding.

Recursive splitting: try paragraph breaks first, then lines, then sentences,
then words, so chunks end at natural boundaries. Chunks never cross a page or
heading, which keeps each citation exact.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from rag.loaders import Section

SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]
MIN_CHUNK_CHARS = 40


@dataclass
class Chunk:
    index: int
    text: str
    page: int | None
    heading: str | None


def _split(text: str, size: int, separators: list[str]) -> list[str]:
    """Break text into pieces no longer than `size`, preferring earlier separators."""
    if len(text) <= size:
        return [text]
    for i, sep in enumerate(separators):
        if sep in text:
            parts = text.split(sep)
            pieces = []
            for j, part in enumerate(parts):
                piece = part + (sep if j < len(parts) - 1 else "")
                if len(piece) > size:
                    pieces.extend(_split(piece, size, separators[i + 1:]))
                elif piece:
                    pieces.append(piece)
            return pieces
    return [text[k:k + size] for k in range(0, len(text), size)]  # no separator at all


def _merge(pieces: list[str], size: int, overlap: int) -> list[str]:
    """Greedily pack pieces up to `size`, carrying ~`overlap` chars into the next chunk."""
    chunks, current = [], ""
    for piece in pieces:
        if current and len(current) + len(piece) > size:
            chunks.append(current.strip())
            tail = current[-overlap:] if overlap else ""
            # start the overlap at a word boundary
            tail = tail[tail.find(" ") + 1:] if " " in tail else tail
            current = tail
        current += piece
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_sections(sections: list[Section], size: int = 800, overlap: int = 150) -> list[Chunk]:
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")
    chunks: list[Chunk] = []
    for section in sections:
        text = re.sub(r"[ \t]+", " ", section.text).strip()
        if not text:
            continue
        for piece in _merge(_split(text, size, SEPARATORS), size, overlap):
            if len(piece) >= MIN_CHUNK_CHARS or not chunks or chunks[-1].page != section.page:
                chunks.append(Chunk(len(chunks), piece, section.page, section.heading))
            else:  # tiny leftover: attach to the previous chunk from the same page
                chunks[-1].text += "\n" + piece
    return chunks


def embedding_text(title: str, chunk: Chunk) -> str:
    """What gets embedded: the document and heading give a short chunk its context."""
    context = " › ".join(p for p in (title, chunk.heading) if p)
    return f"{context}\n{chunk.text}" if context else chunk.text
