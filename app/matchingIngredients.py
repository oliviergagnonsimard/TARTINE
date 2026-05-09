import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from database import *
from main import getFlyerStartWeekStr


load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def matchIngredientsWithDiscounts(idRecette, idClient):
    week_start = getFlyerStartWeekStr()
    
    # Récupère les ingrédients de la recette
    recette, ingredients = getRecetteWithIngredients(idRecette, idClient)
    if not recette or not ingredients:
        return None
    
    # Récupère tous les rabais de la semaine
    discounts = getDiscountsForWeek(week_start)
    if not discounts:
        return None

    # Formate les ingrédients
    ingredients_list = [f"{ing[1]} {ing[0]}" if ing[1] else ing[0] for ing in ingredients]
    
    # Formate les rabais
    discounts_formatted = [
        {
            "id": d[0],
            "product_name": d[1],
            "original_price": float(d[3]) if d[3] else None,
            "discounted_price": float(d[4]) if d[4] else None,
            "store": d[5]
        }
        for d in discounts
    ]

    prompt = f"""You are a grocery matching assistant.

Here are the ingredients needed for the recipe "{recette[1]}":
{json.dumps(ingredients_list, ensure_ascii=False)}

Here are this week's discounted products:
{json.dumps(discounts_formatted, ensure_ascii=False)}

Your job: match each ingredient to the most relevant discounted product.

Rules:
- Only match if the discount is genuinely useful for the recipe (e.g. "poulet" matches "Poitrines de poulet" but NOT "Soupe de poulet")
- One ingredient can match multiple stores
- If no good match exists, don't force one
- Calculate savings: original_price - discounted_price

Return ONLY a valid JSON array:
[
  {{
    "ingredient": "poulet",
    "discount_id": 42,
    "product_name": "Poitrines de poulet",
    "store": "maxi",
    "original_price": 8.99,
    "discounted_price": 6.29,
    "savings": 2.70
  }}
]
"""

    response = model.generate_content(
        prompt,
        generation_config={{
            "temperature": 0.1,
            "response_mime_type": "application/json"
        }}
    )

    matches = json.loads(response.text.strip())
    
    total_savings = sum(m.get("savings", 0) for m in matches)
    
    return {
        "recette": recette[1],
        "matches": matches,
        "total_savings": round(total_savings, 2)
    }



result = matchIngredientsWithDiscounts(idRecette=1, idClient=1)
print(result)