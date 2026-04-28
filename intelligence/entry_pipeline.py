from __future__ import annotations

import logging
from uuid import UUID

from intelligence.interfaces import EmbeddingClient, ImageLLMClient, TextLLMClient
from storage import ImageType, StorageManager, VectorManager

logger = logging.getLogger(__name__)


def enrich_and_index_entry(
    entry_id: UUID,
    *,
    sm: StorageManager,
    vm: VectorManager,
    text_llm: TextLLMClient,
    image_llm: ImageLLMClient,
    embed_client: EmbeddingClient,
    only_fill_missing: bool = False,
    vector_status_success: str = "ready",
) -> None:
    """
    Shared pipeline: optional image descriptions, mood, embedding, Chroma upsert, SQLite metadata.

    - ``only_fill_missing=False`` (default): always re-run image + mood LLMs (API background task).
    - ``only_fill_missing=True``: only describe images missing descriptions; only infer mood if absent
      (full re-index script).
    """
    try:
        entry = sm.get_entry_by_id(entry_id)
    except KeyError:
        return

    try:
        image_descriptions: list[str] = []
        for img in entry.images:
            existing = (img.description or "").strip()
            if only_fill_missing and existing:
                image_descriptions.append(existing)
                continue
            if img.image_type == ImageType.local:
                abs_path = sm.get_absolute_path(img.location)
                desc = image_llm.describe_image(local_path=abs_path)
            else:
                desc = image_llm.describe_image(remote_url=img.location)
            image_descriptions.append(desc)
            sm.update_image_description(img.id, description=desc)

        combined = f"{entry.title}\n\n{entry.content}"
        if image_descriptions:
            combined += "\n\n" + "\n".join(image_descriptions)

        img_ctx = "\n".join(image_descriptions) if image_descriptions else None
        existing_mood = (entry.mood or "").strip()
        if only_fill_missing and existing_mood:
            mood = existing_mood
        else:
            mood = text_llm.infer_mood(
                title=entry.title,
                content=entry.content,
                image_description=img_ctx,
            )
        logger.debug("Mood calculated for %s: %s", entry_id, mood)

        vector = embed_client.embed(combined)
        logger.debug("Embedding calculated for %s: %s", entry_id, vector)
        vm.upsert_entry(
            str(entry_id),
            vector,
            metadata={
                "journal_date": entry.journal_date.isoformat(),
                "tags": "",
            },
            document_text=combined,
        )
        logger.debug("Vector DB updated for %s", entry_id)
        sm.update_entry_metadata(
            entry_id,
            mood=mood,
            vector_status=vector_status_success,
        )
        logger.debug(
            "SQLite vector_status updated for %s: %s", entry_id, vector_status_success
        )
    except Exception:
        sm.update_entry_metadata(entry_id, vector_status="failed")
