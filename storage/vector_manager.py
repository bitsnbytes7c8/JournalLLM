from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb


class VectorManager:
    """
    ChromaDB persistence under ~/.local_journal/vector_store (created if missing).
    """

    COLLECTION_NAME = "journal_entries"

    def __init__(self, vector_store_path: Optional[Path] = None) -> None:
        base = (
            vector_store_path
            if vector_store_path is not None
            else (Path.home() / ".local_journal" / "vector_store")
        )
        self._path = base.expanduser().resolve()
        self._path.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(self._path))
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Journal entry embeddings"},
        )

    @property
    def store_path(self) -> Path:
        return self._path

    def upsert_entry(
        self,
        entry_id: str,
        vector: List[float],
        metadata: dict,
        document_text: str,
    ) -> None:
        """Index or update one entry; Chroma ID is the entry UUID string."""
        md: Dict[str, Any] = dict(metadata)
        md.setdefault("tags", "")
        self._collection.upsert(
            ids=[entry_id],
            embeddings=[vector],
            metadatas=[md],
            documents=[document_text],
        )

    def delete_entry(self, entry_id: str) -> None:
        """Remove an entry from the vector index by ID."""
        self._collection.delete(ids=[entry_id])

    def query_semantic(
        self,
        query_vector: List[float],
        n_results: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return the most relevant entry IDs with Chroma distances (lower is closer for L2).
        """
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": n_results,
        }
        if filter_metadata:
            kwargs["where"] = filter_metadata

        result = self._collection.query(**kwargs)
        ids_nested = result.get("ids") or []
        dist_nested = result.get("distances") or []
        row_ids = ids_nested[0] if ids_nested else []
        row_dists = dist_nested[0] if dist_nested else []

        out: List[Dict[str, Any]] = []
        for i, eid in enumerate(row_ids):
            dist = row_dists[i] if i < len(row_dists) else None
            out.append({"id": eid, "distance": dist})
        return out
