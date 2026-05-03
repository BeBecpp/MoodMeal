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
