"""Text preprocessing pipeline (synopsis §4.2).

normalise → expand contractions/slang → tokenize → stop-word removal → lemmatize

Short chat messages depend on words that generic stop-word lists throw away
("who are you", "how are you", "no"), so question words, pronouns and
negations are kept.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer

_NLTK_PACKAGES = {
    "tokenizers/punkt_tab": "punkt_tab",
    "corpora/stopwords": "stopwords",
    "corpora/wordnet": "wordnet",
    "corpora/omw-1.4": "omw-1.4",
}


def ensure_nltk_data() -> None:
    """Download any missing NLTK resources (first run only)."""
    for path, package in _NLTK_PACKAGES.items():
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(package, quiet=True)


ensure_nltk_data()

CONTRACTIONS = {
    "won't": "will not", "can't": "can not", "cannot": "can not", "shan't": "shall not",
    "let's": "let us", "what's": "what is", "who's": "who is", "where's": "where is",
    "how's": "how is", "that's": "that is", "it's": "it is", "there's": "there is",
    "i'm": "i am", "y'all": "you all",
}
SUFFIXES = [("n't", " not"), ("'re", " are"), ("'ll", " will"), ("'ve", " have"), ("'d", " would"), ("'s", "")]

# Chat shorthand → standard words
SLANG = {
    "u": "you", "ur": "your", "r": "are", "ya": "you", "yo": "hey",
    "thx": "thanks", "thnx": "thanks", "thanx": "thanks", "tnx": "thanks", "ty": "thank you",
    "pls": "please", "plz": "please", "plse": "please",
    "bday": "birthday", "wfh": "work from home", "pto": "paid time off",
    "pwd": "password", "msg": "message", "info": "information",
    "hlo": "hello", "helo": "hello", "hii": "hi", "hiii": "hi", "heyy": "hey",
    "gn": "good night", "gm": "good morning", "brb": "be right back", "cya": "see you",
    "lol": "haha", "lmao": "haha", "rofl": "haha",
    "ok": "okay", "k": "okay", "kk": "okay", "okk": "okay", "yep": "yes", "yup": "yes", "ya'll": "you all",
    "nope": "no", "nah": "no",
}

KEEP = {
    "who", "whom", "what", "when", "where", "why", "how", "which",
    "i", "me", "my", "you", "your", "yours", "yourself", "we", "our",
    "not", "no", "nor", "can", "do", "does", "are", "is", "am", "should", "will",
    "up", "down", "off", "on", "again", "more", "very", "here", "now",
}
STOP_WORDS = frozenset(stopwords.words("english")) - KEEP

_lemmatizer = WordNetLemmatizer()
_NON_WORD = re.compile(r"[^a-z0-9\s]")
_SPACES = re.compile(r"\s+")
_REPEATS = re.compile(r"(.)\1{2,}")  # "hiiii" -> "hii", "thanksss" -> "thankss"


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().replace("’", "'").replace("`", "'")
    for word, full in CONTRACTIONS.items():
        text = text.replace(word, full)
    for suffix, full in SUFFIXES:
        text = text.replace(suffix, full)
    text = _REPEATS.sub(r"\1\1", text)
    text = _NON_WORD.sub(" ", text)
    words = [SLANG.get(w, w) for w in text.split()]
    return _SPACES.sub(" ", " ".join(words)).strip()


def tokenize(text: str) -> list[str]:
    return nltk.word_tokenize(text)


def remove_stop_words(tokens: list[str]) -> list[str]:
    kept = [t for t in tokens if t not in STOP_WORDS]
    return kept or tokens  # never return an empty message


@lru_cache(maxsize=20_000)
def lemmatize(token: str) -> str:
    verb = _lemmatizer.lemmatize(token, wordnet.VERB)
    return verb if verb != token else _lemmatizer.lemmatize(token, wordnet.NOUN)


def preprocess_tokens(text: str) -> list[str]:
    return [lemmatize(t) for t in remove_stop_words(tokenize(normalise(text)))]


def preprocess(text: str) -> str:
    """Full pipeline, returned as a space-joined string (input to TF-IDF)."""
    return " ".join(preprocess_tokens(text))


def explain(text: str) -> dict:
    """Every pipeline stage, for the UI's 'show NLP steps' view and the report."""
    norm = normalise(text)
    tokens = tokenize(norm)
    filtered = remove_stop_words(tokens)
    lemmas = [lemmatize(t) for t in filtered]
    return {
        "input": text,
        "normalised": norm,
        "tokens": tokens,
        "without_stop_words": filtered,
        "lemmas": lemmas,
    }
