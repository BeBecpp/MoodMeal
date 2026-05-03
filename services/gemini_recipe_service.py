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
            "Бэлтгэл: будаагаа угааж хэдэн удаа усанд хийгээд шүүгээр шүүгээд 10-15 минут усанд дэвтээнэ (шууд чанаж болох ч ийм бол амт илүү сайн). Сонгиноо маш жижиглэн хэрчинэ.",
            "Том ёслын эсвэл гүн тавагт 1-2 хоолны халбага тосоо хийж дунд гал дээр 1-2 минут халаана. Тос бага зэрэг хөдөлж эхлэхэд сонгиноо хийж 2-3 минут зөөлөн шарна — шатаахгүйгээр анхаарна.",
            "Өндгийг саванд хөнгөн цохиод давс бага зэрэг хийнэ. Сонгинон дээрээ нэмээд 1 минут орчим зөөлөн хутгана.",
            "Урьдчилан бэлтгэсэн будаагаа (эсвэл өчигдрийн будаа) нэмж, тос, өндөгтэйгоо сайтар холиулна. Гал дунд зэрэгт байлга.",
            "Давс, перецээр амтлаад 5-7 минут орчим хөдөлгөөнтэйгээр шарна. Давс багаас эхлээд дараа нь нэмж болно.",
            "Өндөг бүрэн болж, будаа алтаар шарсан өнгөтэй, хэсэг хэсгээрээ ялгарч харагдахад бэлэн. Хэрэв хуурай байвал нэг халбага ус нэмж чийглэг болгоно.",
            "Ширээн дээр халуун байхад нь хүүхдүүдэд жижиглэж, том хүмүүст салаттай хамт өгнө үү.",
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
            "Төмсөө хальслаад угааж, махтай ойролцоо жижиг хэрчим болгоно. Махыг шүүс гаргахгүйн тулд алганы даралтгүйгээр хэсэглэнэ.",
            "Том саванд 2 хоолны халбага тосоо хийж дунд-их гал дээр халаана. Махаа нэг давхарга болгоод жигд тавьж, нэг тал нь цайвар шаргал болтол 4-6 минут шарна.",
            "Махаа эргүүлээд нөгөө талыг мөн адил шарна. Одоо төмсөө нэмээд 2-3 минут холиуна.",
            "Галыг бага зэрэг багасгаад, таглаагүйгээр 12-18 минут орчим төмс зөөлөртөл нь шарна. Дундаа хөдөлгөөнтэй хутгана.",
            "Сармисыг нэмээд 1 минут үнэртэнэ гэсэн хэмжээнд шарна. Давс, перец, хүсвэл улаан лоолийн соус бага зэрэг.",
            "Шүүс бага зэрэг үлдээд, гадуур нь гялгар өнгөтэй болсон эсэхийг шалгана. Хэрвээ хуурай бол 2-3 хоолны халбага ус нэмж чийглэг болгоно.",
            "Халуун байхад нь будаа эсвэл талхтай өгнө. Үлдсэнийг хөргөгчинд хадгалбал дахин халаахад ч амттай.",
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
            "Махаа жижиглэн угааж, хүйтэн усанд 5 минут дэвтээнэ (цусны хөөс арилгахад тустай). Лууван, сонгиноо хэрчинэ.",
            "Том саванд 1.5-2 литр ус буцалгаж, махаа хийгээд анхны хөөсийг хутгаар авна. Давс бага зэрэг нэмээд дунд гал дээр 25-35 минут чанаана.",
            "Гурилд бага давс, ус нэмж зөөлөн зуурма болгоно. 10 минут амраана.",
            "Зуурмаа жижиг дөрвөлжин хэрчээд махны шөлөнд хийж 8-10 минут чанаана — боодог өөдөөсөө дээш гарч ирнэ.",
            "Лууван, сонгиноо сүүлийн 10 минутад нэмж, шөлний амтыг нэг мөр болгоно.",
            "Бэлэн болсон шинж: мах зөөлөн, боодог дунд нь цагаан биш, шөл тунгалаг. Перец, ногоон сонгиноор амтлана.",
            "Халуун ширээн дээр өгөөд, үлдэгнийг маргааш өглөөний цайнд дахин халааж болно.",
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
            "Ус буцалгаж бага давс нэмээд гоймонгоо зааврын дагуу 1-2 минут бага илүү чанаана (хэт болохгүй). Шүүгээд 1 хоолны халбага тосоор хөнгөн холиуна.",
            "Өөр саванд 1 хоолны халбага тосоо халааж, сонгиноо 1 минут зөөлөн шарна.",
            "Өндгийг нэмж зөөлөн самнаад, бага зэрэг давстай. Гал дунд зэрэгт 1-2 минут болгоно.",
            "Гоймонгоо буцааж нэмээд соус (улаан лоолийн эсвэл соя) 1-2 хоолны халбагаар амтлана. 2-3 минут хамт халаана.",
            "Хэрвээ хуурай бол нэг халбага ус нэмж гөлгөр болгоно. Эцэст нь перец, ногоон сонгино.",
            "Шууд халуун идэхэд хамгийн амттай — хүүхдэд жижиглэж өгнө үү.",
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
        cook_mins = 12 if "15" in time_limit else (20 if "30" in time_limit else 28)
        steps = [
            "Орц бүрийг угааж, хэрэглэх хэмжээгээр жижиглэн хэрчинэ. Мах байвал шүүс гаргахгүйн тулд алганы даралтгүйгээр хэсэглэнэ.",
            "Том ёслын эсвэл гүн тавагт 2 хоолны халбага тосыг дунд гал дээр халаана. Тос хөдөлж эхлэхэд сонгино (байвал) нэмээд 2 минут үнэртүүлнэ.",
            "Үндсэн орц (мах/өндөг/ногоо) — аль нь байна түүнийгээ нэг давхаргаар тавьж эхний талыг 3-5 минут шарна. Шатаахгүйн тулд хөдөлгөөнтэй хутгана.",
            "Шаардлагатай бол эргүүлж нөгөө талыг шарна. Дунд гал дээр барьж, орцоо хооронд нь зайтай байлгана.",
            "Давс, перецээр амтлаад {0} минут орчим жигд халааж, дунд зэргийн чийглэгтэй (хэрэгтэй бол 2-3 хоолны халбага ус) болгоно.".format(
                cook_mins
            ),
            "Бэлэн болсон шинж: үндсэн орцны өнгө алтлаг, дундаас нь шингэн бага гарч ирнэ. Хүүхдийн хоол бол давс багасгана.",
            "Халуун байхад нь будаа эсвэл салаттай өгнө. Үлдэгнийг шилэн саванд хадгалж, дахин халаахдаа бага ус нэмж чийглэг болгоно.",
        ]

    if missing_ingredients:
        substitution_tips.append(
            "Дутуу орцонд: төмс байвал лууваны оронд, сүү байвал тарагны оронд ашиглаж болно."
        )
    substitution_tips.append("Өөрийн гэрийн амтад тохируулан давс, перецээ бага багаар нэмнэ үү.")

    if weather in ("Хүйтэн", "Цастай"):
        warm += " Хүйтэн өдөр халуун хоол идсэн чинь бие тавгүй байдлыг намдаана."

    prep = time_limit if time_limit else "30 минут"

    img = ""
    ref_title = ""
    if external_recipe and isinstance(external_recipe, dict):
        img = str(external_recipe.get("image") or "").strip()
        ref_title = str(external_recipe.get("title") or "").strip()

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
        "image_url": img,
        "origin": "mock",
        "mealdb_reference_title": ref_title,
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
6. Use a warm, friendly, cozy home-kitchen tone — бичгийн хэв маяг: ярианы Монгол, товч тодорхой, ээлтэй, зааварлагч (жишээ нь: «одоо...», «анхаараарай...», «бэлэн болсон шинж тэмдэг...»).
7. Жорыг жинхэнэ хоолны жор шиг бич: орц бүрт нэгж (г, мл, хх, аяга, ширхэг, хумс) заавал заана.
8. Хамгийн чухал: "steps" массивт дор хаяж 6-9 алхам байна. Алхам бүр 2-4 өгүүлбэртэй, дараахыг заавал оруул:
   - юу бэлтгэх (хэрчих, угаах, хатаах)
   - ямар сав, ямар хэмжээний тос/ус
   - гал ямар байх (бага/дунд/их), ойролцоогоор хэдэн минут
   - өнгө, үнэр, текстурээр яаж шалгах (жишээ: «алтаар шарсан», «шүүс гарч ирнэ»)
   - дараагийн орцыг хэзээ нэмэх
