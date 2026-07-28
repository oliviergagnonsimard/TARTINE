import json
import os
import re
from typing import List, Tuple

from dotenv import load_dotenv

from database import *
from main import *

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - dependency may be unavailable in tests
    genai = None


load_dotenv()

if genai is not None and os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None


STOPWORDS = {"de", "du", "des", "le", "la", "les", "au", "aux", "en", "et", "ou",
             "sac", "boite", "boîte", "paquet", "format", "frais", "surgele", "surgelé",
             "g", "kg", "ml", "l", "lb", "oz", "un", "une"}

def _normalize_text(value: str) -> str:
    if not value:
        return ""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    tokens = [t for t in value.split() if t not in STOPWORDS]
    return " ".join(tokens)


def _coerce_matches(parsed) -> List[dict]:
    if isinstance(parsed, dict):
        for key in ("matches", "results"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break

    if not isinstance(parsed, list):
        return []

    coerced = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        catalog_id = item.get("catalog_id")
        discount_id = item.get("discount_id")
        if catalog_id is None or discount_id is None:
            continue
        try:
            coerced.append({
                "catalog_id": int(catalog_id),
                "discount_id": int(discount_id),
            })
        except (TypeError, ValueError):
            continue

    return coerced


def _parse_gemini_matches(payload: str) -> List[dict]:
    if not payload:
        return []

    cleaned = payload.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    for candidate in (cleaned, cleaned.replace("\n", " ")):
        try:
            return _coerce_matches(json.loads(candidate))
        except json.JSONDecodeError:
            continue

    start = cleaned.find("[")
    if start != -1:
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(cleaned)):
            char = cleaned[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
            else:
                if char == '"':
                    in_string = True
                elif char == "[":
                    depth += 1
                elif char == "]":
                    if depth == 0:
                        continue
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[start:index + 1]
                        try:
                            return _coerce_matches(json.loads(candidate))
                        except json.JSONDecodeError:
                            break

    match = re.search(r"\[(.*?)\]", cleaned, flags=re.DOTALL)
    if match:
        try:
            return _coerce_matches(json.loads(match.group(0)))
        except json.JSONDecodeError:
            return []

    return []


def _build_gemini_prompt(catalog: List[Tuple[int, str]], discounts: List[Tuple[int, str, float, float, float, str]], sample_size: int | None = None) -> str:
    catalog_subset = catalog[:sample_size] if sample_size is not None else catalog
    discounts_subset = discounts[:sample_size] if sample_size is not None else discounts

    return f"""You are matching grocery catalog items to discount products.

Task:
For each catalog item, find the discount product that is the same ingredient.
Return a JSON array of objects with only these keys: catalog_id and discount_id.
Do not return anything else.

Important rules:
- Match only if the products are clearly the same ingredient.
- If you are unsure, return an empty array for that item.
- Prefer precision over recall.
- A catalog item can match multiple discount products if they are from different stores.
- Return a flat JSON array, not a markdown code block.

Catalog items:
{json.dumps([{"id": c[0], "nom": c[1]} for c in catalog_subset], ensure_ascii=False)}

Discount products:
{json.dumps([{"id": d[0], "nom": d[1]} for d in discounts_subset], ensure_ascii=False)}

Example output:
[{{"catalog_id": 1, "discount_id": 10}}]
"""


def testGeminiPromptSample(week_start, sample_size=8, status_cb=None):
    catalog = getCatalogItems()
    discounts = getDiscountsForWeek(week_start)

    if not catalog or not discounts:
        if status_cb:
            status_cb("Aucun catalogue ou rabais disponible pour ce week", "Aucun catalogue ou rabais disponible pour ce week")
        return {"success": False, "error": "Aucun catalogue ou rabais disponible pour ce week"}

    try:
        sample_size = int(sample_size)
    except (TypeError, ValueError):
        sample_size = 8

    sample_size = max(1, min(sample_size, 50))  # ← cap remonté, 12 était trop bas pour tester sérieusement

    # Construit un échantillon avec des recoupements probables, pour que le test
    # ait une vraie chance de produire des matches (plutôt que 2 tranches déconnectées).
    catalog_subset = []
    discounts_subset = []
    used_discount_ids = set()

    for catalog_id, catalog_name in catalog:
        normalized_catalog = _normalize_text(catalog_name)
        if not normalized_catalog:
            continue
        catalog_tokens = set(normalized_catalog.split())

        found_match = False
        for discount in discounts:
            discount_id = discount[0]
            discount_name = discount[1]
            if discount_id in used_discount_ids:
                continue
            normalized_discount = _normalize_text(discount_name)
            if not normalized_discount:
                continue
            discount_tokens = set(normalized_discount.split())

            if normalized_catalog in normalized_discount or catalog_tokens & discount_tokens:
                discounts_subset.append(discount)
                used_discount_ids.add(discount_id)
                found_match = True
                break

        if found_match:
            catalog_subset.append((catalog_id, catalog_name))

        if len(catalog_subset) >= sample_size:
            break

    # Fallback si aucun recoupement heuristique n'existe (catalogue/rabais totalement disjoints)
    if not catalog_subset:
        catalog_subset = catalog[:sample_size]
        discounts_subset = discounts[:sample_size]

    prompt = _build_gemini_prompt(catalog_subset, discounts_subset, sample_size=None)

    if status_cb:
        status_cb(
            f"Test Gemini sur {len(catalog_subset)} produits et {len(discounts_subset)} rabais",
            f"Test Gemini sur {len(catalog_subset)} produits et {len(discounts_subset)} rabais"
        )

    if model is None:
        return {"success": False, "error": "Aucun modèle Gemini disponible", "prompt": prompt}

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        )
        payload = response.text.strip()
        parsed = _parse_gemini_matches(payload)
        return {
            "success": True,
            "catalog_count": len(catalog_subset),
            "discount_count": len(discounts_subset),
            "prompt": prompt,
            "raw_response": payload,
            "parsed_matches": parsed,
        }
    except Exception as exc:
        if status_cb:
            status_cb(f"Test Gemini échoué : {exc}", f"Test Gemini échoué : {exc}")
        return {"success": False, "error": str(exc), "prompt": prompt}


