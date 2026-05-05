#!/usr/bin/env python3
"""
energy_news.py  v2.0 — Enerwave-tuned Daily Energy News Aggregator
────────────────────────────────────────────────────────────────────
Changes vs v1:
  • Topic-based HTML report (EE → ESCO → Solar Thermal → CHP → …)
    instead of per-site listing — scan in seconds, not minutes
  • TOP-N headline section at the top of the email
  • Enerwave-weighted scoring: efficiency / esco / solar_th / funding = 5
    (wind / pv demoted to 2 — not in Enerwave service portfolio)
  • New keyword groups: solar_thermal, esco, chp, industrial, funding/ΕΣΠΑ
  • ~18 new sites: ΕΣΠΑ portals, Greek associations (ΕΛΕΤΑΕΝ, HELAPCO,
    IENE, ΔΕΗ, ΔΕΔΔΗΕ, Metlen), IEA-SHC, ESTIF, Euroheat, ΕΦΕΠΑΕ …
  • MAX_AGE_DAYS filter: drops articles with a known date > 3 days old
  • MAX_DT_FETCHES raised to 30 (more articles enriched with exact dates)
  • Global cross-site deduplication (same story from N sites → kept once)
  • Informative email subject: date + article count
"""

import os
import sys
import time
import json
import datetime
import unicodedata
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None  # type: ignore

from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.headerregistry import Address
from email.utils import formatdate, make_msgid
from dateutil import parser as dateparser
from zoneinfo import ZoneInfo

# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════
ATHENS_TZ       = ZoneInfo("Europe/Athens")
MAX_AGE_DAYS    = 3          # drop articles with a known date older than this
MAX_DT_FETCHES  = 30         # max extra HTTP GETs for date enrichment
TOP_N           = 12         # items in the "Top Headlines" section
SCRAPE_DELAY    = 0.4        # seconds between site requests (politeness)
REQUEST_TIMEOUT = 12         # seconds per HTTP request

