from __future__ import annotations

from uuid import UUID

from intelligence.ollama_impl import (
    OllamaEmbeddingClient,
    OllamaImageClient,
    OllamaTextClient,
)
from storage import ImageType, StorageManager


def process_entry_metadata(entry_id: UUID) -> None:
    """
    Background job: enrich entry with image description(s), mood, and embedding vector;
    updates `mood` + `vector_status` in SQLite and writes embedding JSON under vector_store/.
    """
    sm = StorageManager()
    text_llm = OllamaTextClient()
    image_llm = OllamaImageClient()
    embed_client = OllamaEmbeddingClient()

    try:
        entry = sm.get_entry_by_id(entry_id)
    except KeyError:
        return

    try:
        image_descriptions: list[str] = []
        for img in entry.images:
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

        mood = text_llm.infer_mood(
            title=entry.title,
            content=entry.content,
            image_description="\n".join(image_descriptions) if image_descriptions else None,
        )
        vector = embed_client.embed(combined)
        sm.save_embedding_vector(entry_id, vector)
        sm.update_entry_metadata(entry_id, mood=mood, vector_status="ready")
    except Exception:
        sm.update_entry_metadata(entry_id, vector_status="failed")
