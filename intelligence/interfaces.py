from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class TextLLMClient(ABC):
    """Abstract client for short text generation (e.g., mood inference)."""

    @abstractmethod
    def infer_mood(
        self,
        *,
        title: str,
        content: str,
        image_description: Optional[str] = None,
    ) -> str:
        """Return a concise mood label or phrase."""
        ...


class ImageLLMClient(ABC):
    """Abstract client for image understanding."""

    @abstractmethod
    def describe_image(
        self,
        *,
        local_path: Optional[Path] = None,
        remote_url: Optional[str] = None,
    ) -> str:
        """
        Produce a textual description of the image.
        Exactly one of local_path or remote_url must be provided.
        """
        ...


class EmbeddingClient(ABC):
    """Abstract client for text embeddings."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Return an embedding vector for the given text."""
        ...
