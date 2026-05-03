"""MoodMeal AI — Flask application entry."""
import json
from typing import Any, Dict, List, Optional

from flask import Flask, flash, redirect, render_template, request, url_for

from config import Config
from models import Ingredient, Recipe, RecipeIngredient, SavedRecipe, db
from services.gemini_recipe_service import generate_recipe
from services.ingredient_mapper import map_to_mealdb_ingredients, parse_user_ingredients
from services.ingredient_service import match_ingredients
from services.mealdb_service import MealDBService
from services.recipe_match_service import (
    find_best_candidates,
    is_strong_local_match,
    recipe_to_prompt_dict,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    mealdb = MealDBService()

    @app.context_processor
    def inject_config():
        return {"gemini_configured": bool(Config.GEMINI_API_KEY)}

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/generate", methods=["POST"])
    def generate():
        mood = (request.form.get("mood") or "").strip()
        ingredients_raw = (request.form.get("ingredients") or "").strip()
        servings_raw = request.form.get("servings") or "2"
        meal_time = (request.form.get("meal_time") or "").strip()
        weather = (request.form.get("weather") or "").strip()
        time_limit = (request.form.get("time_limit") or "").strip()
        food_style = (request.form.get("food_style") or "").strip()

        errors: List[str] = []
        if not ingredients_raw:
            errors.append("Гэрт байгаа орцоо бичнэ үү — жор санал болгоход шаардлагатай.")
        try:
            servings = int(servings_raw)
        except ValueError:
            servings = 0
        if servings < 1:
            errors.append("Хэдэн хүн идэх вэ? — дор хаяж 1 байх ёстой.")

        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("index"))

        user_ingredients = parse_user_ingredients(ingredients_raw)
        if not user_ingredients:
            flash("Орцуудыг таслалаар ялгаж бичнэ үү.", "error")
            return redirect(url_for("index"))

        matched_rows, unmatched = match_ingredients(user_ingredients)
        ranked, best_local, best_score = find_best_candidates(
            user_ingredients,
            meal_time,
            mood,
            weather,
            food_style,
            time_limit,
        )

        base_recipe_dict: Optional[Dict[str, Any]] = None
        external_norm: Optional[Dict[str, Any]] = None

        strong = is_strong_local_match(best_score, user_ingredients)
        if strong and best_local:
            base_recipe_dict = recipe_to_prompt_dict(best_local)

        if not strong:
            english_terms = map_to_mealdb_ingredients(user_ingredients)
            seen_ids = set()
            merged_summaries: List[Dict[str, Any]] = []
            for term in english_terms:
                for m in mealdb.filter_by_ingredient(term):
                    mid = m.get("idMeal")
                    if mid and mid not in seen_ids:
                        seen_ids.add(mid)
                        merged_summaries.append(m)
                if len(merged_summaries) >= 12:
                    break

            best_meal: Optional[Dict[str, Any]] = None
            best_overlap = -1.0
            user_lower = [u.lower() for u in user_ingredients]
            for summary in merged_summaries[:8]:
                mid = summary.get("idMeal")
                if not mid:
                    continue
                full = mealdb.lookup_by_id(mid)
                if not full:
                    continue
                norm = mealdb.normalize_meal(full)
                overlap = 0.0
                for ing in norm.get("ingredients", []):
                    name_l = ing["name"].lower()
                    for u in user_lower:
                        if u in name_l or name_l in u:
                            overlap += 1
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_meal = norm
            if best_meal:
                external_norm = best_meal

        if not strong and not external_norm and best_local:
            base_recipe_dict = recipe_to_prompt_dict(best_local)

        recipe_result = generate_recipe(
            mood=mood,
            ingredients=user_ingredients,
            matched_ingredients=matched_rows,
            missing_ingredients=unmatched,
            weather=weather,
            meal_time=meal_time,
            servings=servings,
            time_limit=time_limit,
            food_style=food_style,
            base_recipe=base_recipe_dict,
            external_recipe=external_norm,
        )

        ctx = {
            "recipe": recipe_result,
            "form": {
                "mood": mood,
                "ingredients": ingredients_raw,
                "servings": servings,
                "meal_time": meal_time,
                "weather": weather,
                "time_limit": time_limit,
                "food_style": food_style,
            },
            "matched": matched_rows,
            "unmatched": unmatched,
            "local_debug": ranked[:3],
        }
        return render_template("result.html", **ctx)

    @app.route("/ingredients")
    def ingredients_list():
        rows = Ingredient.query.order_by(Ingredient.category, Ingredient.name).all()
        return render_template("ingredients.html", ingredients=rows)

    @app.route("/ingredients/add", methods=["GET", "POST"])
    def ingredients_add():
        if request.method == "GET":
            return render_template("add_ingredient.html")
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Нэр заавал оруулна уу.", "error")
            return redirect(url_for("ingredients_add"))
        row = Ingredient(
            name=name,
            name_en=(request.form.get("name_en") or "").strip() or None,
            category=(request.form.get("category") or "other").strip(),
            taste_profile=(request.form.get("taste_profile") or "").strip() or None,
            nutrition_note=(request.form.get("nutrition_note") or "").strip() or None,
            common_pairings=(request.form.get("common_pairings") or "").strip() or None,
            is_common_home_item=bool(request.form.get("is_common")),
        )
        db.session.add(row)
        db.session.commit()
        flash("Орц амжилттай нэмэгдлээ.", "success")
        return redirect(url_for("ingredients_list"))

    @app.route("/saved", methods=["GET", "POST"])
    def saved():
        if request.method == "POST":
            title = (request.form.get("title") or "").strip() or "Хадгалсан жор"
            recipe_content = request.form.get("recipe_content") or ""
            if not recipe_content:
                flash("Хадгалах өгөгдөл байхгүй байна.", "error")
                return redirect(url_for("index"))
            row = SavedRecipe(
                title=title,
                input_mood=request.form.get("input_mood"),
                input_ingredients=request.form.get("input_ingredients"),
                weather=request.form.get("weather"),
                meal_time=request.form.get("meal_time"),
                servings=int(request.form.get("servings") or 2),
                time_limit=request.form.get("time_limit"),
                food_style=request.form.get("food_style"),
                recipe_content=recipe_content,
                source=request.form.get("source"),
                image_url=(request.form.get("image_url") or "").strip() or None,
            )
            db.session.add(row)
            db.session.commit()
            flash("Жор амжилттай хадгалагдлаа.", "success")
            return redirect(url_for("saved"))

        rows = SavedRecipe.query.order_by(SavedRecipe.created_at.desc()).all()
        parsed = []
        for r in rows:
            try:
                content = json.loads(r.recipe_content)
            except json.JSONDecodeError:
                content = {"title": r.title, "steps": [r.recipe_content]}
            parsed.append({"row": r, "content": content})
        return render_template("saved.html", saved=parsed)

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/mealdb-test", methods=["POST"])
    def mealdb_test():
        text = (request.form.get("ingredient_text") or "").strip()
        tokens = parse_user_ingredients(text)
        mapped = map_to_mealdb_ingredients(tokens)
        seen = set()
        meals: List[Dict[str, Any]] = []
        for term in mapped:
            for m in mealdb.filter_by_ingredient(term):
                mid = m.get("idMeal")
                if mid and mid not in seen:
                    seen.add(mid)
                    meals.append(m)
        return render_template(
            "mealdb_results.html",
            ingredient_text=text,
            mapped=mapped,
            meals=meals,
        )

    @app.route("/mealdb/random")
    def mealdb_random():
        raw = mealdb.random_meal()
        norm = mealdb.normalize_meal(raw) if raw else None
        return render_template("mealdb_results.html", random_meal=norm, meals=[])

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
