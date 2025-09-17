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
    from fastapi_app import (
        ConversationStage,
        MenuCatalog,
        RecommendationEngine,
        ReviewService,
    )

from .prompt import default_prompt
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
        """LLM 기반 대화 처리 - 모든 로직을 LLM에 위임"""
        session = self.memory.get_session(session_id)
        if profile:
            session.profile = profile
        cleaned = (message or "").strip()
        session.remember_user(cleaned)

        # 가게 정보 설정
        if store:
            session.store = store.strip()
        elif not session.store:
            # 기본 매장으로 옥소반 마곡본점 고정
            session.store = "옥소반 마곡본점"

        # selected_names 처리 (프론트엔드에서 메뉴 선택한 경우)
        if selected_names:
            for name in selected_names:
                match = self.catalog.find(session.store, name) if session.store else None
                if match:
                    session.selected_menu = match.name
                    session.stage = ConversationStage.AWAIT_QUANTITY

        # LLM이 사용 가능한 경우 모든 처리를 LLM에 위임
        if self.llm and getattr(self.llm, "available", False):
            try:
                llm_response = self._handle_with_llm(session, cleaned)
                if llm_response:
                    return llm_response
            except Exception as e:
                # LLM 실패 시 기본 응답
                return self._respond(
                    session, 
                    "죄송합니다. 잠시 문제가 있었습니다. 다시 말씀해 주세요.", 
                    {"store": session.store or ""}, 
                    []
                )

        # LLM이 없는 경우 기본 응답
        if not session.store:
            reply = "어느 가게에서 주문을 도와드릴까요? 가게 이름을 말씀해 주세요."
            return self._respond(session, reply, {}, [])
        
        return self._respond(
            session, 
            "안녕하세요! 주문을 도와드리겠습니다. 무엇을 드시고 싶으신가요?", 
            {"store": session.store}, 
            []
        )
    def _handle_with_llm(self, session: Any, cleaned_message: str) -> Optional[Dict[str, Any]]:
        if not self.llm or not getattr(self.llm, "available", False):
            return None

        import json

        history_messages: List[Dict[str, str]] = []
        for turn in (session.history or [])[-6:]:
            role = turn.get("role", "user")
            content = turn.get("message", "")
            if content:
                history_messages.append({"role": role, "content": content})

        context_parts = []
        if session.store:
            context_parts.append(f"매장: {session.store}")
        context_parts.append(f"단계: {session.stage.value}")
        if session.selected_menu:
            context_parts.append(f"선택 메뉴: {session.selected_menu}")
        if session.quantity:
            context_parts.append(f"수량: {session.quantity}")
        if session.recommendations:
            context_parts.append("추천 후보: " + ", ".join(session.recommendations[:3]))

        state_summary = " | ".join(context_parts)
        user_message = cleaned_message
        if state_summary:
            user_message += f"\n\n현재 상태: {state_summary}"

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.prompt},
        ]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": user_message})

        llm_reply = self.llm.chat(messages)
        content = (llm_reply or {}).get("content") if isinstance(llm_reply, dict) else None
        if not content:
            return None

        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`\n")
            if "{" in content:
                content = content[content.find("{") : content.rfind("}") + 1]

        try:
            parsed = json.loads(content)
        except Exception:
            return None

        speak = str(parsed.get("speak") or "무엇을 도와드릴까요?")
        actions = parsed.get("actions")
        if not isinstance(actions, list):
            actions = []
        memory_patch = parsed.get("memory")
        if isinstance(memory_patch, dict):
            self._apply_memory_patch(session, memory_patch)

        session.remember_agent(speak)
        return {
            "reply": speak,
            "ui": {"store": session.store},
            "actions": actions,
            "state": session.as_state(),
        }

    def _apply_memory_patch(self, session: Any, patch: Dict[str, Any]) -> None:
        store = patch.get("store")
        if isinstance(store, str) and store.strip():
            session.store = store.strip()

        stage = patch.get("stage")
        if isinstance(stage, str):
            try:
                session.stage = ConversationStage(stage)
            except ValueError:
                pass

        selected = patch.get("selected_menu") or patch.get("selectedMenu")
        if isinstance(selected, str) and selected:
            session.selected_menu = selected

        qty = patch.get("quantity") or patch.get("qty")
        if isinstance(qty, int):
            session.quantity = qty

        recos = patch.get("recommendations")
        if isinstance(recos, list):
            session.recommendations = [str(r) for r in recos if isinstance(r, str)]

        profile = patch.get("profile")
        if isinstance(profile, dict):
            session.profile.update(profile)

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
