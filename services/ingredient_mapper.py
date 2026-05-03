"""Parse user ingredient text and map Mongolian names to TheMealDB English tokens."""
import re
from typing import List

# Mongolian / common variants -> TheMealDB-friendly English ingredient search terms
MEALDB_INGREDIENT_MAP = {
    "тахианы мах": "chicken",
    "тахиан": "chicken",
    "тахиа": "chicken",
    "тахианы цээж": "chicken_breast",
    "үхрийн мах": "beef",
    "үхэр": "beef",
    "мах": "beef",
    "хонины мах": "lamb",
    "хонь": "lamb",
    "өндөг": "egg",
    "төмс": "potatoes",
    "лууван": "carrot",
    "сонгино": "onion",
    "ногоон сонгино": "spring_onions",
    "сармис": "garlic",
    "байцаа": "cabbage",
    "будаа": "rice",
    "гоймон": "noodles",
    "гурил": "flour",
    "мантууны гурил": "flour",
    "сүү": "milk",
    "тараг": "yogurt",
    "бяслаг": "cheese",
    "улаан лооль": "tomatoes",
    "улаан лоолийн соус": "tomato_ketchup",
    "кимчи": "kimchi",
    "загас": "fish",
    "сам хорхой": "prawns",
    "өргөст хэмх": "cucumber",
    "овьёос": "oats",
    "масло": "butter",
    "тос": "butter",
    "давс": "salt",
    "перец": "pepper",
    "цуу": "vinegar",
    "зөгий": "honey",
}


def parse_user_ingredients(text: str) -> List[str]:
    """Split textarea input into normalized lowercase ingredient tokens."""
    if not text or not text.strip():
        return []
    # Replace newlines with commas, normalize separators
    raw = text.replace("\n", ",").replace(";", ",")
    raw = re.sub(r"\s*болон\s*", ",", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*ба\s*", ",", raw, flags=re.IGNORECASE)
    parts = re.split(r"[,，]", raw)
    result: List[str] = []
    seen = set()
    for part in parts:
        name = part.strip().lower()
        name = re.sub(r"\s+", " ", name)
        if not name:
            continue
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _normalize_key(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def map_to_mealdb_ingredients(user_ingredients: List[str]) -> List[str]:
    """
    Map each user ingredient string to a MealDB search ingredient.
    Longer keys are matched first to avoid partial wrong matches.
    """
    if not user_ingredients:
        return []

    sorted_keys = sorted(MEALDB_INGREDIENT_MAP.keys(), key=len, reverse=True)
    mapped: List[str] = []
    seen = set()

    for raw in user_ingredients:
        key = _normalize_key(raw)
        english = None
        for mk in sorted_keys:
            if mk in key or key in mk:
                english = MEALDB_INGREDIENT_MAP[mk]
                break
        if english is None:
            # fallback: use cleaned token as-is (MealDB may still match)
            english = key.replace(" ", "_")

        eng_key = english.lower()
        if eng_key not in seen:
            seen.add(eng_key)
            mapped.append(english)

    return mapped
