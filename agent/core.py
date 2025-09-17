from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

try:
    from voice_mvp.backend import (  # type: ignore[import-not-found]
        ConversationStage,
        MenuCatalog,
        RecommendationEngine,
        ReviewService,
    )
except ModuleNotFoundError:  # pragma: no cover - fallback when running flat
    from backend import (
        ConversationStage,
        MenuCatalog,
        RecommendationEngine,
        ReviewService,
    )

from .config import default_prompt
from .memory import Memory

if TYPE_CHECKING:  # pragma: no cover
    from .llm_openai import AzureLLM


KOREAN_NUMBER_WORDS = {
    "한": 1,
    "하나": 1,
    "두": 2,
    "둘": 2,
    "세": 3,
    "셋": 3,
    "네": 4,
    "넷": 4,
    "다섯": 5,
    "여섯": 6,
    "일곱": 7,
    "여덟": 8,
    "아홉": 9,
    "열": 10,
}

CONFIRM_WORDS = {"네", "예", "맞아요", "맞아", "좋아요", "해주세요", "주문", "확인"}
CANCEL_WORDS = {"아니", "취소", "다른", "변경"}
THANKS_WORDS = {"고마", "감사"}
RECOMMEND_WORDS = {"추천", "뭐가", "먹을까", "골라", "인기", "메뉴 좀"}
INTRO_WORDS = {"소개", "가게", "설명", "어떤 곳"}
REVIEW_WORDS = {"후기", "리뷰", "평점"}