# ══════════════════════════════════════════════════════════════
#  SITES
# ══════════════════════════════════════════════════════════════
SITES: List[str] = [

    # ── Core Greek energy / economy ──────────────────────────────────
    "https://www.energypress.gr",
    "https://www.naftemporiki.gr",
    "https://www.ot.gr",
    "https://www.capital.gr",
    "https://www.moneyreview.gr",
    "https://www.imerisia.gr",
    "https://www.cnn.gr",
    "https://www.kathimerini.gr",
    "https://www.powergame.gr",
    "https://www.euro2day.gr",
    "https://www.liberal.gr",
    "https://www.energyin.gr/",
    "https://ecotec.gr",
    "https://www.greenagenda.gr",
    "https://energynews.gr/",
    "https://industry-news.gr/",
    "https://www.businessdaily.gr/",
    "https://www.worldenergynews.gr/",
    "https://ypodomes.com/",
    "https://www.financialreport.gr/",
    "https://energymag.gr/",

    # ── Additional Greek energy sites (NEW) ──────────────────────────
    "https://www.energia.gr/",                  # ειδήσεις ενέργειας
    "https://www.enallaktiki.gr/",              # ΑΠΕ / εξοικονόμηση
    "https://www.haee.gr/news/",                # Ελληνική Ένωση Εταιρειών Ενέργειας
    "https://helapco.gr/news/",                 # Σύνδεσμος Εταιρειών Φ/Β
    "https://www.eletaen.gr/",                  # ΕΛΕΤΑΕΝ — αιολικά
    "https://www.iene.eu/",                     # Institute of Energy for SE Europe
    "https://www.dei.gr/el/category/news/",     # ΔΕΗ — ανακοινώσεις
    "https://www.hedno.gr/gr/press",            # ΔΕΔΔΗΕ — τύπος
    "https://www.metlen.com/gr/news-media",     # Metlen (πρ. MYTILINEOS)

    # ── ΕΣΠΑ / EU Funding portals (NEW) ─────────────────────────────
    "https://www.espa.gr/el/pages/staticEspaNews.aspx",
    "https://www.antagonistikotita.gr/anakoinoseis/",   # Ανταγωνιστικότητα 2021-27
    "https://www.efepae.gr/front.aspx/news",             # ΕΦΕΠΑΕ
    "https://www.mindev.gov.gr/category/deltia-typou/",  # Υπ. Ανάπτυξης
    "https://www.pepattikis.gr/anakoinoseis/",           # ΠΕΠ Αττικής
    "https://www.mou.gr/el/Pages/News.aspx",             # Μονάδα Οργάνωσης ΕΕ

    # ── Solar thermal / industrial heat / CHP (NEW) ─────────────────
    "https://www.solarthermalworld.org/news/",   # global ST news (AEE INTEC)
    "https://www.iea-shc.org/news",              # IEA Solar Heating & Cooling
    "https://estif.org/news/",                   # EU Solar Thermal Industry Fed.
    "https://www.euroheat.org/news/",            # European Heat & Cooling assoc.

    # ── ESCO / EE industry ───────────────────────────────────────────
    "https://www.eceee.org/all-news/news/",
    "https://www.aceee.org/news",
    "https://www.bpie.eu/news/",

    # ── Balkan / regional ────────────────────────────────────────────
    "https://greekreporter.com",
    "https://balkangreenenergynews.com",
    "https://energynews.oedigital.com",

    # ── International ────────────────────────────────────────────────
    "https://www.euractiv.com/section/energy/",
    "https://www.euronews.com/tag/energy",
    "https://www.spglobal.com",
    "https://www.ft.com",                        # headlines visible, body paywall

    # ── RES specialty ────────────────────────────────────────────────
    "https://www.pv-magazine.com/tag/greece/",
    "https://renewablesnow.com/topic/greece/",

    # ── Regulatory / Gov (GR) ────────────────────────────────────────
    "https://ypen.gov.gr/category/anakoinoseis/",
    "https://www.admie.gr/en/news",
    "https://www.raae.gr/anakoinoseis/",

    # ── EE programs (GR) ─────────────────────────────────────────────
    "https://exoikonomo2025.gov.gr/",
    "https://www.ot.gr/category/green/eksoikonomisi/",
    "https://www.skai.gr/tags/eksoikonomisi-energeias",
    "https://www.topics.gr/diafora/eksoikonomhsh-energeias/",

    # ── EU institutions ───────────────────────────────────────────────
    "https://energy.ec.europa.eu/news_en",
    "https://cinea.ec.europa.eu/index_en",
    "https://build-up.ec.europa.eu/en/news-and-events",
    "https://www.iea.org/topics/energy-efficiency",
    "https://www.power-technology.com/category/energy-efficiency/",
    "https://www.facilitiesdive.com/",
]

# ══════════════════════════════════════════════════════════════
#  TEXT NORMALISATION
# ══════════════════════════════════════════════════════════════
def normalize(text: str) -> str:
    """Lowercase + strip Greek diacritics."""
    if not text:
        return ""
    t = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )


