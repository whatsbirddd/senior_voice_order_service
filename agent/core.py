# core.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

try:
    from voice_mvp.backend import ConversationStage, MenuCatalog  # type: ignore[import-not-found]
except ModuleNotFoundError:
    from fastapi_app.state import ConversationStage  # type: ignore
    from fastapi_app.menus import MenuCatalog  # type: ignore

from .prompt import default_prompt
from .memory import Memory
from . import tools as toolmod  # <-- docstring 기반 discover

# 프론트가 이해하는 액션만 전달
UI_ACTION_WHITELIST = {
    "NAVIGATE",
    "SHOW_RECOMMENDATIONS",
    "SELECT_MENU_BY_NAME",
    "SET_QTY",
    "INCREMENT_QTY",
    "DECREMENT_QTY",
    "ADD_TO_CART",
    'REMOVE_FROM_CART',
    "READ_BACK_SUMMARY",
    "ORDER",
}

def _strip_json_fence(text: str) -> str:
    """Return a JSON string.

    - If the LLM output is fenced (```), remove the fence and extract the outermost JSON object.
    - If the result does not look like JSON, wrap the raw text as a minimal JSON payload
      so downstream json.loads() always succeeds:
        {"speak": <raw_text>, "actions": [{"type": "CLARIFY"}]}
    """
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`\n")
        if "{" in t and "}" in t:
            t = t[t.find("{") : t.rfind("}") + 1]
    # If already looks like a JSON object, return as-is
    if t.startswith("{") and t.endswith("}"):
        return t
    # Fallback: coerce to minimal JSON structure so parsing doesn't fail later
    speak = t or "원하시는 메뉴를 조금 더 구체적으로 말씀해 주시겠어요?"
    fallback = {"speak": speak, "actions": [{"type": "CLARIFY"}]}
    try:
        return json.dumps(fallback, ensure_ascii=False)
    except Exception:
        # Extremely defensive: last resort plain string in JSON
        return '{"speak":"%s","actions":[{"type":"CLARIFY"}]}' % speak.replace('"', '\\"')


class VoiceOrderAgent:
    """
    default_prompt + (docstring에서 추출된 도구 안내/스키마)를 사용.
    OpenAI function-calling 루프로 툴을 자동 선택/실행한다.
    """

    def __init__(
        self,
        menu_catalog: MenuCatalog,
        memory: Memory,
        llm: Optional["AzureLLM"] = None,
    ) -> None:
        self.catalog = menu_catalog
        self.memory = memory
        self.llm = llm

        # 툴 준비 (카탈로그 주입 → docstring discover)
        toolmod.set_catalog(menu_catalog)
        self._tool_schemas, self._tool_map, self._tools_text = toolmod.discover_tools()

    # ------------------------------------------------------------------
    def handle(
        self,
        session_id: str,
        message: str,
        *,
        store: Optional[str] = None,
        selected_names: Optional[List[str]] = None,
        profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        session = self.memory.get_session(session_id)

        if profile:
            session.profile.update(profile)

        text = (message or "").strip()
        if text:
            session.remember_user(text)

        # 기본 매장
        if store:
            session.store = store.strip()
        elif not session.store:
            session.store = "옥소반 마곡본점"

        # 클라에서 직접 선택한 메뉴 반영
        if selected_names:
            for name in selected_names:
                m = self.catalog.find(session.store, name)
                if m:
                    session.selected_menu = m.name
                    session.stage = ConversationStage.AWAIT_QUANTITY

        if not (self.llm and getattr(self.llm, "available", False)):
            print("[Agent] LLM not available")
            return self._respond(session, "안녕하세요. 무엇을 도와드릴까요?", {"store": session.store}, [])

        try:
            print(f"[Agent 응답 가능 / _loop_with_function_calling] session={session_id} stage={session.stage} store={session.store} selected_menu={session.selected_menu} quantity={session.quantity} profile={session.profile}")
            return self._loop_with_function_calling(session, text)
        except Exception:
            return self._respond(session, "죄송합니다. 다시 한 번 말씀해 주세요.", {"store": session.store}, [])

    # ------------------------------------------------------------------
    def _loop_with_function_calling(self, session: Any, user_text: str) -> Dict[str, Any]:
        # 상태 요약
        context = [
            f"단계: {session.stage.value}",
            f"매장: {session.store or '미정'}",
        ]
        if session.selected_menu:
            context.append(f"선택 메뉴: {session.selected_menu}")
        if session.quantity:
            context.append(f"수량: {session.quantity}")
        if session.profile:
            prefers = ", ".join(session.profile.get("prefers", [])[:3]) if session.profile.get("prefers") else ""
            allergies = ", ".join(session.profile.get("allergies", [])[:3]) if session.profile.get("allergies") else ""
            limits = session.profile.get("nutrition_limits") or {}
            lim_s = ", ".join([f"{k}≤{v}" for k, v in list(limits.items())[:3]]) if limits else ""
            brief = " / ".join([s for s in [prefers, allergies, lim_s] if s])
            if brief:
                context.append(f"프로필: {brief}")

        # 메뉴 요약(이름/가격/간단 설명) - LLM이 근사 매칭/정규화에 활용하도록 제공
        menu_items = []
        try:
            for m in self.catalog.list(session.store)[:60]:
                name = getattr(m, "name", "")
                price = getattr(m, "price", None)
                desc = (getattr(m, "desc", "") or "").strip()
                price_s = f" | {price}원" if isinstance(price, (int, float)) and price is not None else ""
                if desc:
                    desc = (desc[:36] + ("…" if len(desc) > 36 else ""))
                    menu_items.append(f"- {name}{price_s} | {desc}")
                else:
                    menu_items.append(f"- {name}{price_s}")
        except Exception:
            pass
        menu_block = "\n".join(menu_items)

        # System prompt = default_prompt + 도구 목록 텍스트 + 현재 상태 + 메뉴 요약
        system = (
            default_prompt.strip()
            + "\n\n[사용 가능한 도구]\n"
            + (self._tools_text or "(현재 사용 가능한 도구가 없습니다)")
            + "\n\n[상태]\n"
            + " | ".join(context)
            + ("\n\n[매장 메뉴]\n" + menu_block if menu_block else "")
            + "\n\n[형식]\n반드시 JSON만 출력하세요. 코드블록 금지."
        )
        print(f"[Agent] system prompt:\n{system}")
        # 도구가 전혀 없을 때의 가드: LLM이 답변을 포기하지 않고 재질문하도록 지시
        if not self._tool_schemas:
            system += (
                "\n\n[도구 없음 안내]\n"
                "현재 사용할 수 있는 도구가 없어요. 필요한 정보가 부족하면 speak에 매우 짧은 재질문을 넣고, actions는 비워두세요."
            )

        # 히스토리
        msgs: List[Dict[str, str]] = [{"role": "system", "content": system}]
        for turn in (session.history or [])[-6:]:
            role = turn.get("role", "user"); content = turn.get("message", "")
            if content: msgs.append({"role": role, "content": content})
        msgs.append({"role": "user", "content": user_text})

        # 1차 호출 (tools 없을 때는 tool_choice를 넘기지 않음)
        if self._tool_schemas:
            res = self.llm.chat(msgs, tools=self._tool_schemas, tool_choice="auto")  # type: ignore
        else:
            res = self.llm.chat(msgs)  # type: ignore
        print(f"[Agent] initial response: {res}")
        # Append assistant including tool_calls when present (required by API)
        def _coerce_tool_calls(r: Dict[str, Any]) -> List[Dict[str, Any]]:
            # Normalize different wrappers (our AzureLLM returns `tool_call`)
            tc = r.get("tool_calls") or []
            if not tc and r.get("tool_call"):
                single = r["tool_call"] or {}
                tc = [{
                    "id": single.get("id") or "tc1",
                    "type": "function",
                    "function": {
                        "name": single.get("name"),
                        "arguments": single.get("arguments"),
                    },
                }]
            if not tc and r.get("function_call"):
                fc = r["function_call"]
                tc = [{"id": "fc1", "type": "function", "function": fc}]
            return tc

        tc_list = _coerce_tool_calls(res)
        assistant_msg: Dict[str, Any] = {"role": "assistant"}
        if res.get("content") is not None:
            assistant_msg["content"] = res.get("content")
        if tc_list:
            assistant_msg["tool_calls"] = [
                {"id": c.get("id") or "tc1", "type": "function", "function": c.get("function") or {}}
                for c in tc_list
            ]
        msgs.append(assistant_msg)

        # tool calls 처리
        tool_calls = tc_list
        print(f"[Agent] tool calls: {tool_calls}")
        guard = 0
        while tool_calls and guard < 6:
            for call in tool_calls:
                fn = call.get("function", {}) or {}
                name = (fn.get("name") or "").strip()
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    args = {}

                # --- 호출 전 인자 보정(리뷰: menu_names 자동 주입) ---
                if name == "reviews" and "menu_names" not in args:
                    names = [m.name for m in self.catalog.list(session.store)][:40]
                    args["menu_names"] = names

                # 실제 실행
                func = self._tool_map.get(name)
                if not func:
                    result = {"error": f"unknown tool: {name}"}
                else:
                    # tools 함수는 키워드 호출
                    result = func(**args)

                msgs.append({
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            if self._tool_schemas:
                res = self.llm.chat(msgs, tools=self._tool_schemas, tool_choice="auto")  # type: ignore
            else:
                res = self.llm.chat(msgs)  # type: ignore
            print(f"[Agent] tool call loop {guard} response: {res}")
            tc_list = _coerce_tool_calls(res)
            assistant_msg = {"role": "assistant"}
            if res.get("content") is not None:
                assistant_msg["content"] = res.get("content")
            if tc_list:
                assistant_msg["tool_calls"] = [
                    {"id": c.get("id") or "tc1", "type": "function", "function": c.get("function") or {}}
                    for c in tc_list
                ]
            msgs.append(assistant_msg)
            tool_calls = tc_list
            guard += 1

        # 최종 JSON 파싱
        content = res.get("content")
        print(f"[Agent] 최종 응답: {content}")
        if not content:
            print("[Agent] No content in LLM response")
            return self._respond(session, "원하시는 메뉴를 말씀해 주세요.", {"store": session.store}, [])
        try:
            data = json.loads(_strip_json_fence(content))
        except Exception:
            return self._respond(session, "잘 못 들었어요. 다시 한 번 말씀해 주세요.", {"store": session.store}, [])

        speak = str(data.get("speak") or "무엇을 도와드릴까요?").strip()
        actions = data.get("actions") or []
        mem_patch = data.get("memory") or {}

        if isinstance(mem_patch, dict):
            self._apply_memory_patch(session, mem_patch)

        ui_actions, ui_delta = self._apply_actions(session, actions)
        session.remember_agent(speak)
        return {
            "reply": speak,
            "ui": {"store": session.store, **ui_delta},
            "actions": ui_actions,
            "state": session.as_state(),
        }

    # ------------------------------------------------------------------
    def _apply_actions(self, session: Any, actions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        ui_actions: List[Dict[str, Any]] = []
        ui: Dict[str, Any] = {}

        for a in [x for x in actions if isinstance(x, dict)][:3]:
            t = str(a.get("type") or "").upper()

            if t == "NAVIGATE":
                ui_actions.append({"type": "NAVIGATE", "target": a.get("target")})

            elif t == "SHOW_RECOMMENDATIONS":
                # 기본 추천 목록을 구성하고, 네이버 리뷰(DDG 경유) 신호로 보강
                items = a.get("items") or []
                recs = []
                for it in items[:3]:
                    name = (it.get("name") or "").strip()
                    m = self.catalog.find(session.store, name) if name else None
                    recs.append({
                        "menu_id": it.get("menu_id") or (getattr(m, "id", None) or name),
                        "name": name,
                        "reason": (it.get("reason") or "").strip(),
                        "price": getattr(m, "price", None),
                        "desc": getattr(m, "desc", None),
                    })
                recs = self._enrich_recommendations_with_reviews(session, recs)
                ui["recommendations"] = recs
                ui_actions.append({"type": "SHOW_RECOMMENDATIONS", "items": recs})

            elif t == "SELECT_MENU_BY_NAME":
                name = str(a.get("name") or "")
                m = self.catalog.find(session.store, name)
                if m:
                    session.selected_menu = m.name
                    session.stage = ConversationStage.AWAIT_QUANTITY
                ui_actions.append({"type": "SELECT_MENU_BY_NAME", "name": name})

            elif t == "SET_QTY":
                q = max(1, int(a.get("value", 1)))
                session.quantity = q
                ui_actions.append({"type": "SET_QTY", "value": q})

            elif t == "INCREMENT_QTY":
                session.quantity = max(1, int(session.quantity or 1) + 1)
                ui_actions.append({"type": "INCREMENT_QTY"})

            elif t == "DECREMENT_QTY":
                session.quantity = max(1, int(session.quantity or 1) - 1)
                ui_actions.append({"type": "DECREMENT_QTY"})

            elif t == "ADD_TO_CART":
                ui_actions.append({"type": "ADD_TO_CART"})

            elif t == "READ_BACK_SUMMARY":
                qty = session.quantity or 1
                item = self.catalog.find(session.store, session.selected_menu or "")
                total = (item.price if item else 0) * qty
                ui["summary"] = {"item": session.selected_menu, "qty": qty, "total": total}
                ui_actions.append({"type": "READ_BACK_SUMMARY"})

            elif t == "ORDER":
                qty = session.quantity or 1
                item = self.catalog.find(session.store, session.selected_menu or "")
                price = (item.price if item else 0) * qty
                ui["payment"] = {"status": "success", "amount": price,
                                 "items": [{"name": session.selected_menu, "price": item.price if item else 0, "quantity": qty}]}
                session.stage = ConversationStage.ORDER_COMPLETE
                ui_actions.append({"type": "ORDER"})

        ui_actions = [a for a in ui_actions if a.get("type") in UI_ACTION_WHITELIST]
        return ui_actions, ui

    # ------------------------------------------------------------------
    def _enrich_recommendations_with_reviews(self, session: Any, recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use web reviews (Naver-heavy via DuckDuckGo) to refine reasons/order.

        - Adds a '리뷰 언급 N회' suffix when available
        - Reorders by mention count desc while preserving original order ties
        """
        try:
            names = [r.get("name") for r in recs if r.get("name")]
            # Provide menu_names to improve mention detection
            data = toolmod.reviews(store=session.store, menu_names=names, max_results=8, fetch_pages=False)
            mentions = data.get("menu_mentions") or []
            # Map normalized name -> count
            norm = lambda s: str(s or "").replace(" ", "").lower()
            counts = {norm(m.get("name")): int(m.get("count", 0) or 0) for m in mentions if m.get("name")}

            enriched: List[Dict[str, Any]] = []
            for r in recs:
                n = norm(r.get("name"))
                c = counts.get(n, 0)
                reason = (r.get("reason") or "").strip()
                if c > 0:
                    tag = f"리뷰 언급 {c}회"
                    reason = tag if not reason else f"{reason} · {tag}"
                r2 = {**r, "reason": reason}
                r2["_mention_count"] = c
                enriched.append(r2)
            # sort by mention count desc, stable for ties
            enriched.sort(key=lambda x: x.get("_mention_count", 0), reverse=True)
            for r in enriched:
                r.pop("_mention_count", None)
            return enriched[:3]
        except Exception:
            return recs[:3]

    # ------------------------------------------------------------------
    def _apply_memory_patch(self, session: Any, patch: Dict[str, Any]) -> None:
        store = patch.get("store")
        if isinstance(store, str) and store.strip():
            session.store = store.strip()

        stage = patch.get("stage")
        if isinstance(stage, str):
            try:
                session.stage = ConversationStage(stage)
            except Exception:
                pass

        selected = patch.get("selected_menu") or patch.get("selectedMenu")
        if isinstance(selected, str) and selected.strip():
            session.selected_menu = selected.strip()

        qty = patch.get("quantity") or patch.get("qty")
        if isinstance(qty, int) and qty > 0:
            session.quantity = qty

        recos = patch.get("recommendations")
        if isinstance(recos, list):
            session.recommendations = [str(r) for r in recos if isinstance(r, str)]

        profile = patch.get("profile")
        if isinstance(profile, dict):
            session.profile.update(profile)

    # ------------------------------------------------------------------
    def _respond(
        self,
        session: Any,
        raw_reply: str,
        ui: Optional[Dict[str, Any]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        session.remember_agent(raw_reply)
        return {
            "reply": raw_reply,
            "ui": ui or {"store": session.store},
            "actions": actions or [],
            "state": session.as_state(),
        }