class VoiceOrderAgent:
    """Conversational agent that guides seniors through ordering."""

    def __init__(
        self,
        menu_catalog: MenuCatalog,
        review_service: ReviewService,
        recommender: RecommendationEngine,
        memory: Memory,
        llm: Optional["AzureLLM"] = None,
    ) -> None:
        self.prompt = default_prompt
        self.catalog = menu_catalog
        self.reviews = review_service
        self.recommender = recommender
        self.memory = memory
        self.llm = llm

    # ------------------------------------------------------------------
    def handle(
        self,
        session_id: str,
        message: str,
        *,
        store: str | None = None,
        selected_names: Optional[List[str]] = None,
        profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        session = self.memory.get_session(session_id)
        if profile:
            session.profile = profile
        cleaned = (message or "").strip()
        session.remember_user(cleaned)

        if store:
            session.store = store.strip()
        else:
            guessed_store = self._guess_store(cleaned)
            if guessed_store:
                session.store = guessed_store

        if selected_names:
            for name in selected_names:
                match = self.catalog.find(session.store, name) if session.store else None
                if match:
                    session.selected_menu = match.name
                    session.stage = ConversationStage.AWAIT_QUANTITY

        if not session.store:
            session.stage = ConversationStage.NEED_STORE
            reply = "어느 가게에서 주문을 도와드릴까요? 가게 이름을 말씀해 주세요."
            return self._respond(session, reply, {}, [])

        intents = self._parse_intents(cleaned, session)
        ui: Dict[str, Any] = {"store": session.store}
        actions: List[Dict[str, Any]] = []

        if intents.get("thanks"):
            reply = "도움이 되어 기뻐요. 더 필요하신 게 있으면 말씀해 주세요."
            return self._respond(session, reply, ui, actions)

        if intents.get("cancel") and session.stage in {
            ConversationStage.AWAIT_CONFIRMATION,
            ConversationStage.AWAIT_MENU_CHOICE,
        }:
            session.selected_menu = None
            session.quantity = None
            session.stage = ConversationStage.AWAIT_MENU_CHOICE
            reply = "알겠습니다. 다른 메뉴를 다시 추천해 드릴까요?"
            return self._respond(session, reply, ui, actions)

        review_bundle = self.reviews.get(session.store)
        menu_items = self.catalog.list(session.store)

        if session.stage == ConversationStage.NEED_STORE:
            session.stage = ConversationStage.AWAIT_RECOMMENDATION
            ui["reviews"] = review_bundle.to_api()
            if menu_items:
                ui["menu"] = [item.to_api() for item in menu_items]
            reply = self._intro_message(session.store, review_bundle.summary)
            return self._respond(session, reply, ui, actions)

        if intents.get("introduction"):
            session.stage = ConversationStage.AWAIT_RECOMMENDATION
            ui["reviews"] = review_bundle.to_api()
            reply = self._intro_message(session.store, review_bundle.summary)
            return self._respond(session, reply, ui, actions)

        if intents.get("reviews"):
            ui["reviews"] = review_bundle.to_api()
            reply = review_bundle.summary
            if review_bundle.highlights:
                reply += " " + " ".join(review_bundle.highlights[:2])
            session.stage = ConversationStage.AWAIT_RECOMMENDATION
            return self._respond(session, reply, ui, actions)

        if intents.get("recommend") or session.stage == ConversationStage.AWAIT_RECOMMENDATION:
            recos = self.recommender.recommend(session.store, session.profile)
            session.recommendations = [item.name for item in recos]
            if recos:
                ui["recommendations"] = [item.to_api() for item in recos]
                reply = self._recommend_message(recos)
                session.stage = ConversationStage.AWAIT_MENU_CHOICE
                return self._respond(session, reply, ui, actions)
            session.stage = ConversationStage.AWAIT_MENU_CHOICE

        explain_target = intents.get("explain")
        if explain_target and session.store:
            item = self.catalog.find(session.store, explain_target)
            if item:
                ui["menu"] = [item.to_api()]
                reply = self._explain_message(item)
                return self._respond(session, reply, ui, actions)

        menu_choice = intents.get("menu_choice")
        if menu_choice:
            item = self.catalog.find(session.store, menu_choice)
            if item:
                session.selected_menu = item.name
                session.stage = ConversationStage.AWAIT_QUANTITY
                ui.setdefault("menu", [item.to_api()])
                reply = f"{item.name}을 고르셨네요. 몇 개 준비해 드릴까요?"
                return self._respond(session, reply, ui, actions)

        if session.stage == ConversationStage.AWAIT_MENU_CHOICE and not session.selected_menu:
            reply = "괜찮아 보이는 메뉴가 있으시면 메뉴 이름을 말씀해 주세요."
            return self._respond(session, reply, ui, actions)

        quantity = intents.get("quantity")
        if quantity and session.selected_menu:
            session.quantity = quantity
            session.stage = ConversationStage.AWAIT_CONFIRMATION
            reply = f"{session.selected_menu} {quantity}개로 도와드릴까요? 확인해 주세요."
            return self._respond(session, reply, ui, actions)

        if session.stage == ConversationStage.AWAIT_QUANTITY and session.selected_menu:
            reply = "필요하신 수량을 숫자로 말씀해 주세요."
            return self._respond(session, reply, ui, actions)

        if intents.get("confirm") and session.stage == ConversationStage.AWAIT_CONFIRMATION:
            reply, ui_update = self._complete_order(session)
            ui.update(ui_update)
            actions.append({"type": "ORDER"})
            return self._respond(session, reply, ui, actions)

        if session.stage == ConversationStage.AWAIT_CONFIRMATION:
            reply = "괜찮으시면 '네'라고 답해 주시면 주문을 마칠게요."
            return self._respond(session, reply, ui, actions)

        reply = "필요하신 메뉴나 도움이 있다면 편하게 말씀해 주세요."
        return self._respond(session, reply, ui, actions)

    # ------------------------------------------------------------------
    def _respond(
        self,
        session: Any,
        raw_reply: str,
        ui: Optional[Dict[str, Any]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        final_reply = self._finalize_reply(session, raw_reply, ui or {})
        session.remember_agent(final_reply)
        return {
            "reply": final_reply,
            "ui": ui or {},
            "actions": actions or [],
            "state": session.as_state(),
        }

    def _finalize_reply(self, session: Any, raw_reply: str, ui: Dict[str, Any]) -> str:
        if not self.llm:
            return raw_reply
        context_parts = [
            f"현재 단계: {session.stage.value}",
            f"매장: {session.store or '미정'}",
        ]
        if session.selected_menu:
            context_parts.append(f"선택 메뉴: {session.selected_menu}")
        if session.quantity:
            context_parts.append(f"수량: {session.quantity}")
        if session.recommendations:
            context_parts.append(
                "추천 후보: " + ", ".join(session.recommendations[:3])
            )
        if ui.get("recommendations"):
            names = [rec.get("name") for rec in ui["recommendations"] if isinstance(rec, dict)]
            if names:
                context_parts.append("화면 추천: " + ", ".join(names))

        system_prompt = (
            self.prompt
            + "\n위 정보와 원문을 참고하여 시니어가 이해하기 쉬운 말투로,"
            + " 2문장 이내로 정리해서 답하세요."
        )
        payload = raw_reply
        if context_parts:
            payload += "\n\n상황 정보: " + " | ".join(context_parts)

        result = self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload},
            ]
        )
        content = (result or {}).get("content") if isinstance(result, dict) else None
        return content.strip() if isinstance(content, str) and content.strip() else raw_reply

    # ------------------------------------------------------------------
    def _parse_intents(self, message: str, session: Any) -> Dict[str, Any]:
        lower = message.lower()
        compact = lower.replace(" ", "")
        intents: Dict[str, Any] = {}
        if any(word in message for word in INTRO_WORDS):
            intents["introduction"] = True
        if any(word in message for word in RECOMMEND_WORDS):
            intents["recommend"] = True
        if any(word in message for word in REVIEW_WORDS):
            intents["reviews"] = True
        if any(word in message for word in THANKS_WORDS):
            intents["thanks"] = True
        if any(word in message for word in CANCEL_WORDS):
            intents["cancel"] = True
        if any(word in message for word in CONFIRM_WORDS):
            intents["confirm"] = True

        quantity = self._extract_quantity(message)
        if quantity:
            intents["quantity"] = quantity

        if "설명" in message or "어떤" in message:
            intents["explain"] = self._match_menu_name(message, session.store)

        menu_choice = self._match_menu_name(message, session.store)
        if menu_choice:
            intents["menu_choice"] = menu_choice

        return intents

    def _extract_quantity(self, message: str) -> Optional[int]:
        match = re.search(r"(\d+)", message)
        if match:
            qty = int(match.group(1))
            return qty if qty > 0 else None
        for word, value in KOREAN_NUMBER_WORDS.items():
            if word in message:
                return value
        return None

    def _match_menu_name(self, message: str, store: str) -> Optional[str]:
        if not store:
            return None
        normalized = message.replace(" ", "").lower()
        for item in self.catalog.list(store):
            candidate = item.name.replace(" ", "").lower()
            if candidate and candidate in normalized:
                return item.name
        return None

    def _guess_store(self, message: str) -> Optional[str]:
        normalized = message.replace(" ", "")
        for store_name in self.catalog.stores():
            if store_name.replace(" ", "") in normalized:
                return store_name
        if "옥소반" in message:
            return "옥소반 마곡본점"
        return None

    def _intro_message(self, store: str, summary: str) -> str:
        return f"{store}은 이런 곳이에요. {summary} 메뉴 추천이나 주문이 필요하시면 말씀해 주세요."

    def _recommend_message(self, items: List[Any]) -> str:
        names = [item.name for item in items if item.name]
        if not names:
            return "추천할 수 있는 메뉴 정보가 아직 없어요."
        if len(names) == 1:
            return f"{names[0]}이 특히 반응이 좋습니다. 괜찮으시면 이 메뉴로 도와드릴까요?"
        joined = ", ".join(names)
        return f"이 가게에서는 {joined} 메뉴가 반응이 좋아요. 관심 가는 메뉴가 있으신가요?"

    def _explain_message(self, item: Any) -> str:
        base = item.desc or "부드럽고 편하게 드시기 좋아요."
        price = f"가격은 {item.price:,}원" if item.price else "가격 정보가 등록되어 있지 않아요"
        return f"{item.name}은 {base} {price}."

    def _complete_order(self, session: Any) -> tuple[str, Dict[str, Any]]:
        session.stage = ConversationStage.ORDER_COMPLETE
        qty = session.quantity or 1
        item = self.catalog.find(session.store, session.selected_menu or "")
        price = (item.price if item else 0) * qty
        payment = {
            "status": "mock",
            "amount": price,
            "items": [
                {
                    "name": session.selected_menu,
                    "price": item.price if item else 0,
                    "quantity": qty,
                }
            ],
        }
        ui = {"payment": payment}
        reply = (
            f"주문을 접수해 두었어요. {session.selected_menu} {qty}개, 총 {price:,}원으로 정리했습니다. "
            "결제는 모의 처리이니 안심하셔도 됩니다. 다른 도움이 필요하시면 알려 주세요."
        )
        return reply, ui


__all__ = ["VoiceOrderAgent"]
