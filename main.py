from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import re

# Playwright-Import
from playwright.sync_api import sync_playwright

app = FastAPI()

class PriceRequest(BaseModel):
    url: str | None = None
    shop: str | None = None
    article_number: str | None = None

# 🟢 Funktion: Baue URL aus Shop & Artikelnummer
def build_url_from_article(shop, article_number):
    shop = shop.lower()
    if shop == "amazon":
        return f"https://www.amazon.de/dp/{article_number}"
    elif shop == "otto":
        return f"https://www.otto.de/p/{article_number}/"
    elif shop == "mediamarkt":
        return f"https://www.mediamarkt.de/de/product/_{article_number}.html"
    elif shop == "conrad":
        return f"https://www.conrad.de/de/p/{article_number}.html"
    else:
        return None

# 🟢 Playwright: Hole den Preis aus dynamischen Seiten
def get_price_with_playwright(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20000)  # 20 Sekunden Timeout

            # Warte bis Preis geladen ist
            page.wait_for_timeout(3000)  # 3 Sek. warten

            content = page.content()
            browser.close()

            # BeautifulSoup zum Parsen nutzen
            soup = BeautifulSoup(content, "html.parser")
            possible_selectors = [
                {"name": "span", "attrs": {"id": "priceblock_ourprice"}},  # Amazon
                {"name": "span", "attrs": {"id": "priceblock_dealprice"}}, # Amazon
                {"name": "span", "attrs": {"class": "product-price__price"}}, # Otto
                {"name": "div", "attrs": {"class": "m-price__price"}},  # MediaMarkt
            ]

            for selector in possible_selectors:
                price_tag = soup.find(selector["name"], selector["attrs"])
                if price_tag:
                    price_text = price_tag.get_text(strip=True)
                    if "€" in price_text:
                        return price_text, "Playwright"

            return None, None
    except Exception as e:
        print(f"Playwright Error: {e}")
        return None, None

# 🟢 BeautifulSoup Fallback
def get_price_with_bs(html):
    soup = BeautifulSoup(html, "html.parser")
    prices = re.findall(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s?€", html)
    if prices:
        return prices[0], "BeautifulSoup fallback"
    return None, None

@app.post("/track_price")
def track_price(request: PriceRequest):
    try:
        # 🟣 Prüfe ob URL oder Artikelnummer verwendet wird
        if request.url:
            url = request.url
        elif request.shop and request.article_number:
            url = build_url_from_article(request.shop, request.article_number)
            if not url:
                raise HTTPException(status_code=400, detail="Unsupported shop or invalid article number.")
        else:
            raise HTTPException(status_code=400, detail="Provide either URL or (shop + article_number).")

        # 🟢 Versuche Playwright
        price, method = get_price_with_playwright(url)
        if price:
            return {
                "url": url,
                "current_price": price,
                "method": method
            }

        # 🟣 Fallback: BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        price, method = get_price_with_bs(response.text)

        if price:
            return {
                "url": url,
                "current_price": price,
                "method": method
            }
        else:
            return {
                "url": url,
                "current_price": "Price not found",
                "method": None
            }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching page: {e}")
