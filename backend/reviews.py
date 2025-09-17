from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ReviewBundle:
    store: str
    summary: str
    highlights: List[str] = field(default_factory=list)
    reviews: List[str] = field(default_factory=list)

    def to_api(self) -> Dict[str, object]:
        return {
            "store": self.store,
            "summary": self.summary,
            "highlights": self.highlights,
            "reviews": self.reviews,
        }


class ReviewService:
    """Simple review source backed by in-memory templates."""

    def __init__(self) -> None:
        self._data: Dict[str, ReviewBundle] = {}

    def bootstrap(self) -> None:
        # Provide a sensible default for the demo store.
        default_store = "옥소반 마곡본점"
        if default_store not in self._data:
            self._data[default_store] = ReviewBundle(
                store=default_store,
                summary=(
                    "옥소반 마곡본점은 부드러운 서비스와 깔끔한 내부로 유명해요. "
                    "어르신들이 드시기 좋은 담백한 메뉴가 많고, 양이 넉넉하다는 평가가 많습니다."
                ),
                highlights=[
                    "직원 응대가 친절해서 재방문한다는 후기가 많아요.",
                    "담백한 한식 위주의 메뉴라 속이 편안하다는 의견이 많아요.",
                    "점심 시간 대기열이 있으니 미리 예약하면 편합니다.",
                ],
                reviews=[
                    "부모님 모시고 갔는데 반찬이 깔끔하고 짜지 않아서 좋아하셨어요.",
                    "사장님이 친절하고 자리 안내도 빨랐어요.",
                    "음식이 따뜻하게 나와서 좋았고 양도 많았습니다.",
                ],
            )

    def get(self, store: str) -> ReviewBundle:
        if not self._data:
            self.bootstrap()
        if store in self._data:
            return self._data[store]
        summary = (
            f"{store}는 친절한 서비스와 편안한 분위기로 후기가 좋아요. "
            f"대표 메뉴가 맛있고 양이 넉넉하다는 의견이 많습니다."
        )
        bundle = ReviewBundle(store=store, summary=summary)
        self._data[store] = bundle
        return bundle

    def set(self, bundle: ReviewBundle) -> None:
        self._data[bundle.store] = bundle


__all__ = ["ReviewService", "ReviewBundle"]
