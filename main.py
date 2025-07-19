from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup

app = FastAPI()

# Eingabemodell
class TrackRequest(BaseModel):
    url: str

@app.post("/track_price")
def track_price(request: TrackRequest):
    url = request.url
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
    }

    try:
        # HTML der Seite laden
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to load page.")

        soup = BeautifulSoup(response.text, "html.parser")

        # Amazon Beispiel: Preis parsen
        price_element = soup.select_one("#priceblock_ourprice, #priceblock_dealprice")
        if price_element:
            price = price_element.get_text(strip=True)
        else:
            price = "Price not found"

        return {"url": url, "current_price": price}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching price: {str(e)}")

