from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import RLock
from typing import Dict, Iterable, List, Optional


@dataclass
class MenuItem:
    """Represents a single menu item."""

    name: str
    desc: str = ""
    price: int = 0
    image: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    allergens: List[str] = field(default_factory=list)

    def to_api(self) -> Dict[str, object]:
        data = asdict(self)
        data["description"] = data.pop("desc", "")
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "MenuItem":
        return cls(
            name=str(data.get("name", "")).strip(),
            desc=str(data.get("desc") or data.get("description") or ""),
            price=int(data.get("price", 0) or 0),
            image=(data.get("image") or data.get("img") or None),
            tags=list(data.get("tags", []) or []),
            allergens=list(data.get("allergens", []) or []),
        )


class MenuCatalog:
    """Thread-safe in-memory catalogue that powers the API and agent."""

    def __init__(self) -> None:
        self._menus: Dict[str, List[MenuItem]] = {}
        self._featured: Dict[str, MenuItem] = {}
        self._lock = RLock()

    # ------------------------------------------------------------------
    def bootstrap_from_file(self, path: Path) -> None:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        store = str(payload.get("store", "")).strip()
        if not store:
            return
        menu_items = [MenuItem.from_dict(it) for it in payload.get("menu", [])]
        featured = None
        if isinstance(payload.get("featured"), dict):
            featured = MenuItem.from_dict(payload["featured"])
        self.upsert(store=store, menu=menu_items, featured=featured)

    # ------------------------------------------------------------------
    def upsert(self, store: str, menu: Iterable[MenuItem], featured: Optional[MenuItem] = None) -> None:
        store_key = store.strip()
        if not store_key:
            raise ValueError("store name required")
        items = [item for item in menu if item.name]
        with self._lock:
            self._menus[store_key] = items
            if featured and featured.name:
                self._featured[store_key] = featured
            elif items:
                self._featured[store_key] = items[0]

    # ------------------------------------------------------------------
    def list(self, store: str) -> List[MenuItem]:
        with self._lock:
            return list(self._menus.get(store.strip(), []))

    def featured(self, store: str) -> Optional[MenuItem]:
        with self._lock:
            return self._featured.get(store.strip())

    def find(self, store: str, name: str) -> Optional[MenuItem]:
        needle = name.replace(" ", "").lower()
        for item in self.list(store):
            if item.name.replace(" ", "").lower() == needle:
                return item
        return None

    def has_menu(self, store: str) -> bool:
        return bool(self.list(store))

    def stores(self) -> List[str]:
        with self._lock:
            return list(self._menus.keys())


__all__ = ["MenuCatalog", "MenuItem"]