# ══════════════════════════════════════════════════════════════
#  KEYWORDS  (normalized — no accents needed)
# ══════════════════════════════════════════════════════════════
KEYWORDS: List[str] = [
    # General energy / market
    "ενεργεια", "ενεργειακη αγορα", "ενεργειακο κοστος",
    "kwh", "mwh", "τιμολογια ρευματος", "χονδρεμπορικη", "day ahead", "dam",
    # Networks
    "ηλεκτρ", "αδμηε", "δεδδηε", "διασυνδεση", "smart grid", "smart meter",
    # PV
    "φωτοβολ", "φβ", "pv", "net metering", "net billing",
    "αυτοκαταναλωση", "zero feed in", "virtual net billing",
    # Wind
    "αιολικ", "wind", "ανεμογεννητρ", "turbine", "offshore wind", "repowering",
    # Storage
    "μπαταρ", "battery", "bess", "αντλησιοταμιευση", "pumped storage",
    # Gas / oil
    "φυσικο αεριο", "gas", "lng", "fsru", "αγωγος", "pipeline",
    "eastmed", "tap", "κοιτασμα", "πετρελ", "διυλιστ",
    # EE / Buildings
    "εξοικονομηση", "ενεργειακη αναβαθμιση", "εξοικονομω",
    "energy efficiency", "efficient", "energy audit", "ενεργειακος ελεγχος",
    "θερμικη μονωση", "μονωση", "u-value", "building envelope",
    "hvac", "heat pump", "αντλια θερμοτητας", "led", "retrofit", "airtightness",
    # ESCO / EPC / M&V
    "esco", "epc", "energy performance contract", "energy service",
    "m&v", "ipmvp", "iso 50001", "bems", "ems", "bas", "building automation",
    "commissioning", "retrocommissioning",
    # Industrial EE
    "vfd", "variable speed drive", "inverter drive", "ie3", "ie4",
    "heat recovery", "ανακτηση θερμοτητας", "waste heat",
    "process heat", "βιομηχανικη ενεργεια", "compressed air", "πεπιεσμενος αερας",
    # Solar thermal / CST
    "solar thermal", "ηλιοθερμικ", "ηλιακη θερμοτητα",
    "parabolic trough", "παραβολικα κατοπτρα", "cst", "concentrating solar",
    "solar heat", "process steam", "ατμος παραγωγης",
    "district heating", "τηλεθερμανση",
    # CHP / Cogeneration
    "chp", "cogeneration", "συμπαραγωγη", "τριπαραγωγη", "trigeneration",
    # Hydrogen
    "πρασινο υδρογονο", "green hydrogen", "electrolyzer", "fuel cell",
    "power to x", "αποανθρακοποιηση",
    # Policy
    "υπεν", "ypen", "ρααευ", "ppa", "cfd", "fit", "auctions", "ets", "cbam",
    # ΕΣΠΑ / EU Funding
    "εσπα", "espa", "ταμειο ανακαμψης", "recovery fund", "rrf",
    "innovation fund", "if26", "life program", "life clean energy",
    "horizon europe", "ευρωπαϊκα ταμεια", "επιχειρησιακο προγραμμα",
    "ανταγωνιστικοτητα 2021", "αλλαζω συστημα θερμανσης", "εσπα ενεργεια",
]

NEGATIVE: List[str] = [
    "αθλη", "πολιτισ", "ψυχαγωγ", "μαγειρ", "συνταγ", "μοδα",
    "καιρος", "υγεια", "πανδημ", "κορονο", "τουρισ",
    "sports", "entertainment", "ποδοσφαιρ",
]


# ══════════════════════════════════════════════════════════════
#  SCORING  —  Enerwave-weighted
# ══════════════════════════════════════════════════════════════
WEIGHTS: Dict[str, int] = {
    "efficiency": 5,   # core business
    "esco":       5,   # main contract model
    "solar_th":   5,   # flagship technology (CST / industrial process heat)
    "funding":    5,   # ΕΣΠΑ/EU funding drives project pipeline
    "chp":        4,   # cogeneration projects
    "industrial": 4,   # VFD, heat recovery, compressed air
    "policy":     4,
    "gas":        4,
    "heatpump":   3,
    "bess":       3,
    "pv":         2,   # commoditised — low margin for Enerwave
    "wind":       2,   # not in Enerwave service portfolio
}

