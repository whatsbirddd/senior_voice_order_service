from __future__ import annotations

from pathlib import Path

try:  # Support both `voice_mvp` package and flat module execution
    from voice_mvp.backend import MenuCatalog, RecommendationEngine, ReviewService  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover
    from fastapi_app import MenuCatalog, RecommendationEngine, ReviewService

from .core import VoiceOrderAgent
from .memory import Memory
from .llm_openai import AzureLLM


def build_agent() -> VoiceOrderAgent:
    catalog = MenuCatalog()
    data_path = Path(__file__).resolve().parent.parent / "data" / "oxoban_menu.json"
    catalog.bootstrap_from_file(data_path)

    reviews = ReviewService()
    reviews.bootstrap()

    recommender = RecommendationEngine(catalog, reviews)
    memory = Memory()
    llm = AzureLLM()

    return VoiceOrderAgent(
        menu_catalog=catalog,
        review_service=reviews,
        recommender=recommender,
        memory=memory,
        llm=llm if llm.available else None,
    )


__all__ = ["build_agent", "VoiceOrderAgent"]
