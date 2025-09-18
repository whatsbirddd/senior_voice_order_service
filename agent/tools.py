# tools.py
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import requests

try:
    from voice_mvp.backend import MenuCatalog  # type: ignore[import-not-found]
except ModuleNotFoundError:
    from fastapi_app.menus import MenuCatalog  # type: ignore

# ─────────────────────────────────────────────────────────────
# 실행 환경 공유(카탈로그 인젝션)
# ─────────────────────────────────────────────────────────────
_CURRENT_CATALOG: Optional[MenuCatalog] = None

def set_catalog(catalog: MenuCatalog) -> None:
    """Agent가 초기화 시 주입해 줌."""
    global _CURRENT_CATALOG
    _CURRENT_CATALOG = catalog


# ─────────────────────────────────────────────────────────────
# HTTP 유틸 (간단/보수적으로)
# ─────────────────────────────────────────────────────────────
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36"
)

def _get(url: str, timeout: int = 8) -> Optional[str]:
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=timeout)
        if r.ok and "text/html" in (r.headers.get("Content-Type") or ""):
            r.encoding = r.apparent_encoding  # 한글 보정
            return r.text
    except Exception:
        return None
    return None


# ─────────────────────────────────────────────────────────────
# 1) 리뷰 수집: DuckDuckGo → 네이버/블로그/커뮤니티 링크 모음 → 스니펫 추출
# ─────────────────────────────────────────────────────────────
def reviews(store: str, query: Optional[str] = None, max_results: int = 8,
            fetch_pages: bool = False, menu_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    매장 리뷰/후기/블로그 글을 직접 검색해 스니펫을 모아줍니다.
    네이버 블로그/카페, 지도 설명, 커뮤니티 글 등 공개 웹페이지를 대상으로 DuckDuckGo HTML을 사용합니다.
    일부 사이트는 동적 렌더링/차단으로 전문을 수집하지 못할 수 있습니다.

    TOOL_SPEC={
      "name": "reviews",
      "description": "DuckDuckGo를 사용해 매장 리뷰/후기/블로그 링크와 스니펫을 수집합니다. 필요하면 페이지 본문 일부도 가져옵니다.",
      "parameters": {
        "type": "object",
        "properties": {
          "store": { "type": "string", "description": "매장명(필수)" },
          "query": { "type": "string", "description": "선택 키워드(예: 추천, 부드럽다, 알레르기 등)" },
          "max_results": { "type": "integer", "minimum": 1, "maximum": 20, "default": 8 },
          "fetch_pages": { "type": "boolean", "default": false, "description": "true면 링크 페이지의 본문 일부를 추가로 수집" },
          "menu_names": { "type": "array", "items": {"type":"string"}, "description": "메뉴명 리스트를 주면 언급 탐지" }
        },
        "required": ["store"]
      }
    }
    Returns:
      {
        "summary": str,                # 간단 요약(규칙 기반)
        "highlights": [str, ...],      # 키워드 하이라이트
        "menu_mentions": [{"name":str, "count":int}, ...],
        "sources": [{"title":str, "url":str, "snippet":str}, ...]
      }
    """
    q = f"{store} 리뷰"
    if query:
        q += f" {query}"
    # 네이버 가중치: site: 네이버 블로그/지도/카페 위주
    q += " (site:blog.naver.com OR site:m.place.naver.com OR site:pcmap.place.naver.com OR site:cafe.naver.com)"

    results = _ddg_search(q, max_results=max_results)
    sources = []
    texts = []

    for title, url, snippet in results:
        sources.append({"title": title, "url": url, "snippet": snippet})
        base_text = f"{title}\n{snippet}"
        texts.append(base_text)
        if fetch_pages:
            html = _get(url)
            if html:
                clean = _strip_html(html)[:2000]
                if clean:
                    texts.append(clean)
        time.sleep(0.15)  # 매너 지연

    # 메뉴 언급 세기
    mentions = []
    if menu_names:
        joined = "\n".join(texts).lower()
        for name in menu_names:
            n = name.strip()
            if not n:
                continue
            c = joined.count(n.lower().replace(" ", ""))
            if c > 0:
                mentions.append({"name": n, "count": c})
        mentions.sort(key=lambda x: x["count"], reverse=True)
        mentions = mentions[:10]

    # 요약/하이라이트(아주 단순 규칙 기반)
    corpus = "\n".join(texts)
    highlights = _extract_highlights_ko(corpus)
    summary = _build_summary_from_highlights(store, highlights)

    return {
        "summary": summary,
        "highlights": highlights,
        "menu_mentions": mentions,
        "sources": sources,
    }


def _ddg_search(query: str, max_results: int = 8) -> List[Tuple[str, str, str]]:
    """DuckDuckGo HTML 결과를 파싱해 (title, url, snippet) 리스트를 반환."""
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    html = _get(url)
    if not html:
        return []
    # 매우 보수적인 정규식 파서 (의존성 없이)
    items = re.findall(
        r'<a rel="nofollow" class="result__a" href="([^"]+)".*?>(.*?)</a>.*?<a[^>]+class="result__snippet".*?>(.*?)</a>',
        html, flags=re.S
    )
    out: List[Tuple[str, str, str]] = []
    for u, t, s in items:
        out.append((_unescape(_strip_tags(t)), u, _unescape(_strip_tags(s))))
        if len(out) >= max_results:
            break
    return out


# ─────────────────────────────────────────────────────────────
# 2) 영양 정보 간이 조회: 검색 스니펫에서 kcal/나트륨/당/단백질 수치 추정
# ─────────────────────────────────────────────────────────────
def nutrition(name: str) -> Dict[str, Any]:
    """
    메뉴/제품명으로 kcal/나트륨/당/단백질 수치를 검색 스니펫/페이지에서 추정합니다.
    신뢰도는 낮을 수 있으며, 정확 표는 'unknown'으로 반환합니다.

    TOOL_SPEC={
      "name": "nutrition",
      "description": "메뉴명으로 kcal/sodium/sugar/protein을 추정해 태그(저염/저당/단백질)를 부여합니다.",
      "parameters": {
        "type": "object",
        "properties": { "name": { "type": "string" } },
        "required": ["name"]
      }
    }
    Returns:
      {
        "name": str,
        "kcal": int|null,
        "sodium_mg": int|null,
        "sugar_g": int|null,
        "protein_g": int|null,
        "tags": [str,...]       # ["저염","저당","단백질"] 등 조건부
      }
    """
    q = f"{name} 칼로리 나트륨 당 단백질"
    res = _ddg_search(q, max_results=5)
    blob = " ".join([f"{t} {s}" for t, _, s in res])

    kcal = _first_int(re.findall(r"(\d{2,4})\s*kcal", blob))
    sodium = _first_int(re.findall(r"나트륨\s*([\d,]{2,6})\s*mg", blob))
    sugar = _first_int(re.findall(r"(당류|당)\s*([\d,]{1,4})\s*g", blob))
    protein = _first_int(re.findall(r"(단백질)\s*([\d,]{1,4})\s*g", blob))
    tags = []
    if sodium is not None and sodium <= 700:
        tags.append("저염")
    if sugar is not None and sugar <= 8:
        tags.append("저당")
    if protein is not None and protein >= 15:
        tags.append("단백질")

    return {
        "name": name,
        "kcal": kcal,
        "sodium_mg": sodium,
        "sugar_g": sugar,
        "protein_g": protein,
        "tags": tags,
    }


# ─────────────────────────────────────────────────────────────
# 3) 카탈로그/결제/장소 (로컬)
# ─────────────────────────────────────────────────────────────
def catalog_list(store: str) -> List[Dict[str, Any]]:
    """
    매장의 메뉴 카탈로그를 반환합니다.

    TOOL_SPEC={
      "name": "catalog_list",
      "description": "해당 매장의 전체 메뉴/가격/설명을 반환합니다.",
      "parameters": {
        "type": "object",
        "properties": {"store": {"type": "string"}},
        "required": ["store"]
      }
    }
    Returns: [{"id":str, "name":str, "price":int, "desc":str}, ...]
    """
    if not _CURRENT_CATALOG:
        return []
    return [
        {"id": m.id, "name": m.name, "price": m.price, "desc": getattr(m, "desc", "")}
        for m in _CURRENT_CATALOG.list(store)
    ]


def pay(store: str, names: List[str]) -> Dict[str, Any]:
    """
    선택된 메뉴로 모의 결제 금액을 계산합니다.

    TOOL_SPEC={
      "name": "pay",
      "description": "선택된 메뉴로 금액을 합산해 모의 결제 결과를 반환합니다.",
      "parameters": {
        "type": "object",
        "properties": {
          "store": {"type": "string"},
          "names": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["store", "names"]
      }
    }
    Returns: {"status":"success","amount":int,"items":[{"name":str,"price":int,"quantity":1}]}
    """
    if not _CURRENT_CATALOG:
        return {"status": "success", "amount": 0, "items": []}
    items = []
    amount = 0
    for n in names or []:
        m = _CURRENT_CATALOG.find(store, n)
        if not m:
            continue
        price = int(m.price or 0)
        items.append({"name": m.name, "price": price, "quantity": 1})
        amount += price
    return {"status": "success", "amount": amount, "items": items}


def place(store: str) -> Dict[str, Any]:
    """
    네이버 지도 검색 링크를 반환합니다.

    TOOL_SPEC={
      "name": "place",
      "description": "네이버 지도로 이동 가능한 검색 링크를 반환합니다.",
      "parameters": {
        "type": "object",
        "properties": {"store": {"type": "string"}},
        "required": ["store"]
      }
    }
    Returns: {"mapUrl": "https://map.naver.com/v5/search/<store>"}
    """
    return {"mapUrl": f"https://map.naver.com/v5/search/{quote_plus(store)}"}


# ─────────────────────────────────────────────────────────────
# 4) 추천 집계(reviews + nutrition + catalog)
# ─────────────────────────────────────────────────────────────
# def recommend(store: str, top_n: int = 3, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
#     """
#     리뷰 언급과 간단 영양 태그, 선호/비선호/알레르리를 고려해 상위 N개 추천.

#     TOOL_SPEC={
#       "name": "recommend",
#       "description": "리뷰/영양/프로필(선호·비선호·알레르기)을 고려해 상위 N개 메뉴를 추천합니다.",
#       "parameters": {
#         "type": "object",
#         "properties": {
#           "store": {"type": "string"},
#           "top_n": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
#           "profile": {"type": "object"}
#         },
#         "required": ["store"]
#       }
#     }
#     Returns: {"items": [{"name": str, "reason": str}], "debug": {...}}
#     """
#     if not _CURRENT_CATALOG:
#         return {"items": []}

#     try:
#         prof = profile or {}
#         prefers = {str(x).lower() for x in (prof.get("prefers") or [])}
#         dislikes = {str(x).lower() for x in (prof.get("dislikes") or [])}
#         allergies = {str(x).lower() for x in (prof.get("allergies") or [])}

#         items = _CURRENT_CATALOG.list(store)
#         names = [m.name for m in items]
#         rev = reviews(store=store, menu_names=names, max_results=8, fetch_pages=False)
#         mention_map = {str(x.get("name", "")).replace(" ", "").lower(): int(x.get("count", 0) or 0) for x in (rev.get("menu_mentions") or [])}

#         def score(m) -> float:
#             s = 0.0
#             nm = m.name.replace(" ", "").lower()
#             desc = str(getattr(m, "desc", "")).lower()
#             # review boost
#             s += 0.6 * mention_map.get(nm, 0)
#             # prefers/dislikes
#             if any(p in desc for p in prefers):
#                 s += 0.5
#             if any(d in desc for d in dislikes):
#                 s -= 0.5
#             # allergies block (if mentioned in desc)
#             if any(a in desc for a in allergies):
#                 s -= 2.0
#             return s

#         ranked = sorted(items, key=score, reverse=True)
#         out: List[Dict[str, Any]] = []
#         for m in ranked:
#             if len(out) >= int(top_n or 3):
#                 break
#             nm = m.name
#             desc = str(getattr(m, "desc", ""))
#             mention = mention_map.get(nm.replace(" ", "").lower(), 0)
#             tag = []
#             if prefers and any(p in desc.lower() for p in prefers):
#                 tag.append("선호")
#             if mention:
#                 tag.append(f"리뷰 언급 {mention}회")
#             reason = " · ".join(tag) if tag else (desc[:24] + ("…" if len(desc) > 24 else ""))
#             out.append({"name": nm, "reason": reason})

#         return {"items": out, "debug": {"mentions": mention_map}}
#     except Exception:
#         return {"items": []}

# ─────────────────────────────────────────────────────────────
# LLM 기반 사랑스러운 구어체 추천 (Azure OpenAI) - 문자열 반환
# ─────────────────────────────────────────────────────────────
 
# 업데이트 된 맥도날드 메뉴별 리뷰 (menu 필드 포함)
_MCD_REVIEWS = [
    {"store": "맥도날드", "branch": "강남점", "menu": "빅맥", "rating": 5, "review": "빅맥은 역시 최고입니다! 패티와 소스가 완벽하게 어울려요."},
    {"store": "맥도날드", "branch": "홍대점", "menu": "맥치킨", "rating": 4, "review": "맥치킨이 바삭하고 촉촉해서 맛있었어요. 소스도 잘 어울렸습니다."},
    {"store": "맥도날드", "branch": "신촌점", "menu": "맥너겟", "rating": 3, "review": "맥너겟은 평범한 맛이었지만 소스가 맛있었어요."},
    {"store": "맥도날드", "branch": "잠실점", "menu": "상하이 스파이시 버거", "rating": 5, "review": "상하이 스파이시 버거는 매콤하고 바삭해서 정말 맛있어요!"},
    {"store": "맥도날드", "branch": "구로디지털점", "menu": "슈슈버거", "rating": 2, "review": "슈슈버거는 소스가 너무 달고 제 입맛엔 별로였어요."},
    {"store": "맥도날드", "branch": "서초점", "menu": "불고기버거", "rating": 4, "review": "불고기버거는 달달한 소스와 촉촉한 패티가 잘 어울려요."},
    {"store": "맥도날드", "branch": "종로점", "menu": "에그불고기버거", "rating": 3, "review": "에그불고기버거는 계란이 들어가서 부드럽지만 좀 느끼했어요."},
    {"store": "맥도날드", "branch": "여의도점", "menu": "더블치즈버거", "rating": 5, "review": "더블치즈버거는 치즈가 듬뿍 들어가 정말 진한 맛이에요."},
    {"store": "맥도날드", "branch": "명동점", "menu": "맥스파이시 상하이 디럭스", "rating": 4, "review": "맥스파이시 상하이 디럭스는 매운맛이 적당해서 만족했습니다."},
    {"store": "맥도날드", "branch": "건대입구점", "menu": "치즈스틱", "rating": 5, "review": "치즈스틱은 겉은 바삭하고 속은 쭉 늘어나서 정말 맛있어요."},
    {"store": "맥도날드", "branch": "역삼점", "menu": "감자튀김", "rating": 4, "review": "감자튀김은 항상 바삭하고 짭짤해서 맛있어요."},
    {"store": "맥도날드", "branch": "노원점", "menu": "코울슬로", "rating": 2, "review": "코울슬로는 드레싱이 너무 달고 별로였어요."},
    {"store": "맥도날드", "branch": "합정점", "menu": "아이스크림콘", "rating": 5, "review": "아이스크림콘은 부드럽고 달콤해서 아이들과 먹기 좋아요."},
    {"store": "맥도날드", "branch": "왕십리점", "menu": "해피스낵 치즈버거", "rating": 3, "review": "해피스낵 치즈버거는 크기가 작아서 간식으로 괜찮아요."},
    {"store": "맥도날드", "branch": "신림점", "menu": "애플파이", "rating": 4, "review": "애플파이는 따뜻하고 달콤해서 후식으로 딱입니다."},
    {"store": "맥도날드", "branch": "목동점", "menu": "오레오 맥플러리", "rating": 5, "review": "오레오 맥플러리는 오레오와 아이스크림이 잘 어우러져 정말 맛있어요."},
    {"store": "맥도날드", "branch": "수유점", "menu": "스파이시 맥너겟", "rating": 4, "review": "스파이시 맥너겟은 매콤해서 술안주로도 좋은 것 같아요."},
    {"store": "맥도날드", "branch": "신대방점", "menu": "에그 맥머핀", "rating": 3, "review": "에그 맥머핀은 부드럽지만 빵이 조금 퍽퍽했어요."},
    {"store": "맥도날드", "branch": "대치점", "menu": "더블 쿼터파운더 치즈", "rating": 5, "review": "더블 쿼터파운더 치즈는 두툼한 패티와 치즈가 환상적이에요."},
    {"store": "맥도날드", "branch": "이수점", "menu": "불고기버거", "rating": 4, "review": "불고기버거는 소스가 맛있고 패티가 촉촉해서 자주 먹어요."}
]
 
_USER_MENUS = [
    {"store": "버거킹", "category": "Fastfood", "menu": "와퍼", "user": "김지민"},
    {"store": "롯데리아", "category": "Fastfood", "menu": "새우버거", "user": "박서준"},
    {"store": "KFC", "category": "Fastfood", "menu": "징거버거", "user": "이수빈"},
    {"store": "본죽", "category": "한식", "menu": "전복죽", "user": "김지민"},
    {"store": "한솥도시락", "category": "한식", "menu": "치킨마요", "user": "박서준"},
    {"store": "비빔밥집", "category": "한식", "menu": "소고기비빔밥", "user": "이수빈"},
    {"store": "이탈리안레스토랑", "category": "양식", "menu": "크림파스타", "user": "김지민"},
    {"store": "파스타하우스", "category": "양식", "menu": "토마토파스타", "user": "박서준"},
    {"store": "피자헛", "category": "양식", "menu": "페퍼로니피자", "user": "이수빈"},
    {"store": "파리바게뜨", "category": "베이커리", "menu": "소세지빵", "user": "김지민"},
    {"store": "뚜레쥬르", "category": "베이커리", "menu": "치즈케이크", "user": "박서준"},
    {"store": "샤니", "category": "베이커리", "menu": "단팥빵", "user": "이수빈"},
    {"store": "스타벅스", "category": "카페", "menu": "아이스아메리카노", "user": "김지민"},
    {"store": "이디야커피", "category": "카페", "menu": "연유라떼", "user": "박서준"},
    {"store": "투썸플레이스", "category": "카페", "menu": "카페라떼", "user": "이수빈"},
    {"store": "교촌치킨", "category": "치킨", "menu": "허니콤보", "user": "김지민"},
    {"store": "BBQ", "category": "치킨", "menu": "황금올리브치킨", "user": "박서준"},
    {"store": "네네치킨", "category": "치킨", "menu": "스노윙치킨", "user": "이수빈"},
]
 
def _classify_rating(r: int) -> str:
    if r >= 4:
        return "positive"
    if r <= 2:
        return "negative"
    return "neutral"
 
def _aggregate_reviews(store: str):
    rows = [r for r in _MCD_REVIEWS if r["store"] == store]
    by_menu = {}
    for r in rows:
        m = r["menu"]
        bucket = by_menu.setdefault(m, {"menu": m, "ratings": [], "positive": 0, "neutral": 0, "negative": 0, "samples": []})
        bucket["ratings"].append(r["rating"])
        sent = _classify_rating(r["rating"])
        bucket[sent] += 1
        if len(bucket["samples"]) < 2:
            bucket["samples"].append(r["review"])
    menus = []
    for m, info in by_menu.items():
        avg = sum(info["ratings"]) / len(info["ratings"])
        info["avg_rating"] = round(avg, 2)
        diff = info["positive"] - info["negative"]
        info["score"] = diff * 2 + avg * 0.3
        del info["ratings"]
        menus.append(info)
    menus.sort(key=lambda x: (-x["score"], -x["avg_rating"], -x["positive"]))
    overall = {
        "count": len(rows),
        "positive": sum(1 for r in rows if _classify_rating(r["rating"]) == "positive"),
        "neutral": sum(1 for r in rows if _classify_rating(r["rating"]) == "neutral"),
        "negative": sum(1 for r in rows if _classify_rating(r["rating"]) == "negative"),
        "menus": menus[:20]
    }
    return overall
 
def _fallback_text(store: str, top_items, tone: str = "customer") -> str:
    if not top_items:
        return f"죄송합니다 고객님, 지금은 {store} 메뉴 추천 정보를 불러오지 못했어요. 잠시 후 다시 도와드릴게요."
    parts = []
    for it in top_items:
        menu = it["menu"]
        pos = it["positive"]
        neg = it["negative"]
        avg = it["avg_rating"]
        if pos and not neg:
            reason = "평이 고루 좋아 부담 없이 드시기 좋아 보여요"
        elif pos > neg:
            reason = "좋다는 말씀 비율이 높아서 골라봤어요"
        else:
            reason = "무난한 편이라 편하게 드실 수 있을 것 같아요"
        parts.append(f"{menu}는 별점 {avg}점대에 긍정 {pos}건이라 {reason}")
    body = " / ".join(parts[:3])
    return f"고객님, 제가 살펴본 바로는 {body}. 천천히 골라보실까요?"
 
def recommend(store: str, user: Optional[str] = None, top_n: int = 3,
                  profile: Optional[Dict[str, Any]] = None,
                  model: Optional[str] = None) -> str:
    """
    Azure OpenAI GPT를 사용해 매장 직원이 고객님께 다정하고 세심하게 2~3개 메뉴를 제안하는 문장을 생성합니다.
    (손주가 살뜰히 챙기듯 배려하되 호칭은 항상 '고객님')
    TOOL_SPEC={
      "name": "llm_recommend",
      "description": "사용자 이력(있으면) 또는 리뷰 감성(별점 4이상 긍정, 2이하 부정)을 활용해 직원 톤으로 2~3개 메뉴를 한국어 자연문으로 추천합니다.",
      "parameters": {
        "type": "object",
        "properties": {
          "store": {"type": "string"},
          "user": {"type": "string"},
          "top_n": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
          "profile": {"type": "object"},
          "model": {"type": "string"}
        },
        "required": ["store"]
      }
    }
    Returns: 추천 멘트 문자열
    """
    if not _CURRENT_CATALOG:
        return "고객님, 현재 메뉴 정보를 불러오지 못해 바로 추천을 드리기 어렵습니다. 잠시 후 다시 도와드릴게요."
    try:
        catalog_items = _CURRENT_CATALOG.list(store)
        if not catalog_items:
            return f"고객님, {store} 매장 메뉴가 아직 준비되지 않아 추천이 어려워요."
 
        # 사용자 이력
        user_history = [r for r in _USER_MENUS if user and r.get("user") == user]
 
        # 리뷰 집계 (사용자 이력 없을 때)
        review_agg = _aggregate_reviews(store) if not user_history else None
 
        prof = profile or {}
        prefers = prof.get("prefers") or []
        dislikes = prof.get("dislikes") or []
        allergies = prof.get("allergies") or []
 
        # 컨텍스트 구성
        context = {
            "basis": "user_history" if user_history else "reviews",
            "store": store,
            "requested_top_n": top_n,
            "profile": {
                "prefers": prefers,
                "dislikes": dislikes,
                "allergies": allergies
            }
        }
        if user_history:
            context["user_history"] = user_history
        else:
            context["review_summary"] = review_agg
 
        # 모델 지시
        system_message = {
            "role": "system",
            "content": (
                "역할: 패스트푸드 매장 직원. 고객님께 다정하고 세심하게 메뉴 2~3가지를 권유.\n"
                "톤: '고객님' 호칭, 공손·따뜻·차분. 과한 감탄, 이모지, 해시태그, 명령조, 과장 표현 금지.\n"
                "리뷰 감성 규칙: rating>=4 → 긍정, rating<=2 → 부정. 부정 많은 메뉴는 직접적 비추천 대신 자연스럽게 제외.\n"
                "선정 원칙:\n"
                "1) 긍정 건수와 평균 별점이 높은 메뉴 우선\n"
                "2) 알레르기·비선호 추정 재료(문맥에 포함) 가능성 있으면 조용히 제외하거나 '부담 덜한' 대안 강조\n"
                "3) 2~3개 이내, 230자 이하 하나의 단락.\n"
                "표현 지침:\n"
                "- 이유는 '평이 고르게 좋아', '많이 찾으셔서', '속 편하게 드시기 좋아 보여', '부담 덜하실 것 같아' 등 자연스러운 생활어\n"
                "- 숫자 나열/JSON/불릿/따옴표/목록/괄호 남용 금지\n"
                "- 메뉴명은 그대로 사용, 필요한 경우 1회 정도만 언급\n"
                "- 사랑을 직접 언급 X. 대신 세심한 배려 뉘앙스\n"
                "출력: 조건에 맞는 한 단락 한국어 문장만."
            )
        }
 
        user_message = {
            "role": "user",
            "content": "컨텍스트:\n" + json.dumps(context, ensure_ascii=False)
        }
 
        messages = [system_message, user_message]
 
        # Azure 호출
        try:
            from openai import AzureOpenAI  # type: ignore
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            azure_key = os.getenv("AZURE_OPENAI_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            deployment = model or os.getenv("AZURE_OPENAI_DEPLOYMENT") or "gpt-4o-mini"
            client = AzureOpenAI(
                api_key=azure_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint,
            )
            resp = client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=0.4,
                max_tokens=420,
                top_p=0.9,
            )
            text = (resp.choices[0].message.content or "").strip()
            # 형식 방어: JSON/목록/기호 제거
            if text.startswith("{") or text.startswith("["):
                text = re.sub(r"[{}\[\]]", " ", text)
            text = re.sub(r"(?:^[-•\d\)\.]+\s*)", "", text)  # 리스트 기호 제거
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 10:
                raise ValueError("empty response")
            return text
        except Exception:
            # Fallback: 상위 메뉴 계산
            if review_agg:
                top = review_agg["menus"][:top_n]
            else:
                top = []
            return _fallback_text(store, top[:top_n])
    except Exception:
        return "고객님, 지금은 추천 문장을 생성하는 중 문제가 발생했어요. 잠시 후 다시 시도해 보겠습니다."
  


# ─────────────────────────────────────────────────────────────
# Docstring → OpenAI tools 스키마/설명 텍스트 생성
# ─────────────────────────────────────────────────────────────
def discover_tools() -> Tuple[List[Dict[str, Any]], Dict[str, Any], str]:
    """
    이 모듈 내 함수들의 docstring에서 TOOL_SPEC(JSON)을 추출해
    (1) OpenAI function-calling tools 스키마
    (2) name→callable 맵
    (3) 프롬프트에 넣을 간단한 목록 텍스트
    를 반환한다.
    """
    import inspect
    import sys
    import importlib
    schemas: List[Dict[str, Any]] = []
    mapping: Dict[str, Any] = {}
    lines: List[str] = []

    # IMPORTANT: __import__(pkg.sub) returns the top-level pkg. Use the actual module object.
    module = sys.modules.get(__name__) or importlib.import_module(__name__)
    for name, obj in inspect.getmembers(module):
        if not inspect.isfunction(obj):
            continue
        spec = _extract_spec(obj.__doc__)
        if not spec:
            continue
        # 스키마
        schemas.append({"type": "function", "function": spec})
        mapping[spec["name"]] = obj
        # 텍스트
        desc = spec.get("description") or ""
        params = ", ".join(list((spec.get("parameters") or {}).get("properties", {}).keys()))
        lines.append(f"- {spec['name']}({params}): {desc}")

    return schemas, mapping, "\n".join(lines)


def _extract_spec(doc: Optional[str]) -> Optional[Dict[str, Any]]:
    """Extract a JSON object assigned to TOOL_SPEC from a docstring.

    The JSON may contain nested braces. This function finds the first '{' after
    'TOOL_SPEC=' and returns the balanced JSON segment.
    """
    if not doc:
        return None
    idx = doc.find('TOOL_SPEC')
    if idx < 0:
        return None
    # find the opening brace after TOOL_SPEC=
    brace_start = doc.find('{', idx)
    if brace_start < 0:
        return None
    i = brace_start
    depth = 0
    in_string = False
    quote = ''
    escape = False
    end = -1
    while i < len(doc):
        ch = doc[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        i += 1
    if end == -1:
        return None
    blob = doc[brace_start:end]
    try:
        return json.loads(blob)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# 텍스트 처리 보조
# ─────────────────────────────────────────────────────────────
_tag_re = re.compile(r"<[^>]+>")
_ws_re = re.compile(r"\s+")

def _strip_tags(x: str) -> str:
    return _tag_re.sub(" ", x)

def _unescape(x: str) -> str:
    return (
        x.replace("&amp;", "&")
         .replace("&lt;", "<")
         .replace("&gt;", ">")
         .replace("&quot;", '"')
         .replace("&#39;", "'")
    )

def _strip_html(html: str) -> str:
    return _ws_re.sub(" ", _strip_tags(html)).strip()

def _first_int(groups: List[str]) -> Optional[int]:
    for g in groups:
        try:
            return int(g.replace(",", ""))
        except Exception:
            continue
    return None

_HIGHLIGHT_PATTERNS = [
    (r"친절|서비스", "친절한 서비스"),
    (r"부드럽|연하다", "부드러운 식감"),
    (r"가성비|가격", "가격 만족"),
    (r"신선|야채", "야채 신선"),
    (r"대기|줄|혼잡", "대기 있을 수 있음"),
    (r"맵다|매콤|자극", "자극 있는 맛"),
    (r"깔끔|청결", "매장 깔끔"),
]

def _extract_highlights_ko(corpus: str) -> List[str]:
    corpus = corpus or ""
    found: List[str] = []
    for pat, label in _HIGHLIGHT_PATTERNS:
        if re.search(pat, corpus):
            found.append(label)
    return found[:6]

def _build_summary_from_highlights(store: str, hl: List[str]) -> str:
    if not hl:
        return f"{store}에 대한 후기가 여럿 있습니다. 메뉴 추천을 받아보실래요?"
    if len(hl) == 1:
        return f"리뷰에 따르면 {hl[0]}이라는 의견이 많아요."
    return f"리뷰에 따르면 {', '.join(hl[:2])}이라는 의견이 많아요."