9. Хүүхэд идэж болох эсэх, хадгалалт, үлдэгнийг яаж ашиглах талаар тодорхой бич.
10. Do not mention that you are an AI.
11. Do not mention API, MealDB, database, or Gemini to the user.
12. image_url талбарыг хоосон үлдээ (хоосон string) — зургийг систем өөрөө TheMealDB-аас холбоно.
13. Return only valid JSON. No markdown. No explanation outside JSON.

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
        "mealdb_reference_title": str(data.get("mealdb_reference_title") or ""),
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


def _apply_mealdb_illustration(
    recipe: Dict[str, Any], external_recipe: Optional[Dict[str, Any]]
) -> None:
    """Mutates recipe: always prefer MealDB thumbnail when we have a candidate."""
    if not external_recipe or not isinstance(external_recipe, dict):
        return
    img = str(external_recipe.get("image") or "").strip()
    if img:
        recipe["image_url"] = img
    ref = str(external_recipe.get("title") or "").strip()
    if ref:
        recipe["mealdb_reference_title"] = ref


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
        _apply_mealdb_illustration(mock, external_recipe)
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
        out = _coerce_recipe_dict(data, ext_image)
        _apply_mealdb_illustration(out, external_recipe)
        return out
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
        _apply_mealdb_illustration(mock, external_recipe)
        return mock
