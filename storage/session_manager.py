from __future__ import annotations

from typing import Any, Dict, List


class InMemorySessionManager:
    """In-memory store: session_id -> list of {role, content} messages."""

    def __init__(self) -> None:
        self._sessions: Dict[str, List[Dict[str, str]]] = {}

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return [dict(m) for m in self._sessions.get(session_id, [])]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self._sessions.setdefault(session_id, []).append(
            {"role": role, "content": content}
        )
