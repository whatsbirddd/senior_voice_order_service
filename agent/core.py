from typing import Dict, Any, List


class Agent:
    def __init__(self, prompt: str, tools: Dict[str, Any], memory):
        self.prompt = prompt
        self.tools = tools  # name -> Tool
        self.enabled_tools = set(tools.keys())
        self.memory = memory

    def set_prompt(self, prompt: str):
        self.prompt = prompt

    def set_enabled_tools(self, tool_names: List[str]):
        names = set(tool_names)
        self.enabled_tools = {n for n in names if n in self.tools}

    def get_config(self):
        return {
            "prompt": self.prompt,
            "enabledTools": sorted(list(self.enabled_tools)),
            "availableTools": sorted(list(self.tools.keys())),
        }

    def _tool(self, name):
        if name in self.enabled_tools:
            return self.tools[name]
        return None

    def run(self, session_id: str, message: str, ctx: Dict[str, Any]):
        # Memory binding
        mem = self.memory.get(session_id)
        store = (ctx.get("store") or mem.get("store") or "").strip()
        history = ctx.get("history") or mem.get("history") or []
        selected_names = ctx.get("selectedNames") or []

        tnorm = (message or "").replace(" ", "").lower()
        reply_parts = []
        ui: Dict[str, Any] = {}
        did_any = False

        # crude store extraction
        if not store and any(k in tnorm for k in ["리뷰", "후기", "메뉴", "지도", "결제", "추천", "설명"]):
            guess = message
            for kw in ["리뷰", "후기", "알려줘", "보여줘", "메뉴", "추천", "설명", "지도", "위치", "열어줘", "결제", "주문", "시켜줘"]:
                guess = guess.replace(kw, "")
            store = guess.strip() or store

        # Reviews
        if ("리뷰" in tnorm) or ("후기" in tnorm):
            tool = self._tool("reviews")
            if not store:
                reply_parts.append("가게 이름을 알려주시면 리뷰를 요약해 드릴게요.")
            elif tool:
                out = tool.func(store)
                ui.update(out)
                reply_parts.append(out.get("summary", ""))
                did_any = True

        # Menu explore
        if ("메뉴" in tnorm) and not ("추천" in tnorm):
            tool = self._tool("menu")
            if not store:
                reply_parts.append("어느 가게의 메뉴를 볼까요?")
            elif tool:
                out = tool.func(store)
                ui.update({"menu": out})
                reply_parts.append(f"{store}의 인기 메뉴를 보여드릴게요.")
                did_any = True

        # Recommend
        if ("추천" in tnorm) and ("메뉴" in tnorm or "뭐먹" in tnorm):
            tool_reco = self._tool("recommend")
            tool_menu = self._tool("menu")
            tool_rev = self._tool("reviews")
            suggested = []
            if tool_reco:
                suggested = tool_reco.func(history)
            # Try to bias by reviews mentioning menu names
            picked = None
            if store and tool_menu and tool_rev:
                menu_list = tool_menu.func(store)
                rev = tool_rev.func(store)
                text = " ".join((rev.get("summary") or "", " ".join(rev.get("reviews") or [])))
                for m in menu_list:
                    name = m.get("name") or ""
                    if name and (name.replace(" ", "") in text.replace(" ", "")):
                        picked = name
                        break
                if not picked and menu_list:
                    picked = (menu_list[0].get("name") or None)
            if picked and picked not in suggested:
                suggested = [picked] + suggested
            ui.update({"recommendations": suggested})
            reply_parts.append(f"{', '.join(suggested[:2])} 메뉴를 추천드립니다.")
            did_any = True

        # Explain menu if name appears
        if ("설명" in tnorm) or ("어떤" in tnorm and "메뉴" in tnorm):
            tool_menu = self._tool("menu")
            menu_names = ["시그니처 메뉴", "셰프 추천", "가벼운 메뉴"]
            target = None
            for name in menu_names:
                if name.replace(" ", "").lower() in tnorm:
                    target = name; break
            if store and target and tool_menu:
                menu = tool_menu.func(store)
                item = next((m for m in menu if m["name"] == target), None)
                if item:
                    ui.setdefault("menu", menu)
                    reply_parts.append(f"{item['name']}은/는 {item['desc']} 가격은 {item['price']}원입니다.")
                    did_any = True

        # Map
        if ("지도" in tnorm) or ("위치" in tnorm) or ("네이버지도" in tnorm):
            tool = self._tool("place")
            if store and tool:
                ui.update(tool.func(store))
                reply_parts.append("네이버 지도를 열어드릴게요.")
                did_any = True
            else:
                reply_parts.append("가게 이름을 알려주시면 지도를 열어 드려요.")

        # Payment
        if ("결제" in tnorm) or ("주문" in tnorm):
            tool = self._tool("pay")
            if not store:
                reply_parts.append("어떤 가게에서 결제할지 알려주세요.")
            elif tool:
                pay = tool.func(store, selected_names)
                ui.update({"payment": pay})
                reply_parts.append(f"총 {pay['amount']}원 결제되었습니다. 모의 결제에요.")
                did_any = True

        # Fallback
        if not did_any:
            if not store:
                reply_parts.append("가게 이름과 함께 '리뷰 알려줘', '메뉴 추천'처럼 말씀해 보세요.")
            else:
                reply_parts.append(f"{store}에 대해 리뷰 요약, 메뉴 추천, 지도, 결제 등 무엇을 도와드릴까요?")

        # Update memory
        new_state = {"store": store}
        self.memory.append_history(session_id, "user", message)
        self.memory.update(session_id, new_state)

        return {
            "reply": " ".join(reply_parts) if reply_parts else "요청을 이해하지 못했어요. 다시 말씀해 주실래요?",
            "ui": ui,
            "state": new_state,
        }
