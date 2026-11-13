"""Editable settings: type, range and help text for each key. Drives both the Settings
page and server-side validation, so a bad value can never reach the pipeline."""
from __future__ import annotations

SCHEMA: list[dict] = [
    # --- Answering
    {"key": "llm_model", "group": "Answering", "label": "Chat model", "type": "ollama_model",
     "help": "Ollama model that writes answers. Bigger models answer better but more slowly."},
    {"key": "llm_fallback_model", "group": "Answering", "label": "Fallback model", "type": "ollama_model",
     "help": "Used automatically if the chat model isn't installed."},
    {"key": "temperature", "group": "Answering", "label": "Temperature", "type": "float", "min": 0, "max": 1, "step": 0.05,
     "help": "0 = most factual and repeatable; higher = more varied wording. Keep it low for policy answers."},
    {"key": "max_answer_tokens", "group": "Answering", "label": "Max answer length (tokens)", "type": "int",
     "min": 100, "max": 2000, "step": 50, "help": "About 0.75 words per token."},
    {"key": "context_window", "group": "Answering", "label": "Context window (tokens)", "type": "choice",
     "choices": ["2048", "3072", "4096", "6144", "8192"],
     "help": "Room for sources + history + answer. 4096 fits a 6 GB GPU; larger values may push the model onto the CPU."},

    # --- Retrieval
    {"key": "top_k", "group": "Retrieval", "label": "Sources per answer", "type": "int", "min": 1, "max": 10, "step": 1,
     "help": "How many document chunks the model reads before answering."},
    {"key": "neighbor_chunks", "group": "Retrieval", "label": "Include neighbouring chunks", "type": "choice",
     "choices": ["0", "1"],
     "help": "1 = also give the model the chunk before and after the top two matches, which helps when a fact "
             "spans sections. 0 = top matches only (recommended: tested no better on the evaluation set)."},
    {"key": "relevance_threshold", "group": "Retrieval", "label": "Relevance threshold", "type": "float",
     "min": 0, "max": 1, "step": 0.005,
     "help": "Below this similarity the assistant says it couldn't find the answer. Tuned with `python -m rag.evaluate --apply`."},
    {"key": "relevance_floor", "group": "Retrieval", "label": "Relevance floor (with keyword agreement)", "type": "float",
     "min": 0, "max": 1, "step": 0.005,
     "help": "Questions scoring between this and the relevance threshold are still answered when the keyword "
             "search finds the same passage (helps short follow-ups). Must not exceed the relevance threshold."},
    {"key": "intent_threshold", "group": "Retrieval", "label": "Small-talk confidence", "type": "float",
     "min": 0.05, "max": 0.95, "step": 0.05,
     "help": "Minimum classifier confidence for an instant canned reply; below it, the question goes to the documents. Retraining re-tunes it."},

    # --- Documents
    {"key": "embed_model", "group": "Documents", "label": "Embedding model", "type": "ollama_model", "reindex": True,
     "help": "Turns text into vectors for search. Changing it requires re-indexing every document."},
    {"key": "chunk_size", "group": "Documents", "label": "Chunk size (characters)", "type": "int",
     "min": 300, "max": 2000, "step": 50, "reindex": True,
     "help": "Applies to documents indexed from now on; re-index to apply to existing ones."},
    {"key": "chunk_overlap", "group": "Documents", "label": "Chunk overlap (characters)", "type": "int",
     "min": 0, "max": 500, "step": 10, "reindex": True, "help": "Must be smaller than the chunk size."},

    # --- Voice
    {"key": "whisper_model", "group": "Voice", "label": "Whisper model", "type": "choice",
     "choices": ["tiny", "base", "small", "medium"],
     "help": "base ≈ 0.6 s, small ≈ 1.7 s per question on this CPU (small is more accurate). Larger models download on first use."},
    {"key": "whisper_device", "group": "Voice", "label": "Whisper runs on", "type": "choice", "choices": ["cpu", "cuda"],
     "help": "cuda needs NVIDIA cuBLAS/cuDNN 12 and competes with the chat model for GPU memory."},
    {"key": "speech_language", "group": "Voice", "label": "Spoken language", "type": "choice",
     "choices": ["en", "hi", "kn", "auto"], "help": "en = English, hi = Hindi, kn = Kannada, auto = detect."},
]

BY_KEY = {s["key"]: s for s in SCHEMA}


class SettingsError(ValueError):
    pass


def validate(values: dict, installed_models: list[str] | None = None, current: dict | None = None) -> dict[str, str]:
    """Return cleaned string values, or raise SettingsError naming the first bad field."""
    clean: dict[str, str] = {}
    for key, raw in values.items():
        spec = BY_KEY.get(key)
        if spec is None:
            raise SettingsError(f"Unknown setting: {key}")
        label = spec["label"]
        if spec["type"] in ("int", "float"):
            try:
                num = int(raw) if spec["type"] == "int" else float(raw)
            except (TypeError, ValueError):
                raise SettingsError(f"{label} must be a number.")
            if not spec["min"] <= num <= spec["max"]:
                raise SettingsError(f"{label} must be between {spec['min']} and {spec['max']}.")
            clean[key] = str(num)
        elif spec["type"] == "choice":
            if str(raw) not in spec["choices"]:
                raise SettingsError(f"{label} must be one of: {', '.join(spec['choices'])}.")
            clean[key] = str(raw)
        elif spec["type"] == "ollama_model":
            name = str(raw or "").strip()
            if not name:
                raise SettingsError(f"{label} is required.")
            if installed_models is not None and name not in installed_models and f"{name}:latest" not in installed_models:
                raise SettingsError(f"{label}: '{name}' isn't installed in Ollama. Run: ollama pull {name}")
            clean[key] = name

    merged = {**(current or {}), **clean}
    if int(merged.get("chunk_overlap", 0)) >= int(merged.get("chunk_size", 800)):
        raise SettingsError("Chunk overlap must be smaller than the chunk size.")
    if float(merged.get("relevance_floor", 0)) > float(merged.get("relevance_threshold", 1)):
        raise SettingsError("The relevance floor can't be higher than the relevance threshold.")
    return clean
