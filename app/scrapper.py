import os
import json
import time
import base64
from dotenv import load_dotenv
import google.generativeai as genai

from database import *
from r2 import getImageUrl, imageExists
import requests

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

def scrapeStoreFlyer(store, idEpicerie, week_start):
    images = []

    i = 0
    while imageExists(f"circulaires/{store}_{week_start}/{store}{i}.png"):
        url = getImageUrl(f"circulaires/{store}_{week_start}/{store}{i}.png")

        response = requests.get(url)

        images.append({
            "mime_type": "image/png",
            "data": response.content
        })

        i += 1

    if not images:
        print(f"Aucune image trouvée pour {store} - {week_start}")
        return

    prompt = f"""
Extract ALL discounts from these grocery flyer pages for store '{store}'.

Return ONLY a valid JSON array.

Format:
[
  {{
    "product_name": "Poitrines de poulet",
    "discount_pct": 30,
    "original_price": 8.99,
    "discounted_price": 6.29,
    "page_number": 1
  }}
]

Rules:
- Each image is one flyer page
- page_number starts at 1
- Extract EVERY discounted product visible
- If original price is missing, calculate it
- Output ONLY raw JSON
- No markdown
- No explanations
"""

    MAX_RETRIES = 5

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(
                [prompt] + images,
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json"
                }
            )

            text = response.text.strip()

            discounts = json.loads(text)

            for d in discounts:
                insertDiscount(
                    idEpicerie=idEpicerie,
                    week_start=week_start,
                    product_name=d.get("product_name"),
                    discount_pct=d.get("discount_pct"),
                    original_price=d.get("original_price"),
                    discounted_price=d.get("discounted_price"),
                    page_number=d.get("page_number")
                )

            print(f"✅ {len(discounts)} rabais insérés pour {store}")
            return

        except Exception as e:
            print(f"Tentative {attempt + 1} échouée: {e}")

            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            else:
                print("❌ Échec final")