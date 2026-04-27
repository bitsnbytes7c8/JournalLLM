from __future__ import annotations

from uuid import UUID

from intelligence.entry_pipeline import enrich_and_index_entry
from intelligence.ollama_impl import (
    OllamaEmbeddingClient,
    OllamaImageClient,
    OllamaTextClient,
)
from storage import StorageManager, VectorManager


def process_entry_metadata(entry_id: UUID) -> None:
    """
    Background job: enrich entry with image description(s), mood, and embedding vector;
    updates `mood` + `vector_status` in SQLite, and upserts into ChromaDB via VectorManager.
    """
    sm = StorageManager()
    vm = VectorManager()
    text_llm = OllamaTextClient()
    image_llm = OllamaImageClient()
    embed_client = OllamaEmbeddingClient()

    enrich_and_index_entry(
        entry_id,
        sm=sm,
        vm=vm,
        text_llm=text_llm,
        image_llm=image_llm,
        embed_client=embed_client,
        only_fill_missing=False,
        vector_status_success="ready",
    )
