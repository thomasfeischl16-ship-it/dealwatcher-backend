from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import re
import json
import asyncio
from playwright.async_api import async_playwright

app = FastAPI()

# === Helper Functions ===
async def fetch_price_with_playwright(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        await page.goto(url, timeout=60000)

        # Try various selectors for price
        selectors = [
            '[id*="price"]',
            '[class*="price"]',
            'span:has-text("€")',
            'span:has-text("$")'
        ]

        price_text = None
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    price_match = re.search(r"[\d.,]+", text)
                    if price_match:
                        price_text = price_match.group(0)
                        break
            except:
                continue

        await browser.close()

        if not price_text:
            raise HTTPException(status_code=404, detail="Price not found with Playwright")
        return price_text


def fetch_price_with_requests(url: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Error fetching page: {response.status_code}")

    soup = BeautifulSoup(response.content, "html.parser")
    selectors = [
        '[id*="price"]',
        '[class*="price"]',
        'span:has-text("€")',
        'span:has-text("$")'
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            price_match = re.search(r"[\d.,]+", element.get_text())
            if price_match:
                return price_match.group(0)

    raise HTTPException(status_code=404, detail="Price not found with requests")


# === API Endpoints ===
class PriceRequest(BaseModel):
    url: str

@app.post("/track_price")
async def track_price(req: PriceRequest):
    try:
        # Try with requests first
        price = fetch_price_with_requests(req.url)
        return {"url": req.url, "current_price": price}
    except:
        # Fallback to Playwright if requests fail
        try:
            price = await fetch_price_with_playwright(req.url)
            return {"url": req.url, "current_price": price}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Playwright also failed: {str(e)}")

