"""Flask application configuration."""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Default configuration for MoodMeal AI."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///moodmeal.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    MEALDB_API_KEY = os.getenv("MEALDB_API_KEY", "1").strip()
    MEALDB_BASE_URL = os.getenv(
        "MEALDB_BASE_URL", "https://www.themealdb.com/api/json/v1"
    ).rstrip("/")
