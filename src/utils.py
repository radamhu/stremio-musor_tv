"""Utility functions for text processing."""
import re
import unicodedata
from typing import Optional


def slugify(s: str) -> str:
    """Convert string to URL-friendly slug."""
    return re.sub(
        r"(^-|-$)", "",
        re.sub(r"[^a-z0-9]+", "-", strip_diacritics(s).lower())
    )


def strip_diacritics(s: str) -> str:
    """Remove diacritical marks from Unicode string."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def is_probably_film(category: Optional[str]) -> bool:
    """Heuristic to determine if content is a film vs. series."""
    if not category:
        return False
    c = category.lower()
    if "film" in c:
        return True
    if "sorozat" in c:
        return False
    return False
