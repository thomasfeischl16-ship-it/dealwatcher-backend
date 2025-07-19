from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI()

class PriceRequest(BaseModel):
    url: str

def get_price_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    # 🟢 Schritt 1: BeautifulSoup mit präziseren Selector
    possible_selectors = [
        {"name": "span", "attrs": {"class": "product-price__price"}},  # Otto (präzise)
        {"name": "span", "attrs": {"id": "priceblock_ourprice"}},      # Amazon
        {"name": "span", "attrs": {"id": "priceblock_dealprice"}},     # Amazon Deal-Preis
        {"name": "span", "attrs": {"class": "a-price-whole"}},         # Amazon fallback
        {"name": "div", "attrs": {"class": "price"}},                  # generisch
    ]

    for selector in possible_selectors:
        price_tag = soup.find(selector["name"], selector["attrs"])
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            if price_text:
                return price_text, "BeautifulSoup (precise selector)"

    # 🟢 Schritt 2: Fallback – nur Main-Content durchsuchen
    main_content = soup.find("main")
    if main_content:
        html_to_search = str(main_content)
    else:
        html_to_search = html

    prices = re.findall(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s?€", html_to_search)
    if prices:
        return prices[0], "Regex fallback (main content)"

    # 🟢 Schritt 3: Kein Preis gefunden
    return None, None

@app.post("/track_price")
def track_price(request: PriceRequest):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(request.url, headers=headers, timeout=10)
        response.raise_for_status()

        price, method = get_price_from_html(response.text)
        if price:
            return {
                "url": request.url,
                "current_price": price,
                "method": method
            }
        else:
            return {
                "url": request.url,
                "current_price": "Price not found",
                "method": None
            }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching page: {e}")
