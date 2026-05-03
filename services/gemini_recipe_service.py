"""Gemini 2.5 Flash recipe generation with JSON output and mock fallback."""
import json
import os
import re
from typing import Any, Dict, List, Optional

from config import Config

# Optional import so unit tests can load module without google-genai
try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None  # type: ignore
    types = None  # type: ignore


def _has_any(tokens: List[str], *keywords: str) -> bool:
    tl = [t.lower() for t in tokens]
    for k in keywords:
        kl = k.lower()
        for t in tl:
            if kl in t or t in kl:
                return True
    return False


def _scale_note(servings: int, base: int = 2) -> str:
    if servings <= 0:
        servings = 2
    if base <= 0:
        base = 2
    return f"{servings} хүнд тохируулсан орц (суурь {base} хүнээс тооцоолсон)"


def generate_mock_recipe(
    mood: str,
    ingredients: List[str],
    matched_ingredients: List[Any],
    missing_ingredients: List[str],
    weather: str,
    meal_time: str,
    servings: int,
    time_limit: str,
    food_style: str,
    base_recipe: Optional[Dict[str, Any]] = None,
    external_recipe: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Rule-based warm Mongolian-style recipe when Gemini is unavailable."""
    tokens = ingredients[:]
    title = "Гэрийн дулаахан хоол"
    steps: List[str] = []
    ing_list: List[Dict[str, str]] = []
    short_reason = "Гэрт байгаа орцоор хурдан, амттай хоолыг санал болгож байна."
    substitution_tips: List[str] = []
    child_note = "Хүүхдүүдэд зөөлөн амттай — давс, перецээ өөрсдөө тохируулна уу."
    storage = "Үлдэгнийг хөргөгчинд шилээр хадгалж, 2 хоногийн дотор идээрэй."
    warm = "Өнөөдөр ч гэсэн гэр бүлээрээ дулаан суух цаг гаргасан танд баярлалаа."

    if meal_time == "Хүүхдийн хоол":
        child_note = "Хүүхдэд зориулсан зөөлөн амт — халуун, жижиглэж өгнө үү."

    if _has_any(tokens, "будаа", "rice") and _has_any(tokens, "өндөг", "egg"):
        title = "Өндөгтэй шарсан будаа"
        short_reason = "Өндөг, будаа хосолсон нь ядарсан өдөр ч хурдан эрч хүч өгнө."
        ing_list = [
            {"name": "будаа", "amount": f"{max(1, servings // 2)} аяга", "note": "урьдчилан чанаж болно"},
            {"name": "өндөг", "amount": f"{servings} ширхэг", "note": ""},
            {"name": "тос", "amount": "1-2 хоолны халбага", "note": ""},
            {"name": "сонгино", "amount": "жижиг 1/2", "note": "сонголттой"},
        ]
        steps = [
            "Тосоо халааж, сонгиноо шарна.",
            "Өндгөө нэмж, зөөлөн хутгана.",
            "Будаагаа нэмээд давс, перецээр амтлаад хамт дунд гал дээр 5-7 минут шарна.",
            "Ширээн дээр халуун байхад нь өгнө үү.",
        ]
    elif _has_any(tokens, "төмс", "potato") and _has_any(tokens, "мах", "тахиа", "үхэр", "хонь", "chicken", "beef"):
        title = "Төмстэй хуурга"
        short_reason = "Төмс, махны хослол гэр бүлийн хоолонд тохиромжтой."
        ing_list = [
            {"name": "төмс", "amount": f"{servings} ширхэгт тохируулан", "note": "жижиг хэрчмээр"},
            {"name": "мах (тахиа/үхэр/хонь)", "amount": f"{servings * 80}-{servings * 100} г", "note": ""},
            {"name": "сонгино", "amount": "1 ширхэг", "note": ""},
            {"name": "сармис", "amount": "2-3 хумс", "note": ""},
            {"name": "тос", "amount": "2 хоолны халбага", "note": ""},
        ]
        steps = [
            "Төмс, махаа жижиглэж бэлтгэнэ.",
            "Тосоо халааж махаа шарна.",
            "Төмс нэмээд зөөлөртөл нь жигд гал дээр шарна.",
            "Давс, перецээр амтлаад гэр бүлээрээ халуун иднэ үү.",
        ]
    elif _has_any(tokens, "гурил", "flour") and _has_any(tokens, "мах", "тахиа", "үхэр", "хонь"):
        title = "Гурилтай шөл"
        short_reason = "Хүйтэн, бүрхэг өдөр дотор талдаа дулаацуулах шөл."
        ing_list = [
            {"name": "гурил", "amount": "1 аяга", "note": "гурилан боодог хийхэд"},
            {"name": "мах", "amount": f"{servings * 60} г", "note": ""},
            {"name": "лууван", "amount": "1 ширхэг", "note": ""},
            {"name": "сонгино", "amount": "1 ширхэг", "note": ""},
            {"name": "давс", "amount": "зөвхөн амтлахад", "note": ""},
        ]
        steps = [
            "Мах, ногоогоо жижиглэнэ.",
            "Шөлний усаа буцалгаж, махаа чанаана.",
            "Гурилаар жижиг боодог хийж нэмнэ.",
            "15-20 минут дунд зэргийн гал дээр буцалгана.",
        ]
    elif _has_any(tokens, "гоймон", "noodle") and _has_any(tokens, "өндөг", "egg"):
        title = "Өндөгтэй гоймон"
        short_reason = "Хөнгөн, хурдан — оройн завгүй цагт тохиромжтой."
        ing_list = [
            {"name": "гоймон", "amount": f"{servings} хүнд 1 боодол", "note": ""},
            {"name": "өндөг", "amount": f"{servings} ширхэг", "note": ""},
            {"name": "сонгино", "amount": "1/2 ширхэг", "note": ""},
            {"name": "соус (улаан лоолийн/соя)", "amount": "1-2 хоолны халбага", "note": ""},
        ]
        steps = [
            "Гоймонгоо зааврын дагуу чанаана.",
            "Тосоо халааж өндөг, сонгиноо шарна.",
            "Гоймонгоо нэмж, соусоор амтлана.",
            "Дээрээ ногоон сонгиноо цацна уу.",
        ]
    else:
        # Generic cozy one-pot style
        if weather in ("Хүйтэн", "Цастай", "Бороотой"):
            title = "Ногоотой дулаан шөл"
            short_reason = "Цаг агаар хүйтэн байхад дотор тал тань дулаан байхад тусална."
        elif mood == "Ядарсан":
            title = "Хурдан ногоотой будаа"
            short_reason = "Бага завтай үед ч гэсэн шууд хийж болох хөнгөн хоол."
        else:
            title = "Гэрийн хуурга"
            short_reason = "Гэрт байгаа орцоор уян хатан хийж болох гэрийн хоол."

        for t in tokens[:6]:
            ing_list.append({"name": t, "amount": "хэрэглэхэд тохируулан", "note": ""})
        if not ing_list:
            ing_list = [
                {"name": "будаа эсвэл төмс", "amount": "1 аяга", "note": "аль нэг байвал хангалттай"},
                {"name": "өндөг эсвэл мах", "amount": f"{servings * 50} г орчим", "note": ""},
            ]
        steps = [
            "Орцоо угааж, жижиглэн бэлтгэнэ.",
            "Тосоо халааж үндсэн орцоо шарна.",
            "Давс, перецээр амтлаад {0} минут орчим жигд гал дээр болгоно.".format(
                15 if "15" in time_limit else 25
            ),
            "Халуун байхад нь ширээн дээр өгнө үү.",
        ]

    if missing_ingredients:
        substitution_tips.append(
            "Дутуу орцонд: төмс байвал лууваны оронд, сүү байвал тарагны оронд ашиглаж болно."
        )
    substitution_tips.append("Өөрийн гэрийн амтад тохируулан давс, перецээ бага багаар нэмнэ үү.")

    if weather in ("Хүйтэн", "Цастай"):
        warm += " Хүйтэн өдөр халуун хоол идсэн чинь бие тавгүй байдлыг намдаана."

    prep = time_limit if time_limit else "30 минут"

    return {
        "title": title,
        "short_reason": short_reason,
        "servings": max(1, servings),
        "prep_time": prep,
        "ingredients": ing_list,
        "steps": steps,
        "substitution_tips": substitution_tips,
        "serving_tips": "Шинэхэн халуун байхад нь идэхэд хамгийн амттай. Салат, тарагтай хослуулбал зүгээр.",
        "child_friendly_note": child_note,
        "storage_note": storage,
        "warm_message": warm,
        "source": "mock",
        "image_url": "",
        "origin": "mock",
    }


def _build_prompt(
    mood: str,
    ingredients: List[str],
    matched_ingredients: str,
    missing_ingredients: str,
    weather: str,
    meal_time: str,
    servings: int,
    time_limit: str,
    food_style: str,
    base_recipe: Optional[Any],
    external_recipe: Optional[Any],
) -> str:
    base_txt = json.dumps(base_recipe, ensure_ascii=False) if base_recipe else "байхгүй"
    ext_txt = json.dumps(external_recipe, ensure_ascii=False) if external_recipe else "байхгүй"
    ing_txt = ", ".join(ingredients)

    return f"""You are a warm Mongolian home cooking assistant for housewives, mothers, and family home cooks.

You must create one practical recipe in Mongolian.

User context:
- Mood: {mood}
- Weather: {weather}
- Meal time: {meal_time}
- Servings: {servings}
- Available ingredients: {ing_txt}
- Matched database ingredients: {matched_ingredients}
- Missing or unmatched ingredients: {missing_ingredients}
- Cooking time limit: {time_limit}
- Food style: {food_style}

Best local recipe candidate:
{base_txt}

External MealDB recipe candidate:
{ext_txt}

Rules:
1. Use available ingredients as much as possible.
2. Do not require many unavailable ingredients.
3. If an ingredient is missing, suggest a simple substitute common in Mongolian homes.
4. Adjust ingredient amounts for {servings} people.
5. Make the recipe suitable for the selected mood and weather.
6. Use a warm, friendly, cozy home-kitchen tone.
7. Make it understandable for a busy housewife or mother.
8. Include whether children can eat it.
9. Include storage or leftover note.
10. Do not mention that you are an AI.
11. Do not mention API, MealDB, database, or Gemini to the user.
12. Return only valid JSON. No markdown. No explanation outside JSON.

JSON format:
{{
  "title": "",
  "short_reason": "",
  "servings": 0,
  "prep_time": "",
  "ingredients": [
    {{
      "name": "",
      "amount": "",
      "note": ""
    }}
  ],
  "steps": [],
  "substitution_tips": [],
  "serving_tips": "",
  "child_friendly_note": "",
  "storage_note": "",
  "warm_message": "",
  "source": "gemini",
  "image_url": ""
}}
"""


def _coerce_recipe_dict(data: Dict[str, Any], image_url: str = "") -> Dict[str, Any]:
    """Ensure required keys exist for templates."""
    out = {
        "title": str(data.get("title") or "Жор"),
        "short_reason": str(data.get("short_reason") or ""),
        "servings": int(data.get("servings") or 2),
        "prep_time": str(data.get("prep_time") or ""),
        "ingredients": data.get("ingredients") or [],
        "steps": data.get("steps") or [],
        "substitution_tips": data.get("substitution_tips") or [],
        "serving_tips": str(data.get("serving_tips") or ""),
        "child_friendly_note": str(data.get("child_friendly_note") or ""),
        "storage_note": str(data.get("storage_note") or ""),
        "warm_message": str(data.get("warm_message") or ""),
        "source": str(data.get("source") or "gemini"),
        "image_url": str(data.get("image_url") or image_url or ""),
        "origin": str(data.get("origin") or "pure"),
    }
    # Normalize ingredient rows
    fixed_ings = []
    for item in out["ingredients"]:
        if isinstance(item, dict):
            fixed_ings.append(
                {
                    "name": str(item.get("name") or ""),
                    "amount": str(item.get("amount") or ""),
                    "note": str(item.get("note") or ""),
                }
            )
    out["ingredients"] = fixed_ings
    if not isinstance(out["steps"], list):
        out["steps"] = [str(out["steps"])]
    else:
        out["steps"] = [str(s) for s in out["steps"]]
    if not isinstance(out["substitution_tips"], list):
        out["substitution_tips"] = [str(out["substitution_tips"])]
    else:
        out["substitution_tips"] = [str(s) for s in out["substitution_tips"]]
    return out


def _strip_json_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def generate_recipe(
    mood: str,
    ingredients: List[str],
    matched_ingredients: Any,
    missing_ingredients: List[str],
    weather: str,
    meal_time: str,
    servings: int,
    time_limit: str,
    food_style: str,
    base_recipe: Optional[Dict[str, Any]] = None,
    external_recipe: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Try Gemini 2.5 Flash JSON mode; on failure or missing key, use mock generator.
    """
    matched_txt = (
        ", ".join([m.name for m in matched_ingredients])
        if matched_ingredients
        else "байхгүй"
    )
    missing_txt = ", ".join(missing_ingredients) if missing_ingredients else "байхгүй"

    origin = "pure"
    if base_recipe:
        origin = "local"
    elif external_recipe:
        origin = "mealdb"

    ext_image = ""
    if external_recipe and isinstance(external_recipe, dict):
        ext_image = str(external_recipe.get("image") or "")

    api_key = Config.GEMINI_API_KEY
    model = Config.GEMINI_MODEL or "gemini-2.5-flash"

    if not api_key or genai is None or types is None:
        mock = generate_mock_recipe(
            mood,
            ingredients,
            matched_ingredients,
            missing_ingredients,
            weather,
            meal_time,
            servings,
            time_limit,
            food_style,
            base_recipe,
            external_recipe,
        )
        mock["origin"] = "mock"
        return mock

    prompt = _build_prompt(
        mood,
        ingredients,
        matched_txt,
        missing_txt,
        weather,
        meal_time,
        servings,
        time_limit,
        food_style,
        base_recipe,
        external_recipe,
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,
                response_mime_type="application/json",
            ),
        )
        raw_text = getattr(response, "text", None) or ""
        if not raw_text and response.candidates:
            # Some SDK versions nest text
            parts = []
            for c in response.candidates:
                for p in getattr(c.content, "parts", []) or []:
                    if getattr(p, "text", None):
                        parts.append(p.text)
            raw_text = "\n".join(parts)

        cleaned = _strip_json_fence(raw_text)
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("Gemini JSON not an object")
        data["source"] = "gemini"
        data["origin"] = origin
        if ext_image and not data.get("image_url"):
            data["image_url"] = ext_image
        return _coerce_recipe_dict(data, ext_image)
    except Exception as exc:
        if os.getenv("FLASK_ENV") == "development" or os.getenv("FLASK_DEBUG"):
            print(f"[Gemini] generation failed, using mock: {exc}")
        mock = generate_mock_recipe(
            mood,
            ingredients,
            matched_ingredients,
            missing_ingredients,
            weather,
            meal_time,
            servings,
            time_limit,
            food_style,
            base_recipe,
            external_recipe,
        )
        mock["origin"] = "mock"
        if ext_image:
            mock["image_url"] = ext_image
        return mock
