"""Match user ingredient strings against local Ingredient rows."""
from typing import List, Optional, Tuple

from models import Ingredient


def _token_matches_row(token_lower: str, row: Ingredient) -> bool:
    names = [row.name.lower()]
    if row.name_en:
        names.append(row.name_en.lower())
    for n in names:
        if token_lower == n or token_lower in n or n in token_lower:
            return True
    return False


def match_ingredients(user_tokens: List[str]) -> Tuple[List[Ingredient], List[str]]:
    """
    Return (matched Ingredient ORM objects, unmatched user strings).
    Matching is case-insensitive on name or name_en.
    """
    if not user_tokens:
        return [], []

    all_rows: List[Ingredient] = Ingredient.query.order_by(Ingredient.name).all()
    matched: List[Ingredient] = []
    matched_ids = set()
    unmatched: List[str] = []

    for token in user_tokens:
        tl = token.strip().lower()
        if not tl:
            continue
        found: Optional[Ingredient] = None
        for row in all_rows:
            if _token_matches_row(tl, row):
                found = row
                break
        if found:
            if found.id not in matched_ids:
                matched_ids.add(found.id)
                matched.append(found)
        else:
            unmatched.append(token.strip())

    return matched, unmatched


def matched_summary_for_prompt(matched: List[Ingredient]) -> str:
    """Human-readable list for Gemini prompt."""
    if not matched:
        return "байхгүй"
    parts = []
    for m in matched:
        line = f"{m.name}"
        if m.name_en:
            line += f" ({m.name_en})"
        if m.category:
            line += f" — {m.category}"
        parts.append(line)
    return "; ".join(parts)
