from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb

logger = logging.getLogger(__name__)


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
            metadata={"description": "Journal entry embeddings", "hnsw:space": "cosine"},
        )

    def wipe_journal_collection(self) -> None:
        """Delete and recreate the ``journal_entries`` collection (full re-index)."""
        try:
            self._client.delete_collection(self.COLLECTION_NAME)
        except Exception:
            pass
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
        max_distance: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return the most relevant entry IDs with Chroma distances (lower is closer for L2).
        If ``max_distance`` is set, drop hits whose distance is strictly greater than that
        (e.g. ``0.5`` for a similarity-style cutoff, depending on Chroma's metric).
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

        raw = []
        for i, eid in enumerate(row_ids):
            dist = row_dists[i] if i < len(row_dists) else None
            raw.append({"id": eid, "distance": dist})
        logger.debug("Chroma raw results (pre-filter): %s", raw)

        out: List[Dict[str, Any]] = []
        for i, eid in enumerate(row_ids):
            dist = row_dists[i] if i < len(row_dists) else None
            if max_distance is not None and dist is not None and dist > max_distance:
                continue
            out.append({"id": eid, "distance": dist})
        logger.debug("Chroma query_semantic results: %s", out)
        return out
