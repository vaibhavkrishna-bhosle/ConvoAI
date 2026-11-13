"""Chat model access through Ollama: streaming answers and short completions.

If the configured model isn't installed, the fallback model (llama3.2:3b) is used.
`EchoLLM` stands in for tests.
"""
from __future__ import annotations

from typing import Iterator

KEEP_ALIVE = "30m"


class LLMError(Exception):
    pass


class OllamaLLM:
    def __init__(self, host: str, model: str, fallback: str | None = None, temperature: float = 0.2,
                 num_ctx: int = 4096, max_tokens: int = 700):
        import ollama

        self._client = ollama.Client(host=host, timeout=180)
        self.model, self.fallback = model, fallback
        self.temperature, self.num_ctx, self.max_tokens = temperature, num_ctx, max_tokens

    def _options(self, **overrides) -> dict:
        return {"temperature": self.temperature, "num_ctx": self.num_ctx, "num_predict": self.max_tokens, **overrides}

    def _call(self, model: str, messages: list[dict], stream: bool, options: dict):
        return self._client.chat(model=model, messages=messages, stream=stream, options=options, keep_alive=KEEP_ALIVE)

    def _with_fallback(self, messages, stream, options):
        import ollama

        try:
            return self._call(self.model, messages, stream, options), self.model
        except ollama.ResponseError as exc:
            if exc.status_code == 404 and self.fallback and self.fallback != self.model:
                try:
                    return self._call(self.fallback, messages, stream, options), self.fallback
                except ollama.ResponseError as exc2:
                    raise LLMError(f"Neither {self.model} nor {self.fallback} is installed in Ollama.") from exc2
            raise LLMError(f"Ollama error: {exc.error}") from exc
        except Exception as exc:
            if "connect" in type(exc).__name__.lower() or isinstance(exc, (ConnectionError, OSError)):
                raise LLMError("Cannot reach Ollama. Is it running? (ollama serve)") from exc
            raise

    def stream(self, messages: list[dict]) -> Iterator[str]:
        """Yield answer text pieces as they're generated."""
        response, self.used_model = self._with_fallback(messages, True, self._options())
        try:
            for part in response:
                token = part.message.content if part.message else ""
                if token:
                    yield token
        except Exception as exc:
            raise LLMError(f"The model stopped unexpectedly: {exc}") from exc

    def complete(self, messages: list[dict], max_tokens: int = 80) -> str:
        """Short, deterministic completion (used for rewriting follow-up questions).

        Uses the same model *and the same num_ctx* as answers: Ollama reloads a model whenever
        num_ctx changes, and loading a second model evicts the first from a 6 GB GPU (measured:
        5–80 s stalls)."""
        response, _ = self._with_fallback(messages, False, self._options(temperature=0, num_predict=max_tokens))
        return response.message.content.strip()

    def warm_up(self) -> None:
        """Load the model into GPU memory with the answer-time options, so the first question isn't slow."""
        try:
            self._client.generate(model=self.model, prompt="", keep_alive=KEEP_ALIVE,
                                  options={"num_ctx": self.num_ctx})
        except Exception:
            pass


class EchoLLM:
    """Test double: answers with the first sentence of source [1], cited."""

    model = used_model = "echo-test"

    def stream(self, messages):
        content = messages[-1]["content"]
        first = content.split("[1]", 1)[1].split("\n", 2)[-1] if "[1]" in content else "No sources."
        answer = first.split(". ")[0].strip().rstrip(".") + ". [1]"
        for word in answer.split(" "):
            yield word + " "

    def complete(self, messages, max_tokens=80):
        return messages[-1]["content"].rsplit("Latest message:", 1)[-1].split("\n")[0].strip()

    def warm_up(self):
        pass


def get_llm(app):
    if app.config.get("LLM") == "echo":
        return EchoLLM()
    from models import database as db

    s = db.get_settings()
    return OllamaLLM(app.config["OLLAMA_HOST"], s.get("llm_model", "qwen2.5:7b-instruct"),
                     fallback=s.get("llm_fallback_model"), temperature=float(s.get("temperature", 0.2)),
                     num_ctx=int(s.get("context_window", 4096)), max_tokens=int(s.get("max_answer_tokens", 700)))