GROUPS: Dict[str, List[str]] = {
    "efficiency": [
        "εξοικονομηση", "ενεργειακη αναβαθμιση", "εξοικονομω",
        "energy efficiency", "efficient", "energy audit",
        "ενεργειακος ελεγχος", "θερμικη μονωση", "μονωση",
        "u-value", "building envelope", "hvac", "retrofit", "led",
        "bems", "ems", "bas", "building automation",
        "commissioning", "retrocommissioning", "iso 50001", "m&v", "ipmvp",
    ],
    "esco": [
        "esco", "epc", "energy performance contract",
        "energy service", "εξοικονομω μεσω παροχων",
    ],
    "solar_th": [
        "solar thermal", "ηλιοθερμικ", "ηλιακη θερμοτητα",
        "parabolic trough", "παραβολικα κατοπτρα", "cst",
        "concentrating solar", "solar heat", "process steam",
        "ατμος παραγωγης", "ηλιακο θερμικο",
    ],
    "chp": [
        "chp", "cogeneration", "συμπαραγωγη",
        "τριπαραγωγη", "trigeneration",
    ],
    "industrial": [
        "vfd", "variable speed drive", "ie3", "ie4",
        "heat recovery", "ανακτηση θερμοτητας", "waste heat",
        "process heat", "βιομηχανικη ενεργεια",
        "compressed air", "πεπιεσμενος αερας",
        "district heating", "τηλεθερμανση",
    ],
    "heatpump": [
        "heat pump", "αντλια θερμοτητας",
        "air-to-water", "geothermal heat pump",
    ],
    "funding": [
        "εσπα", "espa", "ταμειο ανακαμψης", "recovery fund", "rrf",
        "innovation fund", "if26", "life program", "life clean energy",
        "horizon europe", "ευρωπαϊκα ταμεια",
        "ανταγωνιστικοτητα 2021", "αλλαζω συστημα θερμανσης",
        "εξοικονομω 2025", "εσπα ενεργεια",
    ],
    "pv": [
        "φωτοβολ", "φβ", "pv", "net metering", "net billing",
        "αυτοκαταναλωση", "zero feed in", "virtual net billing",
    ],
    "bess": [
        "μπαταρ", "battery", "bess",
        "αντλησιοταμιευση", "pumped storage", "lfp",
    ],
    "wind": [
        "αιολικ", "wind", "ανεμογεννητρ", "turbine",
        "offshore wind", "repowering",
    ],
    "gas": [
        "φυσικο αεριο", "gas", "lng", "fsru",
        "αγωγος", "pipeline", "eastmed",
    ],
    "policy": [
        "υπεν", "ypen", "ρααευ", "ppa", "cfd",
        "fit", "auctions", "ets", "cbam",
    ],
}

# First matching key wins (most Enerwave-specific first)
TOPIC_PRIORITY: List[str] = [
    "esco", "solar_th", "chp", "industrial",
    "efficiency", "funding", "heatpump",
    "pv", "bess", "wind", "gas", "policy",
]

# Display metadata per topic: (emoji, Greek label)
TOPIC_META: Dict[str, Tuple[str, str]] = {
    "efficiency": ("🏢", "Εξοικονόμηση Ενέργειας & Κτίρια"),
    "esco":       ("📋", "ESCO / EPC / Χρηματοδοτικά Μοντέλα"),
    "solar_th":   ("☀️",  "Ηλιοθερμικά & Βιομηχανική Θερμότητα"),
    "chp":        ("⚡", "Συμπαραγωγή (CHP / Τριπαραγωγή)"),
    "industrial": ("🏭", "Βιομηχανική Ενεργειακή Αποδοτικότητα"),
    "funding":    ("💶", "ΕΣΠΑ & EU Funding"),
    "heatpump":   ("🌡️",  "Αντλίες Θερμότητας"),
    "pv":         ("🌞", "Φωτοβολταϊκά"),
    "bess":       ("🔋", "Αποθήκευση Ενέργειας"),
    "wind":       ("💨", "Αιολική Ενέργεια"),
    "gas":        ("⛽", "Φυσικό Αέριο & LNG"),
    "policy":     ("🏛️",  "Πολιτική & Ρύθμιση"),
    "other":      ("📰", "Γενικά Ενεργειακά"),
}

# Section header colours (hex) for HTML report
_TOPIC_COLOUR: Dict[str, str] = {
    "efficiency": "#1a7a4a",
    "esco":       "#1a6a3a",
    "solar_th":   "#c67000",
    "chp":        "#5a3e9e",
    "industrial": "#2d6a9f",
    "funding":    "#c0392b",
    "heatpump":   "#b84a00",
    "pv":         "#e07b00",
    "bess":       "#1a5276",
    "wind":       "#117a65",
    "gas":        "#6c3483",
    "policy":     "#1f618d",
    "other":      "#555555",
    "top":        "#e94560",
}


