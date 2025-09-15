from typing import Dict, Any


class Memory:
    def __init__(self):
        self._session: Dict[str, Dict[str, Any]] = {}

    def get(self, session_id: str) -> Dict[str, Any]:
        return self._session.setdefault(session_id, {
            "store": "",
            "history": [],  # list of {role, message}
            "prefs": {},
        })

    def update(self, session_id: str, patch: Dict[str, Any]):
        s = self.get(session_id)
        s.update(patch)
        self._session[session_id] = s
        return s

    def append_history(self, session_id: str, role: str, message: str):
        s = self.get(session_id)
        s.setdefault("history", []).append({"role": role, "message": message})
        return s

    def clear(self, session_id: str):
        self._session.pop(session_id, None)

