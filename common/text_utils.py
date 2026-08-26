"""
common/text_utils.py
Text normalisation, keyword filtering, scoring, and topic assignment.
All logic reads from config.py — edit weights/keywords there, not here.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Optional
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


# ── Boundary-aware keyword matching ──────────────────────────────────
# Plain substring matching (`kw in text`) let short/ambiguous keywords like
# "ems" or "bas" match inside unrelated words — e.g. "ems" inside
# "Unisystems", "bas" inside "database". That's how an OTE–Unisystems cloud
# contract ended up scored as an energy-efficiency article. Every keyword is
# now matched only when NOT immediately preceded/followed by another
# alphanumeric character (Latin or Greek), which approximates a word
# boundary without relying on Python's \b (which doesn't reliably span
# Greek letters). Patterns are compiled once and cached.
_PATTERN_CACHE: Dict[str, "re.Pattern"] = {}


def _kw_pattern(kw: str) -> "re.Pattern":
    pat = _PATTERN_CACHE.get(kw)
    if pat is None:
        pat = re.compile(
            r"(?<![a-zα-ω0-9])" + re.escape(kw) + r"(?![a-zα-ω0-9])"
        )
        _PATTERN_CACHE[kw] = pat
    return pat


def _kw_in(text: str, kw: str) -> bool:
    return _kw_pattern(kw).search(text) is not None


def is_energy_title(title: str) -> bool:
    t = normalize(title)
    if any(_kw_in(t, n) for n in NEGATIVE_KEYWORDS):
        return False
    return any(_kw_in(t, k) for k in ALL_KEYWORDS)


def score_title(title: str) -> int:
    t = normalize(title)
    sc = 0
    for group, words in GROUPS.items():
        if any(_kw_in(t, w) for w in words):
            sc += WEIGHTS.get(group, 1)
    # Small bonus for generic energy mentions
    if any(_kw_in(t, w) for w in ["ενεργεια", "ηλεκτρ"]):
        sc += 1
    return sc


def assign_topic(title: str) -> str:
    t = normalize(title)
    for key in TOPIC_PRIORITY:
        if any(_kw_in(t, w) for w in GROUPS.get(key, [])):
            return key
    return "other"


def count_keyword_hits(text: str) -> int:
    """Total number of distinct ALL_KEYWORDS entries found in text (not
    weighted, not deduplicated by group) — used only as a corroboration
    signal, see weekly_digest.py collect()."""
    t = normalize(text)
    return sum(1 for k in ALL_KEYWORDS if _kw_in(t, k))


@dataclass
class Article:
    title: str
    link: str
    site: str
    score: int = 0
    published_dt: Optional[datetime.datetime] = None
    topic: str = "other"
    snippet: str = ""
