"""SQLAlchemy models for MoodMeal AI."""
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Ingredient(db.Model):
    """Pantry ingredient with Mongolian-first metadata."""

    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    name_en = db.Column(db.String(120), nullable=True)
    category = db.Column(db.String(64), nullable=False, default="other")
    taste_profile = db.Column(db.String(255), nullable=True)
    nutrition_note = db.Column(db.String(255), nullable=True)
    common_pairings = db.Column(db.String(255), nullable=True)
    is_common_home_item = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Recipe(db.Model):
    """Local home-style recipe."""

    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    meal_time = db.Column(db.String(80), nullable=True)
    mood_tags = db.Column(db.String(500), nullable=True)
    weather_tags = db.Column(db.String(500), nullable=True)
    food_style = db.Column(db.String(120), nullable=True)
    base_servings = db.Column(db.Integer, default=4)
    cook_time_minutes = db.Column(db.Integer, default=30)
    difficulty = db.Column(db.String(40), default="дунд")
    child_friendly = db.Column(db.Boolean, default=True)
    instructions = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(32), default="local")
    source_external_id = db.Column(db.String(64), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    youtube_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ingredients = db.relationship(
        "RecipeIngredient",
        backref="recipe",
        lazy="joined",
        cascade="all, delete-orphan",
    )


class RecipeIngredient(db.Model):
    """Ingredient line on a recipe."""

    __tablename__ = "recipe_ingredients"

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False)
    ingredient_name = db.Column(db.String(160), nullable=False)
    amount = db.Column(db.String(80), nullable=True)
    unit = db.Column(db.String(40), nullable=True)
    is_required = db.Column(db.Boolean, default=True)
    substitute_options = db.Column(db.String(255), nullable=True)


class SavedRecipe(db.Model):
    """User-saved generated recipe snapshot."""

    __tablename__ = "saved_recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    input_mood = db.Column(db.String(80), nullable=True)
    input_ingredients = db.Column(db.Text, nullable=True)
    weather = db.Column(db.String(80), nullable=True)
    meal_time = db.Column(db.String(80), nullable=True)
    servings = db.Column(db.Integer, default=2)
    time_limit = db.Column(db.String(40), nullable=True)
    food_style = db.Column(db.String(120), nullable=True)
    recipe_content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(40), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
