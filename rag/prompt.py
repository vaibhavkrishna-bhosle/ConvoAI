"""Prompts for grounded answering and follow-up rewriting."""
from __future__ import annotations

import re
from datetime import date

from rag.store import Hit

SYSTEM_PROMPT = """You are ConvoAI, a helpful assistant for employees. Today is {today}.

Answer the user's question using ONLY the numbered sources provided. Follow these rules:
1. Cite every fact with its source number in square brackets right after it, like [1] or [2][3].
2. If the sources do not contain the answer, say "I couldn't find that in the documents you have access to." and suggest who to ask if a source names a contact. Never guess or use outside knowledge.
3. Be concise and direct. Start with the answer itself. Use short bullet points or numbered steps when there are several items or steps.
4. If the answer depends on conditions (approval levels, grades, cities, plans, durations), briefly list each case instead of giving only the largest or smallest value.
5. Quote numbers, amounts, dates and names exactly as they appear in the sources.
6. Do not mention "the sources" or "the context"; just answer naturally with citations."""
# Phase 9 tried stricter rules (check category definitions, list every case, never compute totals):
# no change on the 41-question answer evaluation (92.7% either way), so the simpler prompt stays.

REWRITE_PROMPT = """Rewrite the user's latest message as a single standalone question that can be understood without the conversation. Only resolve what the message refers to (for example "it", "that", "and sick leave?"). Do NOT add any facts, numbers or answers from the conversation, and do not turn it into a yes/no question. Output only the rewritten question, nothing else.

Example: after a question about connecting to the VPN from a laptop, "what about on my phone?" becomes "How do I connect to the VPN on my phone?"

Conversation:
{history}

Latest message: {question}
Standalone question:"""

FOLLOW_UP_HINTS = re.compile(
    r"\b(it|its|that|this|those|these|they|them|their|there|same|what about|how about|and for|also|"
    r"else|more|another|which one|the other|then)\b", re.I)


def source_label(hit: Hit) -> str:
    parts = [hit.title]
    if hit.page:
        parts.append(f"p.{hit.page}")
    if hit.heading and hit.heading != hit.title:
        parts.append(hit.heading)
    return " · ".join(parts)


def build_messages(question: str, hits: list[Hit], history: list[dict] | None = None) -> list[dict]:
    sources = "\n\n".join(f"[{i}] {source_label(h)}\n{h.text}" for i, h in enumerate(hits, start=1))
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(today=date.today().strftime("%d %B %Y"))}]
    for turn in (history or [])[-4:]:  # last two exchanges, for natural follow-ups
        messages.append({"role": "assistant" if turn["role"] == "bot" else "user",
                         "content": strip_citations(turn["content"])[:600]})  # keeps the prompt within 4096 tokens
    messages.append({"role": "user", "content": f"Sources:\n\n{sources}\n\nQuestion: {question}"})
    return messages


def needs_rewrite(question: str, history: list[dict]) -> bool:
    """Only follow-ups need rewriting: short messages or ones that point back ('what about sick leave?')."""
    if not history:
        return False
    return len(question.split()) <= 6 or bool(FOLLOW_UP_HINTS.search(question))


def rewrite_messages(question: str, history: list[dict]) -> list[dict]:
    lines = [f"{'Assistant' if t['role'] == 'bot' else 'User'}: {strip_citations(t['content'])[:600]}"
             for t in history[-4:]]
    return [{"role": "user", "content": REWRITE_PROMPT.format(history="\n".join(lines), question=question)}]


_CITATION = re.compile(r"\[(\d{1,2})\]")


def strip_citations(text: str) -> str:
    return re.sub(r"\s*\[\d{1,2}\]", "", text)


def cited_numbers(answer: str, n_sources: int) -> list[int]:
    """Source numbers the answer actually cites, in first-use order (ignores out-of-range numbers)."""
    seen = []
    for m in _CITATION.finditer(answer):
        n = int(m.group(1))
        if 1 <= n <= n_sources and n not in seen:
            seen.append(n)
    return seen


def remove_invalid_citations(answer: str, n_sources: int) -> str:
    return _CITATION.sub(lambda m: m.group(0) if 1 <= int(m.group(1)) <= n_sources else "", answer)
