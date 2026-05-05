"""
common/text_utils.py
Text normalisation, keyword filtering, scoring, and topic assignment.
All logic reads from config.py — edit weights/keywords there, not here.
"""

import unicodedata
from dataclasses import dataclass, field
from typing import Optional
import datetime

from config import (
    ALL_KEYWORDS, NEGATIVE_KEYWORDS, GROUPS,
    WEIGHTS, TOPIC_PRIORITY,
)


def normalize(text: str) -> str:
    """Lowercase + strip Greek diacritics for accent-insensitive matching."""
    if not text:
        return ""
    t = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )


def is_energy_title(title: str) -> bool:
    t = normalize(title)
    if any(n in t for n in NEGATIVE_KEYWORDS):
        return False
    return any(k in t for k in ALL_KEYWORDS)


def score_title(title: str) -> int:
    t = normalize(title)
    sc = 0
    for group, words in GROUPS.items():
        if any(w in t for w in words):
            sc += WEIGHTS.get(group, 1)
    # Small bonus for generic energy mentions
    if any(w in t for w in ["ενεργεια", "ηλεκτρ"]):
        sc += 1
    return sc


def assign_topic(title: str) -> str:
    t = normalize(title)
    for key in TOPIC_PRIORITY:
        if any(w in t for w in GROUPS.get(key, [])):
            return key
    return "other"


@dataclass
class Article:
    title: str
    link: str
    site: str
    score: int = 0
    published_dt: Optional[datetime.datetime] = None
    topic: str = "other"
