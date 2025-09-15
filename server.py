import os
from flask import Flask, send_from_directory, jsonify, request, redirect
from datetime import datetime
from agent import build_agent


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    agent = build_agent()

    # In-memory store for imported menus and images: { store_name: [ {name, desc, price, image} ] }
    MENUS = {}
    MENUS_FEATURED = {}

    # Config
    app.config["USE_MOCK"] = os.getenv("USE_MOCK", "true").lower() == "true"

    @app.route("/")
    def index():
        # Serve the static UI by default; opt-in to Next with USE_NEXT=true
        if os.getenv("USE_NEXT", "false").lower() == "true":
            next_base = os.getenv("NEXT_BASE", "http://localhost:3000")
            return redirect(next_base, code=302)
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/health")
    def health():
        return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}

    # --- Mock/Search Endpoints ---
    @app.get("/api/reviews")
    def api_reviews():
        store = request.args.get("store", "").strip()
        if not store:
            return jsonify({"error": "store is required"}), 400

        # For MVP: return mock data; replace with real search + summarization
        sample_reviews = [
            f"{store} 분위기가 좋아요. 직원들이 친절하고 재방문의사 있어요.",
            f"{store} 대표 메뉴가 특히 맛있었어요. 가격 대비 만족!",
            f"대기 시간이 조금 있었지만 전반적으로 만족스러웠습니다.",
        ]
        summary = (
            f"{store}는 친절한 서비스와 분위기가 좋다는 후기가 많고, "
            f"대표 메뉴의 맛과 가성비가 호평입니다. 다만 대기 시간이 있을 수 있어요."
        )
        return jsonify({"store": store, "reviews": sample_reviews, "summary": summary})

    @app.get("/api/menu")
    def api_menu():
        store = request.args.get("store", "").strip()
        # Prefer imported menu if available
        if store and store in MENUS and MENUS[store]:
            payload = {"store": store, "menu": MENUS[store], "source": "imported"}
            feat = MENUS_FEATURED.get(store)
            if isinstance(feat, dict) and feat.get("name"):
                payload["featured"] = feat
            return jsonify(payload)
        # Fallback synthetic menu
        menu = [
            {"name": "시그니처 메뉴", "desc": f"{store}의 대표 메뉴. 가장 인기 많음.", "price": 15000, "image": None},
            {"name": "셰프 추천", "desc": "재료 상태 좋은 날 제공되는 추천 요리.", "price": 18000, "image": None},
            {"name": "가벼운 메뉴", "desc": "가볍게 즐길 수 있는 메뉴.", "price": 9000, "image": None},
        ]
        return jsonify({"store": store, "menu": menu})

    @app.post("/api/menu/import")
    def api_menu_import():
        data = request.get_json(silent=True) or {}
        store = (data.get("store") or "").strip()
        items = data.get("menu") or []
        featured = data.get("featured") or None
        if not store or not isinstance(items, list) or not items:
            return jsonify({"error": "store and non-empty menu list required"}), 400
        # Normalize items
        norm = []
        for it in items:
            norm.append({
                "name": it.get("name"),
                "desc": it.get("desc") or it.get("description"),
                "price": it.get("price") or 0,
                "image": it.get("image") or it.get("img") or None,
            })
        MENUS[store] = norm
        # Featured selection: use provided featured or first item
        if isinstance(featured, dict) and featured.get("name"):
            MENUS_FEATURED[store] = {
                "name": featured.get("name"),
                "desc": featured.get("desc") or featured.get("description"),
                "price": featured.get("price") or 0,
                "image": featured.get("image") or featured.get("img") or None,
            }
        else:
            first = norm[0]
            MENUS_FEATURED[store] = first
        return jsonify({"ok": True, "store": store, "count": len(norm), "featured": MENUS_FEATURED.get(store)})

    @app.post("/api/recommend")
    def api_recommend():
        data = request.get_json(silent=True) or {}
        store = (data.get("store") or "").strip()
        history = data.get("history") or []  # list of {store, likedMenu}
        # MVP heuristic: if user liked something with same keyword, suggest it
        suggested = []
        for h in history[-5:]:
            liked = h.get("likedMenu")
            if liked and liked not in suggested:
                suggested.append(liked)
        if not suggested:
            suggested = ["시그니처 메뉴", "셰프 추천"]
        return jsonify({"store": store, "suggested": suggested})

    @app.get("/api/place")
    def api_place():
        store = request.args.get("store", "").strip()
        # Without API keys, provide a link to Naver Map search
        naver_search_url = f"https://map.naver.com/v5/search/{store}"
        return jsonify({
            "store": store,
            "mapUrl": naver_search_url,
            "note": "For MVP, open the map link. Embed may be blocked by X-Frame-Options."
        })

    @app.post("/api/pay")
    def api_pay():
        data = request.get_json(silent=True) or {}
        store = data.get("store")
        items = data.get("items", [])
        amount = sum(item.get("price", 0) for item in items)
        # Mock Samsung Pay handoff result
        return jsonify({
            "status": "success",
            "provider": "SamsungPay",
            "amount": amount,
            "store": store,
            "message": "모의 결제 성공"
        })

    # --- Agent management ---
    @app.get("/api/agent/config")
    def api_agent_config_get():
        return jsonify(agent.get_config())

    @app.post("/api/agent/config")
    def api_agent_config_set():
        data = request.get_json(silent=True) or {}
        if "prompt" in data:
            agent.set_prompt(str(data["prompt"]))
        if "enabledTools" in data and isinstance(data["enabledTools"], list):
            agent.set_enabled_tools(data["enabledTools"])
        return jsonify(agent.get_config())

    @app.get("/api/agent/memory")
    def api_agent_memory_get():
        session_id = request.args.get("sessionId", "default")
        return jsonify(agent.memory.get(session_id))

    @app.post("/api/agent/memory/clear")
    def api_agent_memory_clear():
        data = request.get_json(silent=True) or {}
        session_id = data.get("sessionId", "default")
        agent.memory.clear(session_id)
        return jsonify({"ok": True})

    # --- Agent endpoint: understand user intent and act without clicks ---
    def _mock_menu(store: str):
        if store and store in MENUS and MENUS[store]:
            return MENUS[store]
        return [
            {"name": "시그니처 메뉴", "desc": f"{store}의 대표 메뉴. 가장 인기 많음.", "price": 15000, "image": None},
            {"name": "셰프 추천", "desc": "재료 상태 좋은 날 제공되는 추천 요리.", "price": 18000, "image": None},
            {"name": "가벼운 메뉴", "desc": "가볍게 즐길 수 있는 메뉴.", "price": 9000, "image": None},
        ]

    def _mock_reviews(store: str):
        reviews = [
            f"{store} 분위기가 좋아요. 직원들이 친절하고 재방문의사 있어요.",
            f"{store} 대표 메뉴가 특히 맛있었어요. 가격 대비 만족!",
            f"대기 시간이 조금 있었지만 전반적으로 만족스러웠습니다.",
        ]
        summary = (
            f"{store}는 친절한 서비스와 분위기가 좋다는 후기가 많고, 대표 메뉴의 맛과 가성비가 호평입니다. 다만 대기 시간이 있을 수 있어요."
        )
        return reviews, summary

    def _heuristic_recommend(history):
        suggested = []
        for h in (history or [])[-5:]:
            liked = h.get("likedMenu")
            if liked and liked not in suggested:
                suggested.append(liked)
        if not suggested:
            suggested = ["시그니처 메뉴", "셰프 추천"]
        return suggested

    @app.post("/api/agent")
    def api_agent():
        data = request.get_json(silent=True) or {}
        text = (data.get("message") or "").strip()
        store = (data.get("store") or "").strip()
        history = data.get("history") or []
        selected_names = data.get("selectedNames") or []

        if not text:
            return jsonify({"reply": "무엇을 도와드릴까요? 가게 이름이나 원하는 작업을 말씀해 주세요."})

        tnorm = text.replace(" ", "").lower()
        ui = {}
        reply_parts = []
        did_any = False

        # Try crude store extraction if missing and keywords present
        if not store and any(k in tnorm for k in ["리뷰", "후기", "메뉴", "지도", "결제", "추천", "설명"]):
            guess = text
            for kw in ["리뷰", "후기", "알려줘", "보여줘", "메뉴", "추천", "설명", "지도", "위치", "열어줘", "결제", "주문", "시켜줘"]:
                guess = guess.replace(kw, "")
            store = guess.strip() or store

        # Reviews
        if ("리뷰" in tnorm) or ("후기" in tnorm):
            if not store:
                reply_parts.append("가게 이름을 알려주시면 리뷰를 요약해 드릴게요.")
            else:
                reviews, summary = _mock_reviews(store)
                ui.update({"reviews": reviews, "summary": summary})
                reply_parts.append(summary)
                did_any = True

        # Menu explore
        if ("메뉴" in tnorm) and not ("추천" in tnorm):
            if not store:
                reply_parts.append("어느 가게의 메뉴를 볼까요?")
            else:
                menu = _mock_menu(store)
                ui.update({"menu": menu})
                reply_parts.append(f"{store}의 인기 메뉴를 보여드릴게요.")
                did_any = True

        # Recommend
        if ("추천" in tnorm) and ("메뉴" in tnorm or "뭐먹" in tnorm):
            suggested = _heuristic_recommend(history)
            ui.update({"recommendations": suggested})
            reply_parts.append(f"{', '.join(suggested)} 메뉴를 추천드립니다.")
            did_any = True

        # Explain menu if name appears
        if ("설명" in tnorm) or ("어떤" in tnorm and "메뉴" in tnorm):
            menu_names = ["시그니처 메뉴", "셰프 추천", "가벼운 메뉴"]
            target = None
            for name in menu_names:
                if name.replace(" ", "").lower() in tnorm:
                    target = name
                    break
            if store and target:
                menu = _mock_menu(store)
                item = next((m for m in menu if m["name"] == target), None)
                if item:
                    ui.setdefault("menu", menu)
                    reply_parts.append(f"{item['name']}은/는 {item['desc']} 가격은 {item['price']}원입니다.")
                    did_any = True

        # Map
        if ("지도" in tnorm) or ("위치" in tnorm) or ("네이버지도" in tnorm):
            if store:
                ui.update({"mapUrl": f"https://map.naver.com/v5/search/{store}"})
                reply_parts.append("네이버 지도를 열어드릴게요.")
                did_any = True
            else:
                reply_parts.append("가게 이름을 알려주시면 지도를 열어 드려요.")

        # Payment
        if ("결제" in tnorm) or ("주문" in tnorm):
            if not store:
                reply_parts.append("어떤 가게에서 결제할지 알려주세요.")
            else:
                menu = _mock_menu(store)
                items = [m for m in menu if m["name"] in selected_names] if selected_names else [menu[0]]
                amount = sum(i["price"] for i in items)
                ui.update({"payment": {"status": "success", "amount": amount, "items": items}})
                reply_parts.append(f"총 {amount}원 결제되었습니다. 모의 결제에요.")
                did_any = True

        if not did_any:
            if not store:
                reply_parts.append("가게 이름과 함께 '리뷰 알려줘', '메뉴 추천'처럼 말씀해 보세요.")
            else:
                reply_parts.append(f"{store}에 대해 리뷰 요약, 메뉴 추천, 지도, 결제 등 무엇을 도와드릴까요?")

        return jsonify({
            "reply": " ".join(reply_parts) if reply_parts else "요청을 이해하지 못했어요. 다시 말씀해 주실래요?",
            "ui": ui,
            "state": {"store": store}
        })

    # --- Agent orchestrator ---
    @app.post("/api/agent")
    def api_agent_route():
        data = request.get_json(silent=True) or {}
        session_id = (data.get("sessionId") or "default").strip() or "default"
        message = (data.get("message") or "").strip()
        ctx = {
            "store": (data.get("store") or "").strip(),
            "history": data.get("history") or [],
            "selectedNames": data.get("selectedNames") or [],
        }
        out = agent.run(session_id=session_id, message=message, ctx=ctx)
        return jsonify(out)

    # Static fallback for assets
    @app.route("/static/<path:path>")
    def static_proxy(path):
        return send_from_directory(app.static_folder, path)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5173")), debug=True)

    # --- Web Search API for Menu Recommendations ---
    @app.post("/api/search-menu")
    def api_search_menu():
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON data required"}), 400
        
        store_name = data.get("store_name", "").strip()
        query = data.get("query", "").strip()
        
        if not store_name or not query:
            return jsonify({"error": "store_name and query are required"}), 400
        
        # Mock web search results for MVP
        # In production, this would use actual web search APIs
        search_results = []
        
        if "추천" in query or "메뉴" in query:
            search_results = [
                {
                    "title": f"{store_name} 인기 메뉴 추천",
                    "snippet": f"{store_name}에서 가장 인기 있는 메뉴는 시그니처 파스타와 수제 피자입니다. 특히 크림 파스타가 맛있다는 후기가 많습니다.",
                    "url": f"https://example.com/{store_name}-menu"
                },
                {
                    "title": f"{store_name} 후기 및 추천 메뉴",
                    "snippet": "방문객들이 추천하는 메뉴로는 버섯 리조또, 토마토 스프, 그릴드 치킨이 있습니다. 모두 신선한 재료로 만들어집니다.",
                    "url": f"https://example.com/{store_name}-reviews"
                }
            ]
        elif "후기" in query or "리뷰" in query:
            search_results = [
                {
                    "title": f"{store_name} 방문 후기",
                    "snippet": f"{store_name}는 맛있고 분위기가 좋다는 평가를 받고 있습니다. 특히 서비스가 친절하고 음식 퀄리티가 높습니다.",
                    "url": f"https://example.com/{store_name}-reviews"
                }
            ]
        
        # Generate recommendations based on search results
        recommendations = []
        if search_results:
            recommendations = [
                {
                    "name": "시그니처 파스타",
                    "description": "크림소스가 진짜 맛있다고 유명해요 (리뷰 기반)",
                    "price": "15,000원",
                    "source": "web_search"
                },
                {
                    "name": "수제 피자",
                    "description": "신선한 토핑과 바삭한 도우 (후기 추천)",
                    "price": "18,000원",
                    "source": "web_search"
                },
                {
                    "name": "버섯 리조또",
                    "description": "방문객들이 자주 추천하는 메뉴",
                    "price": "16,000원",
                    "source": "web_search"
                }
            ]
        
        return jsonify({
            "store_name": store_name,
            "query": query,
            "search_results": search_results,
            "recommendations": recommendations
        })


    # --- Naver Map API Integration for Menu Information ---
    @app.post("/api/naver-menu-info")
    def api_naver_menu_info():
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON data required"}), 400
        
        menu_name = data.get("menu_name", "").strip()
        store_name = data.get("store_name", "").strip()
        
        if not menu_name:
            return jsonify({"error": "menu_name is required"}), 400
        
        # Mock Naver Map API response for MVP
        # In production, this would use actual Naver Map API
        menu_info = {
            "menu_name": menu_name,
            "store_name": store_name or "맛있는 레스토랑",
            "description": f"{menu_name}는 신선한 재료로 만든 시그니처 메뉴입니다.",
            "ingredients": ["신선한 재료", "특제 소스", "엄선된 향신료"],
            "allergens": ["글루텐", "유제품"],
            "nutrition": {
                "calories": "350kcal",
                "protein": "25g",
                "carbs": "30g",
                "fat": "15g"
            },
            "cooking_time": "15-20분",
            "spice_level": "보통",
            "price": "15,000원",
            "reviews": [
                "정말 맛있어요! 재료가 신선해서 좋았습니다.",
                "양도 많고 가격도 합리적이에요.",
                "다음에 또 주문하고 싶은 메뉴입니다."
            ],
            "rating": 4.5,
            "image_url": f"https://example.com/menu/{menu_name}.jpg",
            "source": "naver_map"
        }
        
        return jsonify({
            "success": True,
            "menu_info": menu_info
        })


