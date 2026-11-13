"""Phase 6 tests: speech status/transcribe API (fake transcriber) and, when faster-whisper and a
cached model are available, a real local transcription of synthesized speech."""
import io
import math
import struct
import wave
from pathlib import Path

import pytest

from app import create_app
from config import TestConfig

ROOT = Path(__file__).resolve().parents[1]


def _app(tmp_path, speech="fake"):
    class Cfg(TestConfig):
        DATA_DIR = tmp_path
        DB_PATH = tmp_path / "test.db"
        UPLOAD_DIR = tmp_path / "uploads"
        CHROMA_DIR = tmp_path / "chroma"
        MODEL_DIR = tmp_path / "models"
        ADMIN_PASSWORD = "test-admin-pw"
        LOGIN_REQUIRED = False
        SPEECH = speech

    return create_app(Cfg)


def _wav(seconds=1.0, freq=0.0) -> bytes:
    """16 kHz mono WAV: silence (freq=0) or a tone."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
        frames = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * freq * i / 16000)) if freq else 0)
                          for i in range(int(16000 * seconds)))
        w.writeframes(frames)
    return buf.getvalue()


@pytest.fixture()
def client(tmp_path):
    return _app(tmp_path).test_client()


def test_status(client):
    s = client.get("/api/speech/status").get_json()
    assert s["available"] is True and s["model"] == "fake"


def test_transcribe_returns_text(client):
    r = client.post("/api/speech/transcribe", data={"audio": (io.BytesIO(b"\x01" * 2000), "q.webm")},
                    content_type="multipart/form-data")
    assert r.status_code == 200 and r.get_json()["text"].startswith("How many casual leaves")


def test_transcribe_rejects_bad_input(client):
    assert client.post("/api/speech/transcribe", data={}, content_type="multipart/form-data").status_code == 400
    tiny = {"audio": (io.BytesIO(b"\x01" * 10), "q.webm")}
    assert client.post("/api/speech/transcribe", data=tiny, content_type="multipart/form-data").status_code == 400
    silent = {"audio": (io.BytesIO(b"\0" * 5000), "q.webm")}
    r = client.post("/api/speech/transcribe", data=silent, content_type="multipart/form-data")
    assert r.status_code == 422 and "didn't catch" in r.get_json()["error"]


# --------------------------------------------------------------------------- real Whisper (optional)
WHISPER_CACHE = ROOT / "data" / "models" / "whisper"
needs_whisper = pytest.mark.skipif(
    not any(WHISPER_CACHE.glob("models--Systran--faster-whisper-base")),
    reason="faster-whisper base model not downloaded (data/models/whisper)")


@needs_whisper
def test_real_whisper_ignores_silence_and_tones():
    from services.speech import WhisperTranscriber
    t = WhisperTranscriber("base", "cpu", "int8", WHISPER_CACHE)
    assert t.transcribe(_wav(2.0))["text"] == ""            # silence: no invented "Thank you."
    assert t.transcribe(_wav(2.0, 440.0))["text"] == ""     # a beep is not speech


@needs_whisper
def test_real_whisper_transcribes_speech(tmp_path):
    """Synthesize a question with the Windows speech engine, then transcribe it locally."""
    import subprocess
    wav = tmp_path / "q.wav"
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.SetOutputToWaveFile('{wav}'); $s.Speak('How do I reset my password?'); $s.Dispose()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=60, capture_output=True)
    except (FileNotFoundError, subprocess.SubprocessError):
        pytest.skip("Windows speech synthesis not available")
    from services.speech import WhisperTranscriber
    out = WhisperTranscriber("base", "cpu", "int8", WHISPER_CACHE).transcribe(wav.read_bytes())
    assert "reset my password" in out["text"].lower()
