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

def scrapeStoreFlyerPage(store, idEpicerie, week_start, image, page_num):
    prompt = f"""Extract ALL discounts from this grocery flyer page (page {page_num}) for store '{store}'.

Return ONLY a valid JSON array.

Format:
[
  {{
    "product_name": "Poitrines de poulet",
    "discount_percentage": 30,
    "original_price": 8.99,
    "discounted_price": 6.29,
    "quantity": 500,
    "unit_of_measure": "g",
    "page_number": {page_num}
  }}
]

Rules:
- Extract EVERY discounted product visible on this page — do NOT skip any
- A typical flyer page has 8-15 products minimum, make sure you get them all
- If original price is missing, calculate it from the discount percentage
- quantity: the numeric amount (e.g. 500, 1, 2)
- unit_of_measure: the unit as shown (e.g. "g", "kg", "lb", "ml", "L", "unités"). Set both to null if not shown.
- Output ONLY raw JSON, no markdown, no explanations
"""

    MAX_RETRIES = 5

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(
                [prompt, image],
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
                    discount_pct=d.get("discount_percentage"),
                    original_price=d.get("original_price"),
                    discounted_price=d.get("discounted_price"),
                    page_number=page_num,
                    quantity=d.get("quantity"),
                    unit_of_measure=d.get("unit_of_measure")
                )

            print(f"  📄 Page {page_num}: {len(discounts)} rabais insérés")
            return len(discounts)

        except Exception as e:
            print(f"  ⚠️ Page {page_num} - Tentative {attempt + 1} échouée: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            else:
                print(f"  ❌ Page {page_num} - Échec final")
                return 0


def scrapeStoreFlyer(store, idEpicerie, week_start):
    print(f"🔍 Scraping {store} - semaine du {week_start}...")
    
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

    print(f"  📦 {len(images)} pages trouvées")

    total = 0
    for page_num, image in enumerate(images, start=1):
        count = scrapeStoreFlyerPage(store, idEpicerie, week_start, image, page_num)
        total += count
        time.sleep(1)  # petit délai pour pas spam l'API

    print(f"✅ {store} terminé — {total} rabais insérés au total")