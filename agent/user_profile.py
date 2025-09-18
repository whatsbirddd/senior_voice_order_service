from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List


@dataclass
class SingleUserRecord:
    profile: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"profile": self.profile, "history": self.history}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SingleUserRecord":
        return cls(
            profile=dict(data.get("profile") or {}),
            history=list(data.get("history") or []),
        )


class SingleUserProfileStore:
    """Simple JSON-backed store for a single user's profile + history.

    This matches the app flow where the app is dedicated to one user/device.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = RLock()
        self._record = SingleUserRecord()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._record = SingleUserRecord.from_dict(raw)
        except Exception:
            # keep defaults if corrupted
            self._record = SingleUserRecord()

    def _save(self) -> None:
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def get(self) -> SingleUserRecord:
        with self._lock:
            return SingleUserRecord.from_dict(self._record.to_dict())

    def upsert_profile(self, patch: Dict[str, Any]) -> SingleUserRecord:
        with self._lock:
            for k, v in (patch or {}).items():
                if k in ("allergies", "diseases", "prefers", "dislikes"):
                    prev = list(self._record.profile.get(k) or [])
                    merged = list({*prev, *(v or [])})
                    self._record.profile[k] = merged
                else:
                    self._record.profile[k] = v
            self._save()
            return SingleUserRecord.from_dict(self._record.to_dict())

    def add_order(self, *, store: str, item: str, quantity: int) -> SingleUserRecord:
        entry = {"store": store, "item": item, "quantity": int(quantity)}
        with self._lock:
            self._record.history.append(entry)
            self._save()
            return SingleUserRecord.from_dict(self._record.to_dict())

    def history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._record.history)