def _build_fallback_matches(catalog: List[Tuple[int, str]], discounts: List[Tuple[int, str, float, float, float, str]], status_cb=None) -> List[dict]:
    matches = []
    total_catalog = len(catalog)
    if status_cb:
        status_cb("Analyse du catalogue : début du matching heuristique", "Analyse du catalogue : début du matching heuristique")

    progress_step = max(1, total_catalog // 4)
    for index, (catalog_id, catalog_name) in enumerate(catalog, 1):
        normalized_catalog_name = _normalize_text(catalog_name)
        if not normalized_catalog_name:
            continue

        for discount_id, discount_name, *_rest in discounts:
            normalized_discount_name = _normalize_text(discount_name)
            if not normalized_discount_name:
                continue

            if normalized_catalog_name in normalized_discount_name:
                matches.append({"catalog_id": catalog_id, "discount_id": discount_id})
                continue

            catalog_tokens = set(normalized_catalog_name.split())
            discount_tokens = set(normalized_discount_name.split())
            common_tokens = catalog_tokens & discount_tokens
            if len(common_tokens) >= 2:
                matches.append({"catalog_id": catalog_id, "discount_id": discount_id})

        if status_cb and (index % progress_step == 0 or index == total_catalog):
            status_cb(
                f"Analyse des produits catalogues : {index}/{total_catalog} traités",
                f"Analyse des produits catalogues : {index}/{total_catalog} traités"
            )

    if status_cb:
        status_cb(
            f"Correspondances heuristiques générées : {len(matches)}",
            f"Correspondances heuristiques générées : {len(matches)}"
        )

    return matches


def testGeminiPromptSample(week_start, sample_size=8, status_cb=None):
    catalog = getCatalogItems()
    discounts = getDiscountsForWeek(week_start)

    if not catalog or not discounts:
        if status_cb:
            status_cb("Aucun catalogue ou rabais disponible pour ce week", "Aucun catalogue ou rabais disponible pour ce week")
        return {"success": False, "error": "Aucun catalogue ou rabais disponible pour ce week"}

    try:
        sample_size = int(sample_size)
    except (TypeError, ValueError):
        sample_size = 8

    sample_size = max(1, min(sample_size, 50))

    catalog_subset = []
    discounts_subset = []
    used_discount_ids = set()

    for catalog_id, catalog_name in catalog:
        normalized_catalog = _normalize_text(catalog_name)
        if not normalized_catalog:
            continue
        catalog_tokens = set(normalized_catalog.split())

        for discount in discounts:
            discount_id = discount[0]
            discount_name = discount[1]
            if discount_id in used_discount_ids:
                continue
            normalized_discount = _normalize_text(discount_name)
            if not normalized_discount:
                continue
            discount_tokens = set(normalized_discount.split())

            if normalized_catalog in normalized_discount or catalog_tokens & discount_tokens:
                discounts_subset.append(discount)
                used_discount_ids.add(discount_id)
                catalog_subset.append((catalog_id, catalog_name))
                break

        if len(catalog_subset) >= sample_size:
            break

    used_fallback = not catalog_subset
    if used_fallback:
        catalog_subset = catalog[:sample_size]
        discounts_subset = discounts[:sample_size]

    prompt = _build_gemini_prompt(catalog_subset, discounts_subset, sample_size=None)

    if status_cb:
        status_cb(
            f"Test Gemini sur {len(catalog_subset)} produits et {len(discounts_subset)} rabais"
            + (" (fallback, aucun recoupement trouvé)" if used_fallback else ""),
            "..."
        )

    if model is None:
        return {"success": False, "error": "Aucun modèle Gemini disponible", "prompt": prompt}

    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )
        payload = response.text.strip()
        parsed = _parse_gemini_matches(payload)
        return {
            "success": True,
            "catalog_count": len(catalog_subset),
            "discount_count": len(discounts_subset),
            "used_fallback": used_fallback,               # ← nouveau
            "catalog_names": [c[1] for c in catalog_subset],     # ← nouveau
            "discount_names": [d[1] for d in discounts_subset],  # ← nouveau
            "prompt": prompt,
            "raw_response": payload,
            "parsed_matches": parsed,
        }
    except Exception as exc:
        if status_cb:
            status_cb(f"Test Gemini échoué : {exc}", f"Test Gemini échoué : {exc}")
        return {"success": False, "error": str(exc), "prompt": prompt}


