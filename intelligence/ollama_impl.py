from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

import ollama

from .interfaces import EmbeddingClient, ImageLLMClient, TextLLMClient


def _client():
    """Optional custom host via OLLAMA_HOST (e.g. http://127.0.0.1:11434)."""
    host = os.environ.get("OLLAMA_HOST")
    return ollama.Client(host=host) if host else ollama.Client()


class OllamaTextClient(TextLLMClient):
    """Uses model `llama3.2` for short mood inference."""

    def __init__(self, model: str = "llama3.2"):
        self._model = model
        self._client = _client()

    def infer_mood(
        self,
        *,
        title: str,
        content: str,
        image_description: Optional[str] = None,
    ) -> str:
        parts = [
            "Analyze this journal entry.",
            (
                "Return only a single word representing the primary emotion "
                "(e.g., Happy, Anxious, Reflective) followed by a score from 1-10."
            ),
            "",
            f"Title: {title}",
            f"Content:\n{content}",
        ]
        if image_description:
            parts.extend(["", f"Image context:\n{image_description}"])
        prompt = "\n".join(parts)
        resp = self._client.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        if hasattr(resp, "message") and resp.message is not None:
            text = (getattr(resp.message, "content", None) or "").strip()
        elif isinstance(resp, dict):
            msg = resp.get("message") or {}
            text = (msg.get("content") or "").strip()
        return text[:200] if text else "neutral"


class OllamaImageClient(ImageLLMClient):
    """Uses vision model `moondream` for image descriptions."""

    def __init__(self, model: str = "moondream"):
        self._model = model
        self._client = _client()

    def describe_image(
        self,
        *,
        local_path: Optional[Path] = None,
        remote_url: Optional[str] = None,
    ) -> str:
        if bool(local_path) == bool(remote_url):
            raise ValueError("Exactly one of local_path or remote_url must be set")
        images: List[str]
        if local_path is not None:
            p = local_path.expanduser().resolve()
            if not p.is_file():
                raise FileNotFoundError(str(p))
            images = [str(p)]
        else:
            images = [remote_url or ""]
        prompt = (
            "Describe this image in two sentences, focusing on the setting, objects, "
            "and overall atmosphere to provide context for a personal journal."
        )
        resp = self._client.chat(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": images,
                },
            ],
        )
        text = ""
        if hasattr(resp, "message") and resp.message is not None:
            text = (getattr(resp.message, "content", None) or "").strip()
        elif isinstance(resp, dict):
            msg = resp.get("message") or {}
            text = (msg.get("content") or "").strip()
        return text or "(no description)"


class OllamaEmbeddingClient(EmbeddingClient):
    """Uses `nomic-embed-text` for embeddings."""

    def __init__(self, model: str = "nomic-embed-text"):
        self._model = model
        self._client = _client()

    def embed(self, text: str) -> List[float]:
        resp = self._client.embed(model=self._model, input=text)
        embs = getattr(resp, "embeddings", None)
        if embs is None and isinstance(resp, dict):
            embs = resp.get("embeddings")
        if embs:
            return list(embs[0])
        emb = getattr(resp, "embedding", None)
        if emb is None and isinstance(resp, dict):
            emb = resp.get("embedding")
        if emb is not None:
            return list(emb)
        raise RuntimeError("Unexpected embed response: missing embeddings")
