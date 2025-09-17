from __future__ import annotations

from threading import RLock
from typing import Dict, List, Optional

try:
    from voice_mvp.backend import OrderSession  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover
    from backend import OrderSession


class Memory:
    """Session memory storing structured order conversations."""

    def __init__(self) -> None:
        self._sessions: Dict[str, OrderSession] = {}
        self._lock = RLock()

    def get_session(self, session_id: str) -> OrderSession:
        session_key = session_id or "default"
        with self._lock:
            if session_key not in self._sessions:
                self._sessions[session_key] = OrderSession(session_id=session_key)
            return self._sessions[session_key]

    # Backwards compatible helpers -------------------------------------
    def get(self, session_id: str) -> Dict[str, object]:
        session = self.get_session(session_id)
        return {
            "store": session.store,
            "stage": session.stage.value,
            "selectedMenu": session.selected_menu,
            "quantity": session.quantity,
            "history": list(session.history),
            "profile": dict(session.profile),
        }

    def update(self, session_id: str, patch: Dict[str, object]) -> Dict[str, object]:
        session = self.get_session(session_id)
        store = patch.get("store")
        if isinstance(store, str) and store.strip():
            session.store = store.strip()
        profile = patch.get("profile")
        if isinstance(profile, dict):
            session.profile.update(profile)
        return self.get(session_id)

    def append_history(self, session_id: str, role: str, message: str) -> None:
        session = self.get_session(session_id)
        session.history.append({"role": role, "message": message})

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def all_sessions(self) -> List[OrderSession]:
        with self._lock:
            return list(self._sessions.values())


__all__ = ["Memory"]
