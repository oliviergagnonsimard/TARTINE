import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from main import *


load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def matchCatalogWithDiscounts(week_start):
        catalog = getCatalogItems()
        discounts = getDiscountsForWeek(week_start)
        
        if not catalog or not discounts:
            return
        
        prompt = f"""Match each catalog ingredient to relevant discounted grocery products.

    Catalog ingredients:
    {json.dumps([{"id": c[0], "nom": c[1]} for c in catalog], ensure_ascii=False)}

    Discounted products this week:
    {json.dumps([{"id": d[0], "nom": d[1]} for d in discounts], ensure_ascii=False)}

    Rules:
    - Only match if the product is genuinely the same ingredient ("poulet" → "Poitrines de poulet" ✓, "Soupe de poulet" ✗)
    - One catalog item can match multiple discounts (different stores)

    Return ONLY valid JSON:
    [{{"catalog_id": 3, "discount_id": 42}}, ...]
    """

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        )

        matches = json.loads(response.text.strip())
        saveCatalogDiscountMatches(matches, week_start)
