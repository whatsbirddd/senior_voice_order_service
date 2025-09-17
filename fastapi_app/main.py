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

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _load_env_file() -> None:
    if not _ENV_PATH.exists():
        return
    try:
        for raw in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key and key not in os.environ:
                os.environ[key.strip()] = value.strip()
    except Exception:
        pass


_load_env_file()

try:  # Allow running both as package and as flat module
    from voice_mvp.agent import VoiceOrderAgent, build_agent  # type: ignore[import-not-found]
    from voice_mvp.backend import AzureSpeechService, MenuItem  # type: ignore[import-not-found]
    from voice_mvp.agent.llm_openai import AzureAudioTranscriber  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - fallback for local scripts
    from agent import VoiceOrderAgent, build_agent
    from backend import AzureSpeechService, MenuItem
    from agent.llm_openai import AzureAudioTranscriber


app = FastAPI(title="Senior Voice Agent API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent: VoiceOrderAgent = build_agent()
catalog = agent.catalog
reviews = agent.reviews
recommender = agent.recommender
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
    menu_items = catalog.list(store)
    source = "imported"
    if not menu_items:
        menu_items = _fallback_menu(store)
        source = "fallback"
    featured = catalog.featured(store)
    if not featured and menu_items:
        featured = menu_items[0]
    payload = {
        "store": store,
        "source": source,
        "menu": [item.to_api() for item in menu_items],
    }
    if featured:
        payload["featured"] = featured.to_api()
    return payload


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
    bundle = reviews.get(store)
    return bundle.to_api()


@app.post("/api/recommend")
def recommend_menu(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    store = str(payload.get("store", "")).strip()
    if not store:
        raise HTTPException(status_code=400, detail="store is required")
    profile = payload.get("profile") or {}
    recos = recommender.recommend(store, profile)
    return {
        "store": store,
        "suggested": [item.to_api() for item in recos],
    }


@app.get("/api/place")
def get_place(store: str) -> Dict[str, Any]:
    url = f"https://map.naver.com/v5/search/{store}"
    return {"store": store, "mapUrl": url}


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
    profile_dict = req.profile.dict(exclude_none=True) if req.profile else None
    response = agent.handle(
        session_id=req.sessionId,
        message=req.message,
        store=req.store,
        selected_names=req.selectedNames,
        profile=profile_dict,
    )
    return response


@app.post("/api/agent")
def agent_chat_legacy(req: AgentChatRequest) -> Dict[str, Any]:
    """Backward compatible endpoint consumed by the existing UI proxy."""
    return agent_chat(req)


@app.post("/api/search-menu")
def search_menu(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    store = payload.get("store_name") or payload.get("store") or "가게"
    query = payload.get("query", "")
    recos = recommender.recommend(store, payload.get("profile")) or _fallback_menu(store)
    return {
        "store_name": store,
        "query": query,
        "recommendations": [item.to_api() for item in recos],
    }


@app.post("/api/naver-menu-info")
def naver_menu_info(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    menu_name = str(payload.get("menu_name", "")).strip()
    store = str(payload.get("store_name") or payload.get("store") or "").strip() or "매장"
    if not menu_name:
        raise HTTPException(status_code=400, detail="menu_name is required")
    item = None
    if store:
        item = catalog.find(store, menu_name)
    description = item.desc if item else f"{menu_name}은 깔끔하게 조리되어 부담 없이 드시기 좋습니다."
    price = item.price if item else 0
    return {
        "success": True,
        "menu_info": {
            "menu_name": menu_name,
            "store_name": store,
            "description": description,
            "price": f"{price:,}원" if price else "문의 바랍니다",
            "reviews": reviews.get(store).reviews if store else [],
        },
    }


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


@app.post("/api/generate-qr")
def generate_qr(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    order_number = payload.get("order_number") or f"ORD_{random.randint(10000, 99999)}"
    expires = datetime.utcnow() + timedelta(minutes=10)
    return {
        "success": True,
        "qr_data": {
            "qr_code_url": f"https://qr.samsung.com/order/{order_number}",
            "qr_code_data": f"samsung-pay://order/{order_number}",
            "order_number": order_number,
            "expires_at": expires.isoformat() + "Z",
            "instructions": [
                "삼성페이 앱을 열고",
                "화면 아래 QR 버튼을 누른 뒤",
                "QR 코드를 스캔하면 결제 화면이 열립니다.",
            ],
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
