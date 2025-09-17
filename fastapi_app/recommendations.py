from __future__ import annotations

from typing import Dict, List

from .menus import MenuCatalog, MenuItem
from .reviews import ReviewService


class RecommendationEngine:
    """Lightweight recommender focusing on senior-friendly suggestions."""

    def __init__(self, menus: MenuCatalog, reviews: ReviewService) -> None:
        self._menus = menus
        self._reviews = reviews

    def recommend(
        self,
        store: str,
        profile: Dict[str, object] | None = None,
        limit: int = 3,
    ) -> List[MenuItem]:
        menu = self._menus.list(store)
        if not menu:
            return []
        allergies = set()
        dislikes = set()
        if profile:
            allergies = {str(a) for a in profile.get("allergies", [])}
            dislikes = {str(a) for a in profile.get("dislikes", [])}
        filtered: List[MenuItem] = []
        for item in menu:
            if allergies and (allergies & set(item.allergens)):
                continue
            if dislikes and any(d in item.name for d in dislikes):
                continue
            filtered.append(item)
        if not filtered:
            filtered = menu

        bundle = self._reviews.get(store)
        text_blob = " ".join(bundle.reviews + [bundle.summary])
        scored = []
        for item in filtered:
            score = 0
            if item.name and item.name in text_blob:
                score += 2
            if "부드럽" in text_blob and ("죽" in item.name or "스프" in item.name):
                score += 1
            if "담백" in text_blob and ("정식" in item.name or "구이" in item.name):
                score += 1
            scored.append((score, item))
        scored.sort(key=lambda tup: tup[0], reverse=True)
        return [itm for _, itm in scored[:limit]] or filtered[:limit]


__all__ = ["RecommendationEngine"]
