import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
from database import *
from r2 import getImageUrl, imageExists
import requests
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

BATCH_SIZE = 3

def downloadImage(args):
    i, store, week_start = args
    url = getImageUrl(f"circulaires/{store}_{week_start}/{store}{i}.png")
    response = requests.get(url)
    return {"mime_type": "image/png", "data": response.content}

def scrapePageBatch(store, idEpicerie, week_start, images_batch, start_page):
    page_nums = list(range(start_page, start_page + len(images_batch)))
    
    prompt = f"""Extract ALL discounts from these {len(images_batch)} grocery flyer pages (pages {page_nums}) for '{store}'.
Return ONLY a JSON array

Format:
[
    {{
    "product_name": str,
    "discount_percentage": float|null,
    "original_price": float|null,
    "discounted_price": float|null,
    "quantity": float|null,
    "unit_of_measure": str|null,
    "page_number": int
    }}
]

Rules:
Extract EVERY discounted product visible on this page. Make SURE that you look for an original price next to the item when it has a discount.
The original price in french might be called "Prix régulier: ..$" or "Prix reg. : ..$" or any other similar combination
IF THERE IS NOT DISCOUNT : Set to null
A typical flyer page has 8-15 products minimum, make sure you get them all
If original price is missing, calculate it from the discount percentage
quantity: the numeric amount (e.g. 500, 1, 2)
unit_of_measure: the unit as shown (e.g. "g", "kg", "lb", "ml", "L", "unités"). Set both to null if not shown.
Output ONLY raw JSON, no markdown, no explanations
"""

    MAX_RETRIES = 5
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(
                [prompt] + images_batch,
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json"
                }
            )

            discounts = json.loads(response.text.strip())

            for d in discounts:
                insertDiscount(
                    idEpicerie=idEpicerie,
                    week_start=week_start,
                    product_name=d.get("product_name"),
                    discount_pct=d.get("discount_percentage"),
                    original_price=d.get("original_price"),
                    discounted_price=d.get("discounted_price"),
                    page_number=d.get("page_number"),
                    quantity=d.get("quantity"),
                    unit_of_measure=d.get("unit_of_measure")
                )

            print(f"  📄 Pages {page_nums}: {len(discounts)} rabais insérés")
            return len(discounts)

        except Exception as e:
            print(f"  ⚠️ Pages {page_nums} - Tentative {attempt + 1} échouée: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            else:
                print(f"  ❌ Pages {page_nums} - Échec final")
                return 0

def scrapeStoreFlyer(store, idEpicerie, week_start):
    print(f"🔍 Scraping {store} - semaine du {week_start}...")

    # Trouve toutes les pages disponibles
    indices = []
    i = 0
    while imageExists(f"circulaires/{store}_{week_start}/{store}{i}.png"):
        indices.append(i)
        i += 1

    if not indices:
        print(f"Aucune image trouvée pour {store} - {week_start}")
        return

    print(f"  📦 {len(indices)} pages trouvées — téléchargement parallèle...")

    # Télécharge toutes les images en parallèle
    with ThreadPoolExecutor(max_workers=8) as executor:
        images = list(executor.map(downloadImage, [(i, store, week_start) for i in indices]))

    print(f"  ✅ Images téléchargées — scraping par batch de {BATCH_SIZE}...")

    # Scrape par batch
    total = 0
    for batch_start in range(0, len(images), BATCH_SIZE):
        batch = images[batch_start:batch_start + BATCH_SIZE]
        count = scrapePageBatch(store, idEpicerie, week_start, batch, batch_start + 1)
        total += count
        time.sleep(1)

    print(f"✅ {store} terminé — {total} rabais insérés au total")