from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

class EmbeddingClient(Protocol):
    def embed_text(self, text: str) -> list[float]: ...


class ChatClient(Protocol):
    def generate_text(self, prompt: str, *, temperature: Optional[float] = None) -> str: ...


@dataclass(frozen=True)
class GeminiClient(EmbeddingClient, ChatClient):
    api_key: str
    embedding_model: str = "text-embedding-004"
    chat_model: str = "gemini-1.5-flash"

    def __post_init__(self) -> None:
        # Configure once per process; safe to call multiple times.
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

    def embed_text(self, text: str) -> list[float]:
        """
        Returns an embedding vector for the given text using AI Studio.
        """
        import google.generativeai as genai

        # google-generativeai uses `embed_content` for embeddings.
        # Model name formats can vary by SDK; we keep this centralized.
        res: Any = genai.embed_content(
            model=self._normalize_embedding_model(self.embedding_model),
            content=text,
        )

        # Typically: {"embedding": {"values": [...]}}
        if isinstance(res, dict):
            values = (
                res.get("embedding", {}).get("values")
                if isinstance(res.get("embedding"), dict)
                else res.get("embedding")
            )
            if isinstance(values, list):
                return [float(x) for x in values]

        # Fallback for SDK object responses
        values = getattr(getattr(res, "embedding", None), "values", None)
        if isinstance(values, list):
            return [float(x) for x in values]

        raise RuntimeError("Unexpected embedding response shape from Gemini SDK.")

    def generate_text(self, prompt: str, *, temperature: Optional[float] = None) -> str:
        import google.generativeai as genai

        model = genai.GenerativeModel(self.chat_model)
        generation_config: Optional[Dict[str, Any]] = None
        if temperature is not None:
            generation_config = {"temperature": temperature}

        res: Any = model.generate_content(prompt, generation_config=generation_config)
        text = getattr(res, "text", None)
        if isinstance(text, str):
            return text
        # Fallback: try candidates
        candidates = getattr(res, "candidates", None)
        if candidates:
            try:
                return candidates[0].content.parts[0].text
            except Exception:
                pass
        raise RuntimeError("Unexpected generate_content response shape from Gemini SDK.")

    @staticmethod
    def _normalize_embedding_model(model: str) -> str:
        # Some SDK versions expect "models/<name>"
        if model.startswith("models/"):
            return model
        return f"models/{model}"


@dataclass(frozen=True)
class FakeGeminiClient(EmbeddingClient, ChatClient):
    """
    Deterministic local client for tests/self-checks.
    - `embed_text` maps text into a small vector.
    - `generate_text` returns a stable JSON-like response.
    """

    def embed_text(self, text: str) -> list[float]:
        # Simple stable embedding: 8-dim hash features.
        vec = [0.0] * 8
        for i, ch in enumerate(text):
            vec[i % 8] += (ord(ch) % 31) / 31.0
        # Normalize roughly
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    def generate_text(self, prompt: str, *, temperature: Optional[float] = None) -> str:
        # Return strict JSON to exercise parsing path in tests.
        return (
            '{'
            '"status":"ok",'
            '"shift_reason":"fake_reason",'
            '"new_perspective":"fake_perspective",'
            '"evidence_anchor":["fake_quote"]'
            '}'
        )

