"""Score local recipes against user context and pantry overlap."""
import re
from typing import Any, Dict, List, Optional, Tuple

from models import Recipe

# meal_time option labels from the form (Mongolian)
MEAL_TIME_CHILD = "Хүүхдийн хоол"


def _parse_tags(tag_str: Optional[str]) -> List[str]:
    if not tag_str:
        return []
    parts = re.split(r"[,;|]", tag_str)
    return [p.strip().lower() for p in parts if p.strip()]


def _time_limit_to_minutes(label: str) -> int:
    mapping = {
        "15 минут": 15,
        "30 минут": 30,
        "45 минут": 45,
        "1 цаг+": 999,
    }
    return mapping.get(label, 60)


def score_recipe(
    recipe: Recipe,
    user_ingredient_tokens: List[str],
    meal_time: str,
    mood: str,
    weather: str,
    food_style: str,
    time_limit_label: str,
) -> float:
    """Higher is better."""
    score = 0.0
    limit_min = _time_limit_to_minutes(time_limit_label)

    # Ingredient overlap with recipe lines
    user_lower = [t.lower() for t in user_ingredient_tokens]
    for line in recipe.ingredients:
        name_l = line.ingredient_name.lower()
        for u in user_lower:
            if u in name_l or name_l in u:
                score += 3.0
                break

    if recipe.meal_time and meal_time and recipe.meal_time.strip() == meal_time.strip():
        score += 4.0

    mood_tags = _parse_tags(recipe.mood_tags)
    if mood_tags and mood.lower() in mood_tags:
        score += 2.0

    weather_tags = _parse_tags(recipe.weather_tags)
    if weather_tags and weather.lower() in weather_tags:
        score += 2.0

    if recipe.food_style and food_style and recipe.food_style.strip() == food_style.strip():
        score += 2.0

    if recipe.cook_time_minutes and recipe.cook_time_minutes <= limit_min:
        score += 2.0

    if meal_time == MEAL_TIME_CHILD and recipe.child_friendly:
        score += 2.0

    return score


def find_best_candidates(
    user_ingredient_tokens: List[str],
    meal_time: str,
    mood: str,
    weather: str,
    food_style: str,
    time_limit_label: str,
    top_n: int = 5,
) -> Tuple[List[Tuple[Recipe, float]], Optional[Recipe], float]:
    """
    Returns (ranked list of (recipe, score), best recipe or None, best score).
    """
    recipes: List[Recipe] = Recipe.query.filter_by(source="local").all()
    ranked: List[Tuple[Recipe, float]] = []
    for r in recipes:
        s = score_recipe(
            r,
            user_ingredient_tokens,
            meal_time,
            mood,
            weather,
            food_style,
            time_limit_label,
        )
        ranked.append((r, s))
    ranked.sort(key=lambda x: x[1], reverse=True)
    top = ranked[:top_n]
    best = top[0] if top else None
    best_recipe = best[0] if best and best[1] > 0 else None
    best_score = best[1] if best else 0.0
    return top, best_recipe, best_score


def is_strong_local_match(score: float, user_tokens: List[str]) -> bool:
    """Heuristic: strong if score is high enough relative to pantry size."""
    if score >= 10:
        return True
    if len(user_tokens) >= 3 and score >= 7:
        return True
    if len(user_tokens) <= 2 and score >= 5:
        return True
    return False


def recipe_to_prompt_dict(recipe: Recipe) -> Dict[str, Any]:
    """Serialize SQLAlchemy recipe for Gemini prompt."""
    ings = [
        {
            "name": ri.ingredient_name,
            "amount": ri.amount or "",
            "unit": ri.unit or "",
            "substitute": ri.substitute_options or "",
        }
        for ri in recipe.ingredients
    ]
    return {
        "title": recipe.title,
        "description": recipe.description or "",
        "meal_time": recipe.meal_time or "",
        "mood_tags": recipe.mood_tags or "",
        "weather_tags": recipe.weather_tags or "",
        "food_style": recipe.food_style or "",
        "base_servings": recipe.base_servings,
        "cook_time_minutes": recipe.cook_time_minutes,
        "difficulty": recipe.difficulty,
        "child_friendly": recipe.child_friendly,
        "instructions": recipe.instructions,
        "ingredients": ings,
    }
