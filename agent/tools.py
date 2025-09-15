from typing import List, Dict, Any, Callable


class Tool:
    def __init__(self, name: str, description: str, func: Callable[..., Any]):
        self.name = name
        self.description = description
        self.func = func


def build_default_tools():
    def mock_menu(store: str) -> List[Dict[str, Any]]:
        return [
            {"name": "시그니처 메뉴", "desc": f"{store}의 대표 메뉴. 가장 인기 많음.", "price": 15000},
            {"name": "셰프 추천", "desc": "재료 상태 좋은 날 제공되는 추천 요리.", "price": 18000},
            {"name": "가벼운 메뉴", "desc": "가볍게 즐길 수 있는 메뉴.", "price": 9000},
        ]

    def mock_reviews(store: str):
        reviews = [
            f"{store} 분위기가 좋아요. 직원들이 친절하고 재방문의사 있어요.",
            f"{store} 대표 메뉴가 특히 맛있었어요. 가격 대비 만족!",
            f"대기 시간이 조금 있었지만 전반적으로 만족스러웠습니다.",
        ]
        summary = (
            f"{store}는 친절한 서비스와 분위기가 좋다는 후기가 많고, 대표 메뉴의 맛과 가성비가 호평입니다. 다만 대기 시간이 있을 수 있어요."
        )
        return {"reviews": reviews, "summary": summary}

    def recommend_from_history(history: List[Dict[str, Any]]):
        suggested = []
        for h in (history or [])[-5:]:
            liked = h.get("likedMenu") or h.get("menu")
            if liked and liked not in suggested:
                suggested.append(liked)
        if not suggested:
            suggested = ["시그니처 메뉴", "셰프 추천"]
        return suggested

    def place_map(store: str):
        return {"mapUrl": f"https://map.naver.com/v5/search/{store}"}

    def mock_pay(store: str, selected_names: List[str]):
        menu = mock_menu(store)
        items = [m for m in menu if m["name"] in (selected_names or [])] or [menu[0]]
        amount = sum(i["price"] for i in items)
        return {"status": "success", "amount": amount, "items": items}

    return {
        "reviews": Tool("reviews", "가게 리뷰 요약", lambda store: mock_reviews(store)),
        "menu": Tool("menu", "가게 메뉴 조회", lambda store: mock_menu(store)),
        "recommend": Tool("recommend", "히스토리 기반 메뉴 추천", lambda history: recommend_from_history(history)),
        "place": Tool("place", "네이버 지도 검색 링크", lambda store: place_map(store)),
        "pay": Tool("pay", "결제 모의", lambda store, names: mock_pay(store, names)),
    }

