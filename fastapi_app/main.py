from __future__ import annotations

import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ensure local imports work when running as a module
import sys
sys.path.append(str(Path(__file__).parent.parent))

from agent import VoiceOrderAgent, build_agent
from fastapi_app.speech import AzureSpeechService
from fastapi_app.menus import MenuItem
from agent.llm_openai import AzureAudioTranscriber
from agent.user_profile import SingleUserProfileStore

app = FastAPI(title="Senior Voice Agent API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent: VoiceOrderAgent = build_agent()
catalog = agent.catalog
single_user = SingleUserProfileStore(Path(__file__).resolve().parents[1] / "data" / "user_profile.json")
speech_service = AzureSpeechService()
transcriber = AzureAudioTranscriber()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class MenuItemPayload(BaseModel):
    name: str
    description: str = ""
    price: int = 0
    image: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    allergens: List[str] = Field(default_factory=list)

    def to_domain(self) -> MenuItem:
        return MenuItem(
            name=self.name,
            desc=self.description,
            price=self.price,
            image=self.image,
            tags=self.tags,
            allergens=self.allergens,
        )


class MenuImportBody(BaseModel):
    store: str
    menu: List[MenuItemPayload]
    featured: Optional[MenuItemPayload] = None


class UserProfile(BaseModel):
    sessionId: str
    ageGroup: Optional[str] = None
    allergies: List[str] = Field(default_factory=list)
    diseases: List[str] = Field(default_factory=list)
    prefers: List[str] = Field(default_factory=list)
    dislikes: List[str] = Field(default_factory=list)


class AgentChatRequest(BaseModel):
    sessionId: str
    message: str
    store: Optional[str] = None
    selectedNames: List[str] = Field(default_factory=list)
    profile: Optional[UserProfile] = None
    userId: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fallback_menu(store: str) -> List[MenuItem]:
    base = [
        MenuItem(name="부드러운 불고기 정식", desc="고기가 부드럽고 짜지 않아 어르신들이 좋아하시는 메뉴", price=15000, tags=["식사"]),
        MenuItem(name="담백한 생선구이", desc="비리지 않고 살이 부드러운 생선구이", price=16000, tags=["식사"]),
        MenuItem(name="속 편한 된장찌개", desc="짜지 않고 구수한 국물", price=12000, tags=["국"]),
    ]
    for item in base:
        item.desc = f"{store}에서 인기 있는 {item.desc}"
    return base


def _menu_response(store: str) -> Dict[str, Any]:
    menu_items = catalog.list(store) if catalog else []
    source = "imported" if menu_items else "fallback"
    if not menu_items:
        menu_items = _fallback_menu(store)
    featured = catalog.featured(store) if catalog else (menu_items[0] if menu_items else None)
    return {
        "store": store,
        "source": source,
        "menu": [item.to_api() if hasattr(item, 'to_api') else {
            "name": getattr(item, 'name', None),
            "description": getattr(item, 'desc', ''),
            "price": getattr(item, 'price', 0),
        } for item in menu_items],
        **({"featured": featured.to_api()} if featured else {}),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


@app.post("/profile/upsert")
def upsert_profile(profile: UserProfile) -> Dict[str, Any]:
    agent.memory.update(profile.sessionId, {"profile": profile.dict(exclude_none=True)})
    return {"ok": True}


# ---------------- User profile/history endpoints ----------------
@app.post("/user/profile/upsert")
def user_profile_upsert(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    patch = payload.get("profile") or payload or {}
    rec = single_user.upsert_profile(patch)
    return {"ok": True, "user": rec.to_dict()}


@app.get("/user/profile")
def user_profile_get() -> Dict[str, Any]:
    rec = single_user.get()
    return rec.to_dict()


@app.get("/user/history")
def user_history_get() -> Dict[str, Any]:
    return {"history": single_user.history()}


@app.get("/api/menu")
def get_menu(store: str) -> Dict[str, Any]:
    return _menu_response(store)


@app.post("/api/menu/import")
def import_menu(body: MenuImportBody) -> Dict[str, Any]:
    if not body.menu:
        raise HTTPException(status_code=400, detail="menu list required")
    catalog.upsert(
        store=body.store,
        menu=[item.to_domain() for item in body.menu],
        featured=body.featured.to_domain() if body.featured else None,
    )
    return {
        "ok": True,
        "store": body.store,
        "count": len(body.menu),
        "featured": catalog.featured(body.store).to_api() if catalog.featured(body.store) else None,
    }


@app.get("/api/reviews")
def get_reviews(store: str) -> Dict[str, Any]:
    # Simplified: no external review service
    return {"store": store, "summary": "리뷰 서비스 비활성화", "highlights": []}



@app.post("/api/pay")
def mock_pay(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    items = payload.get("items") or []
    amount = 0
    normalized_items = []
    for item in items:
        price = int(item.get("price", 0) or 0)
        qty = int(item.get("quantity", 1) or 1)
        amount += price * qty
        normalized_items.append({
            "name": item.get("name"),
            "price": price,
            "quantity": qty,
        })
    return {
        "status": "success",
        "provider": "SamsungPay",
        "amount": amount,
        "items": normalized_items,
        "message": "모의 결제 완료",
    }


@app.post("/agent/chat")
def agent_chat(req: AgentChatRequest) -> Dict[str, Any]:
    # merge profile: stored + request
    merged_profile: Optional[Dict[str, Any]] = None
    # merge single-user stored profile
    rec = single_user.get()
    merged_profile = dict(rec.profile)
    try:
        # include recent history so the agent tools can read it
        merged_profile["history"] = single_user.history()
    except Exception:
        pass
    if req.profile:
        patch = req.profile.dict(exclude_none=True)
        merged_profile = {**(merged_profile or {}), **patch}
    response = agent.handle(
        session_id=req.sessionId,
        message=req.message,
        store=req.store,
        selected_names=req.selectedNames,
        profile=merged_profile,
    )
    print(f"[agent_chat] session={req.sessionId} message={req.message} response={response}")
    # record order in history when ORDER action present
    try:
        if any(a.get("type") == "ORDER" for a in (response.get("actions") or [])):
            session = agent.memory.get_session(req.sessionId)
            if session.selected_menu and session.store:
                qty = session.quantity or 1
                single_user.add_order(store=session.store, item=session.selected_menu, quantity=qty)
    except Exception:
        pass
    return response


@app.post("/api/agent")
def agent_chat_legacy(req: AgentChatRequest) -> Dict[str, Any]:
    """Backward compatible endpoint consumed by the existing UI proxy."""
    return agent_chat(req)


@app.post("/api/samsung-pay")
def samsung_pay(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    required = ["items", "total_amount", "store_name"]
    for field in required:
        if field not in payload:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    payment_id = f"SP_{int(time.time())}_{random.randint(1000, 9999)}"
    transaction_id = f"TXN_{random.randint(100000, 999999)}"
    receipt_number = f"RCP_{random.randint(100000, 999999)}"
    order_number = payload.get("order_number") or f"ORD_{random.randint(10000, 99999)}"
    return {
        "success": True,
        "payment_result": {
            "success": True,
            "payment_id": payment_id,
            "transaction_id": transaction_id,
            "amount": payload["total_amount"],
            "currency": "KRW",
            "payment_method": "Samsung Pay",
            "order_info": {
                "items": payload["items"],
                "order_number": order_number,
                "order_time": datetime.utcnow().isoformat() + "Z",
            },
            "receipt": {
                "receipt_number": receipt_number,
                "receipt_url": f"https://receipt.samsung.com/{receipt_number}",
            },
            "message": "결제가 성공적으로 완료되었습니다.",
        },
    }


@app.post("/api/audio/transcribe")
async def audio_transcribe(file: UploadFile = File(...)) -> Dict[str, Any]:
    data = await file.read()
    if speech_service.available:
        speech_result = speech_service.transcribe(data)
        if speech_result.error:
            raise HTTPException(status_code=502, detail=speech_result.error)
        return {"text": speech_result.text, "raw": speech_result.raw}
    if transcriber.available:
        result = transcriber.transcribe(
            audio=data,
            filename=file.filename or "audio.wav",
            mime_type=file.content_type or "audio/wav",
        )
        if result.get("error"):
            raise HTTPException(status_code=502, detail=result["error"])
        return {
            "text": result.get("text"),
            "raw": result.get("raw"),
        }
    raise HTTPException(status_code=503, detail="Audio transcription not configured")


# Entry for local dev
# uvicorn voice_mvp.fastapi_app.main:app --reload --port 8000