# ══════════════════════════════════════════════════════════════
#  ARTICLE DATACLASS
# ══════════════════════════════════════════════════════════════
@dataclass
class Article:
    title: str
    link: str
    site: str
    score: int = 0
    published_dt: Optional[datetime.datetime] = None
    topic: str = "other"


# ══════════════════════════════════════════════════════════════
#  FILTER / SCORE / TOPIC HELPERS
# ══════════════════════════════════════════════════════════════
def is_energy_title(title: str) -> bool:
    t = normalize(title)
    if any(n in t for n in NEGATIVE):
        return False
    return any(k in t for k in KEYWORDS)


def score_title(title: str) -> int:
    t = normalize(title)
    sc = 0
    for group, words in GROUPS.items():
        if any(w in t for w in words):
            sc += WEIGHTS.get(group, 1)
    if any(w in t for w in ["ενεργεια", "ηλεκτρ"]):
        sc += 1
    return sc


def assign_topic(title: str) -> str:
    t = normalize(title)
    for key in TOPIC_PRIORITY:
        if any(w in t for w in GROUPS.get(key, [])):
            return key
    return "other"


def _is_article_text(text: str) -> bool:
    t = normalize(text)
    if len(t) < 8:
        return False
    bad = ["read more", "περισσοτερα", "share", "mailto:", "javascript:"]
    return not any(b in t for b in bad)


def _short_site(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url


# ══════════════════════════════════════════════════════════════
#  HTTP / SCRAPING
# ══════════════════════════════════════════════════════════════
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


def _get_session() -> requests.Session:
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


def scrape_site(url: str) -> List[Tuple[str, str]]:
    """Return (title, absolute_link) pairs scraped from url."""
    results: List[Tuple[str, str]] = []
    try:
        r = _get_session().get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, _BS_PARSER)
        seen: set = set()
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            href  = a["href"]
            if not title or not href:
                continue
            if not _is_article_text(title):
                continue
            link = urljoin(url, href)
            if link.startswith("#"):
                continue
            key = (normalize(title)[:80], normalize(link)[:130])
            if key in seen:
                continue
            seen.add(key)
            results.append((title, link))
    except Exception as exc:
        print(f"[WARN] {url}: {exc}", file=sys.stderr)
    return results


# ══════════════════════════════════════════════════════════════
#  DATE EXTRACTION
# ══════════════════════════════════════════════════════════════
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


def _extract_dt_from_html(html: str) -> Optional[datetime.datetime]:
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


