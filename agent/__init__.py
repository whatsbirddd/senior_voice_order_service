from __future__ import annotations

from pathlib import Path

try:  # Support both `voice_mvp` package and flat module execution
    from voice_mvp.backend import MenuCatalog  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover
    from fastapi_app.menus import MenuCatalog

from .core import VoiceOrderAgent
from .memory import Memory
from .llm_openai import AzureLLM


def build_agent() -> VoiceOrderAgent:
    catalog = MenuCatalog()
    data_path = Path(__file__).resolve().parent.parent / "data" / "oxoban_menu.json"
    catalog.bootstrap_from_file(data_path)

    memory = Memory()
    llm = AzureLLM()
    try:
        # Lightweight diagnostics to help spot misconfiguration in dev
        print(
            "[Agent] Azure LLM configured:",
            {
                "available": llm.available,
                "endpoint": getattr(llm, "endpoint", None),
                "deployment": getattr(llm, "deployment", None),
                "api_version": getattr(llm, "api_version", None),
            },
        )
    except Exception:
        pass

    return VoiceOrderAgent(
        menu_catalog=catalog,
        memory=memory,
        llm=llm if llm.available else None,
    )


__all__ = ["build_agent", "VoiceOrderAgent"]
