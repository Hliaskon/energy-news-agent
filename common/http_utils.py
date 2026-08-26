"""
common/http_utils.py
Shared HTTP session, page scraper, and article date extractor.
"""

import json
import sys
import time
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import datetime

import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from zoneinfo import ZoneInfo

try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None  # type: ignore

ATHENS_TZ = ZoneInfo("Europe/Athens")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

_BS_PARSER = "lxml"
try:
    BeautifulSoup("<html></html>", _BS_PARSER)
except Exception:
    _BS_PARSER = "html.parser"

_SESSION: Optional[requests.Session] = None


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        if Retry is not None:
            retry = Retry(
                total=3, connect=3, read=3,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["GET", "HEAD"]),
            )
            s.mount("http://",  HTTPAdapter(max_retries=retry))
            s.mount("https://", HTTPAdapter(max_retries=retry))
        _SESSION = s
    return _SESSION


def short_site(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url


def _is_usable_link_text(text: str) -> bool:
    t = text.lower()
    if len(t) < 8:
        return False
    bad = ["read more", "περισσοτερα", "share", "mailto:", "javascript:"]
    return not any(b in t for b in bad)


def scrape_site(
    url: str,
    timeout: int = 12,
) -> List[Tuple[str, str]]:
    """Return deduplicated (title, absolute_link) pairs from a page."""
    results: List[Tuple[str, str]] = []
    try:
        r = get_session().get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, _BS_PARSER)
        seen: set = set()
        for a in soup.find_all("a", href=True):
            # Prefer a heading element inside the anchor over the anchor's
            # full text. On several GR sites (e.g. ot.gr) the whole article
            # card — category tag + date + headline + teaser + byline — is
            # wrapped in a single <a>, so a.get_text() returns a long blob
            # instead of just the headline. That blob then matched keywords
            # from teaser text, not the actual title, and looked like noise.
            heading = a.find(["h1", "h2", "h3", "h4"])
            title = heading.get_text(strip=True) if heading else a.get_text(strip=True)
            href  = a["href"]
            if not title or not href:
                continue
            if not _is_usable_link_text(title):
                continue
            if len(title) > 220:
                # Still a blob (no heading tag found) — skip rather than
                # let a multi-headline concatenation through keyword scoring.
                continue
            link = urljoin(url, href)
            if link.startswith("#"):
                continue
            key = (title[:80].lower(), link[:130].lower())
            if key in seen:
                continue
            seen.add(key)
            results.append((title, link))
    except Exception as exc:
        print(f"[WARN] {url}: {exc}", file=sys.stderr)
    return results


def _try_parse_dt(value: str) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        dt = dateparser.parse(value)
        if not dt:
            return None
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(ATHENS_TZ)
    except Exception:
        return None


def extract_dt_from_html(html: str) -> Optional[datetime.datetime]:
    soup = BeautifulSoup(html, _BS_PARSER)
    candidates: List[str] = []

    for attr in ("property", "name"):
        for key in ("article:published_time", "og:updated_time", "pubdate",
                    "publishdate", "timestamp", "dc.date", "date"):
            tag = soup.find("meta", {attr: key})
            if tag and tag.get("content"):
                candidates.append(tag["content"])

    for t in soup.find_all("time"):
        v = t.get("datetime") or t.get_text(strip=True)
        if v:
            candidates.append(v)

    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            for obj in (data if isinstance(data, list) else [data]):
                if isinstance(obj, dict):
                    for k in ("datePublished", "dateCreated",
                              "dateModified", "uploadDate"):
                        if obj.get(k):
                            candidates.append(obj[k])
        except Exception:
            pass

    for raw in candidates:
        dt = _try_parse_dt(raw)
        if dt:
            return dt
    return None


def extract_snippet_from_html(html: str, max_chars: int = 700) -> str:
    """
    Best-effort short excerpt of the article body, used only as a zero-cost
    relevance corroboration signal (see collect() in weekly_digest.py) — NOT
    for display. Prefers meta description / og:description (cheap, already
    summarised by the publisher); falls back to the first couple of <p> tags.
    """
    soup = BeautifulSoup(html, _BS_PARSER)

    for attr in ("property", "name"):
        for key in ("og:description", "description", "twitter:description"):
            tag = soup.find("meta", {attr: key})
            if tag and tag.get("content"):
                return tag["content"][:max_chars]

    paras = soup.find_all("p")
    text = " ".join(p.get_text(" ", strip=True) for p in paras[:4])
    return text[:max_chars]


def fetch_article_dt_and_snippet(
    url: str, timeout: int = 10,
) -> Tuple[Optional[datetime.datetime], str]:
    """
    Single GET that returns both the published date and a short body
    snippet — reuses the same HTTP response instead of fetching the page
    twice (once for date, once for relevance corroboration).
    """
    try:
        r = get_session().get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        dt = extract_dt_from_html(r.text)
        snippet = extract_snippet_from_html(r.text)
        return dt, snippet
    except Exception:
        return None, ""


def fetch_article_dt(url: str, timeout: int = 10) -> Optional[datetime.datetime]:
    try:
        r = get_session().get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        return extract_dt_from_html(r.text)
    except Exception:
        return None
