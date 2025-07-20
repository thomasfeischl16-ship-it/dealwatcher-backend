from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup

app = FastAPI()

class TrackRequest(BaseModel):
    url: str

def fetch_price_with_fallbacks(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error fetching page: {e}")

    soup = BeautifulSoup(response.text, "html.parser")

    # --------- Preis-Fallbacks ---------
    selectors = [
        # Amazon
        {"site": "amazon", "selectors": ["span#priceblock_ourprice", "span#priceblock_dealprice", "span.a-price > span.a-offscreen"]},
        # Otto
        {"site": "otto", "selectors": ["div.price-wrapper span.price", "span[data-testid='price']"]},
        # Zalando
        {"site": "zalando", "selectors": ["span.xnVDEf"]},
        # MediaMarkt
        {"site": "mediamarkt", "selectors": ["div.price span.sr-only", "span[itemprop='price']"]},
        # Standard-Selectors (fallback)
        {"site": "default", "selectors": ["span.price", "div.price", "meta[itemprop='price']", "span[class*='price']"]}
    ]

    for site in selectors:
        for selector in site["selectors"]:
            price_tag = soup.select_one(selector)
            if price_tag:
                price = price_tag.get_text(strip=True)
                return price

    return "Price not found"

@app.post("/track_price")
async def track_price(request: TrackRequest):
    price = fetch_price_with_fallbacks(request.url)
    return {"url": request.url, "price": price}
