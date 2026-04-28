from __future__ import annotations

import json
import re
from typing import Any, Dict, List
from uuid import UUID

from intelligence.ollama_impl import OllamaEmbeddingClient, _client
from storage import StorageManager, VectorManager

INTENT_SYSTEM = """You are a search planning assistant. Given the chat history and the current user message, output ONLY a single JSON object (no markdown fences, no other text) with this exact shape:
{"standalone_query": "<a self-contained search query for the user's information need>", "filters": null}
The "filters" field must always be null. Use double quotes for JSON strings."""


def _extract_message_text(resp: Any) -> str:
    if hasattr(resp, "message") and resp.message is not None:
        return (getattr(resp.message, "content", None) or "")
    if isinstance(resp, dict):
        msg = resp.get("message") or {}
        return (msg.get("content") or "")
    return ""


def _parse_json_object(text: str) -> Dict[str, Any]:
    t = text.strip()
    m = re.search(r"\{[\s\S]*\}", t)
    if m:
        t = m.group(0)
    return json.loads(t)


def _format_history_block(history: List[Dict[str, str]]) -> str:
    if not history:
        return "(none)"
    return "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history
    )


class InsightsEngine:
    """RAG: intent (JSON) -> vector search -> grounded answer with Llama 3.2."""

    def __init__(self, chat_model: str = "llama3.2") -> None:
        self._chat_model = chat_model
        self._client = _client()
        self._embedder = OllamaEmbeddingClient()

    def get_search_intent(
        self,
        current_question: str,
        history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Ask Llama 3.2 for ``{"standalone_query": str, "filters": null}``.
        """
        history_str = _format_history_block(history)
        user_payload = (
            f"### HISTORY (past turns)\n{history_str}\n\n"
            f"### CURRENT QUESTION\n{current_question}"
        )
        resp = self._client.chat(
            model=self._chat_model,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM},
                {"role": "user", "content": user_payload},
            ],
        )
        raw = _extract_message_text(resp)
        try:
            data = _parse_json_object(raw)
        except (json.JSONDecodeError, ValueError):
            return {"standalone_query": current_question.strip(), "filters": None}
        q = data.get("standalone_query") or current_question
        return {"standalone_query": str(q).strip(), "filters": None}

    def answer(
        self,
        current_question: str,
        history: List[Dict[str, str]],
        sm: StorageManager,
        vm: VectorManager,
        *,
        n_results: int = 20,
        max_distance: float = 0.5,
    ) -> str:
        """Full RAG: retrieve by embedding, then generate with the fixed section template."""
        intent = self.get_search_intent(current_question, history)
        standalone = str(intent.get("standalone_query") or current_question).strip()
        vec = self._embedder.embed(standalone)
        raw_hits = vm.query_semantic(
            vec,
            n_results=n_results,
            max_distance=max_distance,
        )
        uuids: List[UUID] = []
        for h in raw_hits:
            sid = h.get("id")
            if sid is None:
                continue
            try:
                uuids.append(UUID(str(sid)))
            except ValueError:
                continue
        entries = sm.get_entries_by_ids_in_order(uuids)
        context_blocks = [
            f"---\nTitle: {e.title}\n\n{e.content}\n" for e in entries
        ]
        context_text = (
            "\n".join(context_blocks)
            if context_blocks
            else "(no relevant journal entries found within the distance threshold.)"
        )
        history_str = _format_history_block(history)
        prompt = f"""### SYSTEM PROMPT: You are a personal journal assistant.

### HISTORY: {history_str}

### CONTEXT: {context_text}

### QUESTION: {current_question}

Answer helpfully using CONTEXT when it is relevant; if CONTEXT is empty or not useful, say so briefly but try to answer the question based on the HISTORY."""
        resp = self._client.chat(
            model=self._chat_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_message_text(resp).strip()