def matchCatalogWithDiscounts(week_start, status_cb=None, catalog_batch_size=40):
    catalog = getCatalogItems()
    discounts = getDiscountsForWeek(week_start)

    if not catalog or not discounts:
        if status_cb:
            status_cb("Aucun catalogue ou rabais disponible pour ce week", "Aucun catalogue ou rabais disponible pour ce week")
        return

    if status_cb:
        status_cb(
            f"Analyse de {len(catalog)} produits du catalogue et {len(discounts)} rabais",
            f"Analyse de {len(catalog)} produits du catalogue et {len(discounts)} rabais"
        )

    matches = []
    matched_catalog_ids = set()

    if model is not None:
        total_batches = (len(catalog) + catalog_batch_size - 1) // catalog_batch_size

        for batch_index in range(total_batches):
            start = batch_index * catalog_batch_size
            end = start + catalog_batch_size
            catalog_batch = catalog[start:end]

            if status_cb:
                status_cb(
                    f"Gemini : lot {batch_index + 1}/{total_batches} ({len(catalog_batch)} produits)…",
                    f"Gemini : lot {batch_index + 1}/{total_batches} ({len(catalog_batch)} produits)…"
                )

            try:
                prompt = _build_gemini_prompt(catalog_batch, discounts)
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "response_mime_type": "application/json"
                    }
                )
                payload = response.text.strip()
                parsed = _parse_gemini_matches(payload)

                matches.extend(parsed)
                matched_catalog_ids.update(m["catalog_id"] for m in parsed)

                if status_cb:
                    status_cb(
                        f"Lot {batch_index + 1}/{total_batches} : {len(parsed)} correspondances",
                        f"Lot {batch_index + 1}/{total_batches} : {len(parsed)} correspondances"
                    )
            except Exception as exc:
                if status_cb:
                    status_cb(
                        f"Lot {batch_index + 1}/{total_batches} échoué : {exc}",
                        f"Lot {batch_index + 1}/{total_batches} échoué : {exc}"
                    )
                print(f"⚠️ Gemini batch {batch_index + 1} failed: {exc}")
                continue

    # 👇 SAUVEGARDE IMMÉDIATE des matches Gemini, avant de risquer le fallback
    if matches:
        if status_cb:
            status_cb(f"Enregistrement de {len(matches)} correspondances Gemini en base", f"Enregistrement de {len(matches)} correspondances Gemini en base")
        saveCatalogDiscountMatches(matches, week_start)
        print(f"✅ Saved {len(matches)} Gemini catalog/discount matches for week {week_start} (before fallback)")

    # Fallback heuristique uniquement pour les items non couverts par Gemini
    uncovered_catalog = [c for c in catalog if c[0] not in matched_catalog_ids]
    if uncovered_catalog:
        if status_cb:
            status_cb(
                f"Fallback heuristique pour {len(uncovered_catalog)} produits non matchés par Gemini…",
                f"Fallback heuristique pour {len(uncovered_catalog)} produits non matchés par Gemini…"
            )
        try:
            fallback_matches = _build_fallback_matches(uncovered_catalog, discounts, status_cb=status_cb)
        except Exception as exc:
            # 👇 Le fallback ne doit JAMAIS effacer le travail déjà sauvegardé
            if status_cb:
                status_cb(f"Fallback heuristique échoué : {exc}", f"Fallback heuristique échoué : {exc}")
            print(f"⚠️ Heuristic fallback failed: {exc}")
            fallback_matches = []

        if fallback_matches:
            # 👇 Combine avec les matches Gemini déjà sauvegardés pour ne pas les écraser
            all_matches = matches + fallback_matches
            if status_cb:
                status_cb(f"Enregistrement de {len(all_matches)} correspondances (Gemini + heuristique) en base", f"Enregistrement de {len(all_matches)} correspondances en base")
            saveCatalogDiscountMatches(all_matches, week_start)
            print(f"✅ Saved {len(all_matches)} total catalog/discount matches for week {week_start}")
            return

    if not matches:
        if status_cb:
            status_cb("Aucune correspondance générée", "Aucune correspondance générée")
        print("⚠️ No catalog/discount matches generated")