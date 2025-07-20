from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup

app = FastAPI()

class TrackRequest(BaseModel):
    url: str

def clean_price(text: str) -> str:
    """Hilfsfunktion, um Preise zu bereinigen."""
    return text.replace("\n", "").strip()

def fetch_price_with_priority(url: str) -> str:
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

    # --------- Spezifische Selectors ---------
    site_selectors = {
        "otto": [
            {"name": "deal price", "selectors": ["span.priceWrapper span.price", "div.price-wrapper span.price"]},
            {"name": "default price", "selectors": ["span.baseprice"]},
        ],
        "amazon": [
            {"name": "deal price", "selectors": ["span#priceblock_dealprice", "span.a-price > span.a-offscreen"]},
            {"name": "default price", "selectors": ["span#priceblock_ourprice"]}
        ],
        "mediamarkt": [
            {"name": "deal price", "selectors": ["div.price span.sr-only", "span.price-current"]},
            {"name": "default price", "selectors": ["span[itemprop='price']"]}
        ],
        "zalando": [
            {"name": "deal price", "selectors": ["span.xnVDEf"]},
            {"name": "default price", "selectors": ["span[title*='Preis']"]}
        ],
        # Fallback für andere
        "default": [
            {"name": "deal price", "selectors": ["span.special-price", "span.sale-price", "span.discount-price"]},
            {"name": "default price", "selectors": ["span.price", "div.price", "meta[itemprop='price']"]}
        ],
    }

    domain = ""
    if "otto.de" in url:
        domain = "otto"
    elif "amazon." in url:
        domain = "amazon"
    elif "mediamarkt" in url:
        domain = "mediamarkt"
    elif "zalando" in url:
        domain = "zalando"
    else:
        domain = "default"

    selectors = site_selectors.get(domain, site_selectors["default"])

    # --------- Suche in Priorität: Deal -> Standard ---------
    for group in selectors:
        for selector in group["selectors"]:
            tag = soup.select_one(selector)
            if tag:
                price = clean_price(tag.get_text())
                if price:
                    return price

    return "Price not found"

@app.post("/track_price")
async def track_price(request: TrackRequest):
    price = fetch_price_with_priority(request.url)
    return {"url": request.url, "price": price}