# 삼성페이 결제 API
@app.route('/api/samsung-pay', methods=['POST'])
def samsung_pay():
    try:
        data = request.get_json()
        
        # 필수 파라미터 검증
        required_fields = ['items', 'total_amount', 'store_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        items = data['items']
        total_amount = data['total_amount']
        store_name = data['store_name']
        
        # Mock 삼성페이 결제 처리
        payment_result = {
            'success': True,
            'payment_id': f'SP_{int(time.time())}_{random.randint(1000, 9999)}',
            'transaction_id': f'TXN_{random.randint(100000, 999999)}',
            'amount': total_amount,
            'currency': 'KRW',
            'payment_method': 'Samsung Pay',
            'card_info': {
                'card_type': 'Credit Card',
                'card_brand': 'Samsung Card',
                'last_four_digits': '****1234'
            },
            'store_info': {
                'name': store_name,
                'location': '서울시 강남구',
                'merchant_id': 'MERCHANT_001'
            },
            'order_info': {
                'items': items,
                'order_number': f'ORD_{random.randint(10000, 99999)}',
                'order_time': datetime.now().isoformat(),
                'estimated_preparation_time': '15-20분'
            },
            'receipt': {
                'receipt_url': f'https://receipt.samsung.com/{random.randint(100000, 999999)}',
                'receipt_number': f'RCP_{random.randint(100000, 999999)}'
            },
            'status': 'completed',
            'message': '결제가 성공적으로 완료되었습니다.',
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'payment_result': payment_result,
            'message': '삼성페이 결제가 완료되었습니다!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '결제 처리 중 오류가 발생했습니다.'
        }), 500

# QR 코드 생성 API
@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        data = request.get_json()
        
        order_number = data.get('order_number', f'ORD_{random.randint(10000, 99999)}')
        
        # Mock QR 코드 데이터
        qr_data = {
            'qr_code_url': f'https://qr.samsung.com/order/{order_number}',
            'qr_code_data': f'samsung-pay://order/{order_number}',
            'order_number': order_number,
            'expires_at': (datetime.now() + timedelta(minutes=10)).isoformat(),
            'instructions': [
                '1. 삼성페이 앱을 실행하세요',
                '2. QR 코드를 스캔하세요',
                '3. 결제 정보를 확인하고 결제하세요',
                '4. 결제 완료 후 주문이 접수됩니다'
            ]
        }
        
        return jsonify({
            'success': True,
            'qr_data': qr_data,
            'message': 'QR 코드가 생성되었습니다.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'QR 코드 생성 중 오류가 발생했습니다.'
        }), 500
