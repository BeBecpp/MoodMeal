"""TheMealDB static ingredient image URLs from English names."""
import re
from typing import Any, Optional

MEALDB_ING_IMG_BASE = "https://www.themealdb.com/images/ingredients"


def build_mealdb_ingredient_image_url(
    name_en: Optional[str], size: str = "medium"
) -> Optional[str]:
    """
    Build TheMealDB ingredient image URL.

    - Empty name_en -> None
    - Lowercase, spaces -> underscores
    - size: "", "small", "medium", "large" (default medium -> -medium.png)
    """
    if not name_en or not str(name_en).strip():
        return None

    slug = str(name_en).strip().lower()
    slug = re.sub(r"\s+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug:
        return None

    s = (size or "medium").strip().lower()
    if s == "small":
        suffix = "-small"
    elif s == "large":
        suffix = "-large"
    elif s == "medium":
        suffix = "-medium"
    else:
        suffix = ""

    return f"{MEALDB_ING_IMG_BASE}/{slug}{suffix}.png"


def ensure_sqlite_ingredient_image_column(db: Any) -> None:
    """Add ingredients.image_url on legacy SQLite DBs (create_all does not migrate)."""
    try:
        from sqlalchemy import inspect, text

        insp = inspect(db.engine)
        if "ingredients" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("ingredients")}
        if "image_url" in cols:
            return
        with db.engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE ingredients ADD COLUMN image_url VARCHAR(500)")
            )
    except Exception:
        pass
