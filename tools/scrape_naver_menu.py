#!/usr/bin/env python3
import argparse
import json
import time
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser(description="Scrape Naver Place share URL for menu items (best-effort)")
    parser.add_argument("url", help="Naver place share URL (e.g., https://naver.me/xxxx)")
    parser.add_argument("store", help="Store name to save under")
    parser.add_argument("--backend", default="http://localhost:5173", help="Backend base for import POST")
    parser.add_argument("--post", action="store_true", help="POST to backend /api/menu/import after scraping")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("Playwright not installed. Install via: pip install playwright && playwright install chromium")
        return 2

    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        ctx = browser.new_context(viewport={"width": 1280, "height": 1600})
        page = ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded")
        # Some share links redirect; wait a bit
        time.sleep(2)
        try:
            # Try to reveal menu section by clicking '메뉴' tab if present
            if page.get_by_role("tab", name="메뉴").is_visible():
                page.get_by_role("tab", name="메뉴").click()
                time.sleep(1.5)
        except Exception:
            pass

        # Heuristic: collect cards that contain price with '원'
        candidates = page.locator("text=원").all()
        seen = set()
        for el in candidates:
            try:
                parent = el.locator("xpath=ancestor::*[self::li or self::div][1]")
                txt = parent.inner_text(timeout=1000)
                if not txt or "원" not in txt:
                    continue
                lines = [t.strip() for t in txt.splitlines() if t.strip()]
                name = lines[0]
                price_line = next((l for l in lines if "원" in l), None)
                price = 0
                if price_line:
                    digits = "".join(ch for ch in price_line if ch.isdigit())
                    price = int(digits or 0)
                img = None
                try:
                    img_el = parent.locator("img").first
                    if img_el and img_el.is_visible():
                        src = img_el.get_attribute("src")
                        img = src
                except Exception:
                    pass
                key = (name, price, img)
                if key in seen:
                    continue
                seen.add(key)
                items.append({"name": name, "desc": "", "price": price, "image": img})
            except Exception:
                continue

        browser.close()

    payload = {"store": args.store, "menu": items}
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.post and items:
        import requests
        url = args.backend.rstrip("/") + "/api/menu/import"
        r = requests.post(url, json=payload, timeout=10)
        print("POST", url, r.status_code, r.text[:200])

    if not items:
        print("No items found. This is expected sometimes due to dynamic rendering.")
        print("Tip: open the URL in a normal browser, copy visible menu names/prices/images, and fill the JSON above.")

if __name__ == "__main__":
    raise SystemExit(main())

