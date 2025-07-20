import asyncio
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import requests
from bs4 import BeautifulSoup

app = FastAPI()

class TrackRequest(BaseModel):
    url: str

# Hilfsfunktion: Zahl aus Text extrahieren
def parse_price(text: str) -> float | None:
    num = "".join(c for c in text if c.isdigit() or c in ",.")
    if not num:
        return None
    return float(num.replace(".", "").replace(",", "."))

# Schritt 1: Playwright Scraping
async def get_price_playwright(url: str) -> float | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(30000)
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "de-DE,de;q=0.9"
        })
        await page.goto(url)
        html = await page.content()
        await browser.close()
    return extract_price(html, url)

# Schritt 2: Requests Scraping als Fallback
def get_price_requests(url: str) -> float | None:
    resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0", "Accept-Language":"de"})
    if resp.status_code != 200:
        return None
    return extract_price(resp.text, url)

# Zentrale Funktion: Suche nach allen möglichen Selektoren
def extract_price(html: str, url: str) -> float | None:
    soup = BeautifulSoup(html, "html.parser")
    selectors = [
        ".price-block__price--final", ".product-price__current-price",  # Otto
        ".product-price span:first-child", 
        ".price", ".price--final", ".price-value",                     # Zalando & MediaMarkt
        "#priceblock_ourprice", "#priceblock_dealprice", ".a-price .a-offscreen",  # Amazon
        ".price-new", ".product-shop-price", ".selling-price",          # weitere Shops
    ]
    texts = [el.get_text(strip=True) for sel in selectors for el in soup.select(sel)]
    for txt in texts:
        price = parse_price(txt)
        if price:
            return price
    # Regex als letzte Chance
    m = re.search(r'([0-9]+[\.,][0-9]{2})\s*€', html)
    if m:
        return float(m.group(1).replace(",", "."))
    return None

@app.post("/track_price")
async def track_price(req: TrackRequest):
    url = req.url
    price = await get_price_playwright(url)
    if price is None:
        price = get_price_requests(url)
    if price is None:
        raise HTTPException(status_code=404, detail="Price not found")
    return {"url": url, "current_price": price}
