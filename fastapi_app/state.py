from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ConversationStage(str, Enum):
    NEED_STORE = "need_store"
    INTRODUCED = "introduced"
    AWAIT_RECOMMENDATION = "await_recommendation"
    AWAIT_MENU_CHOICE = "await_menu_choice"
    AWAIT_QUANTITY = "await_quantity"
    AWAIT_CONFIRMATION = "await_confirmation"
    ORDER_COMPLETE = "order_complete"


@dataclass
class OrderSession:
    session_id: str
    stage: ConversationStage = ConversationStage.NEED_STORE
    store: str = ""
    selected_menu: Optional[str] = None
    quantity: Optional[int] = None
    recommendations: List[str] = field(default_factory=list)
    profile: Dict[str, object] = field(default_factory=dict)
    last_agent_message: str = ""
    history: List[Dict[str, str]] = field(default_factory=list)

    def remember_agent(self, message: str) -> None:
        self.last_agent_message = message
        self.history.append({"role": "assistant", "message": message})

    def remember_user(self, message: str) -> None:
        self.history.append({"role": "user", "message": message})

    def as_state(self) -> Dict[str, object]:
        return {
            "stage": self.stage.value,
            "store": self.store,
            "selectedMenu": self.selected_menu,
            "quantity": self.quantity,
            "recommendations": self.recommendations,
        }


__all__ = ["OrderSession", "ConversationStage"]