def fetch_article_dt(url: str) -> Optional[datetime.datetime]:
    try:
        r = _get_session().get(url, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        return _extract_dt_from_html(r.text)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════
def collect_all_articles() -> List[Article]:
    """
    1. Scrape all sites
    2. Keyword filter + global cross-site deduplication
    3. Score + assign topic
    4. Enrich top MAX_DT_FETCHES articles with exact publish date
    5. Drop articles where date is known and older than MAX_AGE_DAYS
    6. Final sort: date desc, score desc
    """
    raw: List[Tuple[str, str, str]] = []  # (title, link, site)

    for site in SITES:
        print(f"[INFO] Scraping {site} …", file=sys.stderr)
        for title, link in scrape_site(site):
            raw.append((title, link, site))
        time.sleep(SCRAPE_DELAY)

    # Filter + global dedup ──────────────────────────────────────────
    seen_links:  set = set()
    seen_titles: set = set()
    articles: List[Article] = []

    for title, link, site in raw:
        if not is_energy_title(title):
            continue
        nl = normalize(link)[:140]
        nt = normalize(title)[:100]
        if nl in seen_links or nt in seen_titles:
            continue
        seen_links.add(nl)
        seen_titles.add(nt)
        articles.append(Article(
            title=title, link=link, site=site,
            score=score_title(title),
            topic=assign_topic(title),
        ))

    # Date enrichment (top articles by score first) ──────────────────
    articles.sort(key=lambda a: a.score, reverse=True)
    for i, art in enumerate(articles):
        if i >= MAX_DT_FETCHES:
            break
        art.published_dt = fetch_article_dt(art.link)

    # Age filter — keep: (no date known) OR (date within MAX_AGE_DAYS) ─
    now    = datetime.datetime.now(tz=ATHENS_TZ)
    cutoff = now - datetime.timedelta(days=MAX_AGE_DAYS)
    articles = [
        a for a in articles
        if a.published_dt is None or a.published_dt >= cutoff
    ]

    # Final sort ─────────────────────────────────────────────────────
    def _sort_key(a: Article) -> Tuple:
        dt = a.published_dt or datetime.datetime.min.replace(
            tzinfo=ZoneInfo("UTC")
        )
        return (dt, a.score)

    articles.sort(key=_sort_key, reverse=True)
    return articles


# ══════════════════════════════════════════════════════════════
#  REPORT BUILDERS
# ══════════════════════════════════════════════════════════════
def _fmt(dt: Optional[datetime.datetime]) -> str:
    return dt.strftime("%d/%m %H:%M") if dt else "—"


def build_text_report(articles: List[Article]) -> str:
    today = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")
    lines = [f"🔋 DAILY ENERGY NEWS — {today} (EET/EEST)", ""]

    lines += ["═" * 56, f"🏆  TOP {TOP_N} HEADLINES", "═" * 56, ""]
    for a in articles[:TOP_N]:
        lines.append(f"• [{_fmt(a.published_dt)}] (s:{a.score}) {a.title}")
        lines.append(f"  {a.link}  [{_short_site(a.site)}]")
        lines.append("")

    buckets: Dict[str, List[Article]] = {}
    for a in articles:
        buckets.setdefault(a.topic, []).append(a)

    for key in TOPIC_PRIORITY + ["other"]:
        items = buckets.get(key)
        if not items:
            continue
        emoji, label = TOPIC_META.get(key, ("📰", key))
        lines += ["─" * 56, f"{emoji}  {label.upper()}", "─" * 56, ""]
        for a in items:
            lines.append(f"• [{_fmt(a.published_dt)}] (s:{a.score}) {a.title}")
            lines.append(f"  {a.link}  [{_short_site(a.site)}]")
            lines.append("")
    return "\n".join(lines)


def build_html_report(articles: List[Article]) -> str:
    today = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")

    style = """
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
       color: #1a1a2e; background: #f4f5f7; margin: 0; padding: 16px; }
.wrap { max-width: 860px; margin: 0 auto; }
h1   { font-size: 22px; margin: 0 0 4px; color: #0f3460; }
.ts  { color: #888; font-size: 12px; margin-bottom: 20px; }
.sec { background: #fff; border-radius: 8px; margin-bottom: 14px;
       box-shadow: 0 1px 3px rgba(0,0,0,.08); overflow: hidden; }
.shdr { padding: 9px 14px; font-weight: 700; font-size: 13px; color: #fff; }
.item { padding: 8px 14px; border-bottom: 1px solid #f0f0f0;
        display: flex; align-items: flex-start; gap: 8px; }
.item:last-child { border-bottom: none; }
.sc { min-width: 26px; text-align: center; background: #eef; color: #336;
      border: 1px solid #ccd; border-radius: 4px;
      padding: 1px 4px; font-size: 11px; flex-shrink: 0; }
.ib { flex: 1; min-width: 0; }
a { color: #0366d6; text-decoration: none; font-size: 13px; line-height: 1.4; }
a:hover { text-decoration: underline; }
.meta { color: #999; font-size: 11px; margin-top: 2px; }
    """

    def _section(topic_key: str, items: List[Article]) -> str:
        if not items:
            return ""
        colour = _TOPIC_COLOUR.get(topic_key, "#555")
        if topic_key == "top":
            emoji, label = "🏆", f"Top {TOP_N} Headlines"
        else:
            emoji, label = TOPIC_META.get(topic_key, ("📰", topic_key))
        rows = "".join(
            f"<div class='item'>"
            f"<span class='sc'>{a.score}</span>"
            f"<div class='ib'>"
            f"<a href='{a.link}' target='_blank' rel='noopener noreferrer'>"
            f"{a.title}</a>"
            f"<div class='meta'>{_fmt(a.published_dt)} · {_short_site(a.site)}</div>"
            f"</div></div>"
            for a in items
        )
        return (
            f"<div class='sec'>"
            f"<div class='shdr' style='background:{colour}'>"
            f"{emoji} {label}</div>"
            f"{rows}</div>"
        )

    buckets: Dict[str, List[Article]] = {}
    for a in articles:
        buckets.setdefault(a.topic, []).append(a)

    parts = [
        "<div class='wrap'>",
        "<h1>🔋 Daily Energy News — Enerwave</h1>",
        f"<div class='ts'>Europe/Athens — {today} · {len(articles)} articles</div>",
        _section("top", articles[:TOP_N]),
    ]
    for key in TOPIC_PRIORITY + ["other"]:
        parts.append(_section(key, buckets.get(key, [])))
    parts.append("</div>")

    return (
        "<!doctype html><html>"
        "<head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width'>"
        f"<style>{style}</style>"
        "</head>"
        f"<body>{''.join(parts)}</body></html>"
    )


# ══════════════════════════════════════════════════════════════
#  EMAIL
# ══════════════════════════════════════════════════════════════
def send_email(subject: str, body_text: str, body_html: str) -> None:
    EU   = os.getenv("EMAIL_USERNAME")
    EP   = os.getenv("EMAIL_PASSWORD")
    ER   = os.getenv("EMAIL_RECIPIENT")
    CC   = os.getenv("EMAIL_CC",  "").strip()
    BCC  = os.getenv("EMAIL_BCC", "").strip()
    HOST = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    PORT = int(os.getenv("SMTP_PORT", "587"))

    if not EU or not EP or not ER:
        raise RuntimeError(
            "Missing env vars: EMAIL_USERNAME / EMAIL_PASSWORD / EMAIL_RECIPIENT"
        )

    to_list  = [x.strip() for x in ER.split(",")  if x.strip()]
    cc_list  = [x.strip() for x in CC.split(",")  if x.strip()]
    bcc_list = [x.strip() for x in BCC.split(",") if x.strip()]
    all_rcpt = to_list + cc_list + bcc_list

    msg = MIMEMultipart("alternative")
    try:
        local, domain = EU.split("@", 1)
        msg["From"] = str(Address("Daily Energy News Agent", local, domain))
    except Exception:
        msg["From"] = EU
    msg["To"]         = ", ".join(to_list)
    if cc_list:
        msg["Cc"]     = ", ".join(cc_list)
    msg["Subject"]    = subject
    msg["Date"]       = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html",  "utf-8"))

    for mode, host, port in [("STARTTLS", HOST, PORT), ("SSL", HOST, 465)]:
        for _ in range(2):
            srv = None
            last_exc: Optional[Exception] = None
            try:
                if mode == "STARTTLS":
                    srv = smtplib.SMTP(host, port, timeout=20)
                    srv.ehlo(); srv.starttls(); srv.ehlo()
                else:
                    srv = smtplib.SMTP_SSL(host, port, timeout=20)
                srv.login(EU, EP)
                srv.sendmail(EU, all_rcpt, msg.as_string())
                return
            except Exception as exc:
                last_exc = exc
                time.sleep(2)
            finally:
                try:
                    if srv:
                        srv.quit()
                except Exception:
                    pass
    raise RuntimeError(f"Email send failed after all retries: {last_exc}")


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
def main() -> None:
    articles = collect_all_articles()
    total    = len(articles)
    print(f"[INFO] {total} articles after filter, dedup & age check.",
          file=sys.stderr)

    SEND_EMPTY = os.getenv("SEND_EMPTY", "false").lower() == "true"
    if not articles and not SEND_EMPTY:
        print("ℹ️  No articles found — email not sent "
              "(set SEND_EMPTY=true to force).")
        return

    today   = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y")
    subject = f"⚡ Energy News {today} — {total} articles (Enerwave)"

    try:
        send_email(
            subject,
            build_text_report(articles),
            build_html_report(articles),
        )
        print("📨  HTML email sent successfully.")
    except Exception as exc:
        print(f"❌  Email failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
