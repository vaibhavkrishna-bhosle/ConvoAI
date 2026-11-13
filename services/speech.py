"""Local speech-to-text with Whisper (faster-whisper / CTranslate2).

Audio recorded in the browser (WebM/Opus, or WAV/OGG/MP3/M4A) is decoded with PyAV
and transcribed on this computer: nothing is sent to an online service.

Default: the "small" model on the CPU with int8 weights. The GPU is left to Ollama,
because a 6 GB laptop GPU can't hold qwen2.5:7b and Whisper together without pushing
the chat model partly onto the CPU (see the benchmark in PLAN/README).
"""
from __future__ import annotations

import io
import threading
import time
from pathlib import Path

MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_SECONDS = 90
NO_SPEECH_PROB = 0.6   # drop segments Whisper itself thinks are not speech


class SpeechError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


class WhisperTranscriber:
    def __init__(self, model: str, device: str, compute_type: str, download_root: Path):
        self.model_name, self.device, self.compute_type = model, device, compute_type
        self.download_root = download_root
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type,
                                       download_root=str(self.download_root))
        return self._model

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def warm_up(self) -> None:
        with self._lock:
            self._load()

    def transcribe(self, audio: bytes, language: str | None = "en", hint: str | None = None) -> dict:
        started = time.perf_counter()
        with self._lock:
            model = self._load()
            loaded_ms = int((time.perf_counter() - started) * 1000)
            try:
                segments, info = model.transcribe(
                    io.BytesIO(audio), language=language or None, beam_size=1, vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500}, condition_on_previous_text=False,
                    initial_prompt=hint, without_timestamps=True)
                if info.duration > MAX_SECONDS:
                    raise SpeechError(f"Recordings are limited to {MAX_SECONDS} seconds.", 413)
                kept = [s.text.strip() for s in segments if s.no_speech_prob < NO_SPEECH_PROB]
            except SpeechError:
                raise
            except Exception as exc:  # PyAV decode errors, corrupt uploads
                raise SpeechError(f"Couldn't read the recording: {exc}", 400) from exc
        text = " ".join(t for t in kept if t).strip()
        return {"text": text, "language": info.language, "duration_s": round(info.duration, 2),
                "ms": int((time.perf_counter() - started) * 1000), "load_ms": loaded_ms,
                "model": self.model_name, "device": self.device}


class FakeTranscriber:
    """Test double: returns a fixed question; empty audio counts as silence."""

    model_name, device, loaded = "fake", "cpu", True

    def warm_up(self):
        pass

    def transcribe(self, audio, language="en", hint=None):
        if len(audio) > MAX_AUDIO_BYTES:
            raise SpeechError("too large", 413)
        text = "" if audio.strip(b"\0") == b"" else "How many casual leaves do I get per year?"
        return {"text": text, "language": "en", "duration_s": 2.0, "ms": 1, "load_ms": 0,
                "model": "fake", "device": "cpu"}


_instances: dict[tuple, object] = {}
_instances_lock = threading.Lock()


def get_transcriber(app):
    if app.config.get("SPEECH") == "fake":
        return FakeTranscriber()
    from models import database as db

    s = db.get_settings()
    key = (s.get("whisper_model", "small"), s.get("whisper_device", "cpu"))
    with _instances_lock:
        if key not in _instances:
            device = key[1]
            compute = "float16" if device == "cuda" else "int8"
            _instances[key] = WhisperTranscriber(key[0], device, compute, Path(app.config["MODEL_DIR"]) / "whisper")
        return _instances[key]


def vocabulary_hint(app) -> str:
    """Bias recognition toward the company's own words (document titles, collection names)."""
    from models import database as db

    words = [c["name"] for c in db.list_collections()]
    words += [d["title"] for d in db.list_documents() if d["status"] == "ready"][:15]
    return ("Questions to ConvoAI, a company assistant, about: " + ", ".join(words) + ".")[:600]
