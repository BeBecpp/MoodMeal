"""TheMealDB API client — resilient, no crashes on network errors."""
import os
from typing import Any, Dict, List, Optional

import requests

from config import Config


class MealDBService:
    """Thin wrapper around TheMealDB JSON API."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or Config.MEALDB_BASE_URL).rstrip("/")
        self.api_key = api_key or Config.MEALDB_API_KEY
        self._root = f"{self.base_url}/{self.api_key}"
        self._timeout = 12

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        url = f"{self._root}/{endpoint.lstrip('/')}"
        try:
            resp = requests.get(url, params=params or {}, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if os.getenv("FLASK_ENV") == "development" or os.getenv("FLASK_DEBUG"):
                print(f"[MealDB] request failed: {url} — {exc}")
            return None

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        data = self._get("search.php", {"s": name})
        if not data or "meals" not in data or data["meals"] is None:
            return []
        return list(data["meals"])

    def filter_by_ingredient(self, ingredient: str) -> List[Dict[str, Any]]:
        """Filter meals by single ingredient (MealDB free API limitation)."""
        data = self._get("filter.php", {"i": ingredient})
        if not data or "meals" not in data or data["meals"] is None:
            return []
        return list(data["meals"])

    def lookup_by_id(self, meal_id: str) -> Optional[Dict[str, Any]]:
        data = self._get("lookup.php", {"i": meal_id})
        if not data or "meals" not in data or not data["meals"]:
            return None
        return data["meals"][0]

    def random_meal(self) -> Optional[Dict[str, Any]]:
        data = self._get("random.php")
        if not data or "meals" not in data or not data["meals"]:
            return None
        return data["meals"][0]

    def extract_ingredients(self, meal: Dict[str, Any]) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}") or ""
            meas = meal.get(f"strMeasure{i}") or ""
            ing = ing.strip()
            meas = meas.strip()
            if ing:
                out.append({"name": ing, "measure": meas})
        return out

    def normalize_meal(self, meal: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize MealDB meal dict for prompts / templates."""
        ingredients = self.extract_ingredients(meal)
        return {
            "id": meal.get("idMeal") or "",
            "title": meal.get("strMeal") or "",
            "category": meal.get("strCategory") or "",
            "area": meal.get("strArea") or "",
            "instructions": meal.get("strInstructions") or "",
            "image": meal.get("strMealThumb") or "",
            "youtube": meal.get("strYoutube") or "",
            "source": meal.get("strSource") or "",
            "ingredients": ingredients,
        }

    def find_best_meal_for_pantry(
        self,
        english_terms: List[str],
        user_tokens: List[str],
        max_summaries: int = 22,
        max_lookups: int = 14,
    ) -> Optional[Dict[str, Any]]:
        """
        Merge filter.php results per ingredient, lookup meals, pick best overlap
        for Gemini context + strMealThumb illustration image.
        """
        if not english_terms and not user_tokens:
            return None

        seen_ids: set = set()
        summaries: List[Dict[str, Any]] = []

        for term in english_terms:
            for m in self.filter_by_ingredient(term):
                mid = m.get("idMeal")
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    summaries.append(m)
            if len(summaries) >= max_summaries:
                break

        # Secondary: name search on first English token for more variety / images
        if english_terms:
            primary = english_terms[0].replace("_", " ")
            if len(primary) >= 3:
                for m in self.search_by_name(primary)[:5]:
                    mid = m.get("idMeal")
                    if mid and mid not in seen_ids:
                        seen_ids.add(mid)
                        summaries.append(m)

        if not summaries:
            return None

        user_lower = [t.lower().strip() for t in user_tokens if t.strip()]
        best: Optional[Dict[str, Any]] = None
        best_score = -1.0

        for m in summaries[:max_summaries]:
            mid = m.get("idMeal")
            if not mid:
                continue
            full = self.lookup_by_id(mid)
            if not full:
                continue
            norm = self.normalize_meal(full)
            sc = self._score_meal_overlap(norm, english_terms, user_lower)
            if norm.get("image"):
                sc += 0.35
            if sc > best_score:
                best_score = sc
                best = norm
            max_lookups -= 1
            if max_lookups <= 0:
                break

        # Fallback: any MealDB hit with a thumbnail (better than no photo)
        if best is None or not (best.get("image") or "").strip():
            for m in summaries[:10]:
                mid = m.get("idMeal")
                if not mid:
                    continue
                full = self.lookup_by_id(mid)
                if not full:
                    continue
                norm = self.normalize_meal(full)
                if (norm.get("image") or "").strip():
                    return norm
                if best is None:
                    best = norm

        return best

    @staticmethod
    def _score_meal_overlap(
        norm: Dict[str, Any],
        english_terms: List[str],
        user_tokens_lower: List[str],
    ) -> float:
        score = 0.0
        ing_blob = " ".join(
            (i.get("name") or "").lower() for i in norm.get("ingredients", [])
        )
        title_l = (norm.get("title") or "").lower()

        for raw in english_terms:
            e = raw.lower().replace("_", " ").strip()
            if len(e) < 2:
                continue
            parts = e.split()
            for p in parts:
                if len(p) >= 3 and p in ing_blob:
                    score += 2.0
            if e in ing_blob:
                score += 1.5
            if e in title_l:
                score += 0.5

        # Light boost if Mongolian token appears in English ingredient (rare)
        for u in user_tokens_lower:
            if len(u) >= 4 and u in ing_blob:
                score += 0.25

        return score
