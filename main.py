from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from playwright.async_api import async_playwright

app = FastAPI()

class Product(BaseModel):
    url: str

price_history = {}

async def scrape_price(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # Amazon Beispiel
        price_selectors = [
            "#priceblock_ourprice",      # Amazon normal
            "#priceblock_dealprice",     # Amazon Angebote
            ".price",                    # Otto / Alternate
            ".product-price",            # MediaMarkt/Saturn
        ]

        price = None
        for selector in price_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    price_text = await element.inner_text()
                    price = price_text.strip().replace("€", "").replace(",", ".")
                    price = float(price)
                    break
            except:
                continue

        await browser.close()

        if price is None:
            raise Exception("Kein Preis gefunden. Selektor prüfen oder Shop blockiert Bots.")
        return price

@app.post("/track_price")
async def track_price(product: Product):
    url = product.url

    try:
        price = await scrape_price(url)
    except Exception as e:
        return {"error": str(e)}

    # Preisverlauf speichern
    if url not in price_history:
        price_history[url] = []
    price_history[url].append(price)

    return {
        "url": url,
        "current_price": price,
        "history": price_history[url]
    }

