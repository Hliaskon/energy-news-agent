#!/usr/bin/env python3
"""
energy_news.py  —  Daily Energy News Agent  v2
Enerwave | HELLENiQ ENERGY — Energy Efficiency Division

Changes from v1
───────────────
• CONFIG block at top — tune without editing logic
• Scoring weights rebalanced for Enerwave EE focus
  (efficiency 6 / heatpump 5 / solar_thermal 5 / chp_cogen 5 /
   esco_epc 5 / eu_funding 5 / industrial_decarb 4  /  wind LOWERED to 2)
• 5 new keyword + scoring groups: solar_thermal, chp_cogen, esco_epc,
  eu_funding, industrial_decarb  — all core Enerwave service lines
• MAX_AGE_DAYS  — articles older than N days automatically discarded
• Parallel date enrichment via ThreadPoolExecutor (faster, larger pool)
• Cross-site title deduplication (Jaccard similarity ≥ 0.65)
• SKIP_SITES set — hard-paywalled / bot-blocked domains excluded cleanly
• Report reorganised:
    1. 🔝 Top Highlights  (best N across all sites)
    2. Thematic sections  (EE / Solar / Funding / Industry / Storage / Gas)
    — per-site breakdown removed (source shown inline on each item)
• Email subject now includes article count and date
"""

import os
import sys
import time
import json
import datetime
import unicodedata
from urllib.parse import urljoin
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None

from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.headerregistry import Address
from email.utils import formatdate, make_msgid

from dateutil import parser as dateparser
from zoneinfo import ZoneInfo

# ══════════════════════════════════════════════════════════════════
#  CONFIG  —  edit here, no changes needed elsewhere
# ══════════════════════════════════════════════════════════════════
ATHENS_TZ      = ZoneInfo("Europe/Athens")
MAX_AGE_DAYS   = 5      # drop articles with known date older than N days (0 = keep all)
MAX_DATE_FETCH = 50     # max articles enriched with a per-article date request
MAX_TOP        = 15     # items shown in "Top Highlights" section
DATE_WORKERS   = 10     # parallel threads for date enrichment
SITE_TIMEOUT   = 12     # seconds — site scrape request
DATE_TIMEOUT   = 8      # seconds — per-article date fetch

# Hard-paywalled / bot-blocked — returns nothing useful, skip immediately
SKIP_SITES: set = {
    "https://www.bloomberg.com",
}

# ══════════════════════════════════════════════════════════════════
#  SOURCES
# ══════════════════════════════════════════════════════════════════
SITES: List[str] = [
    # ── Core Greek energy media ──────────────────────────────────
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
    # ── International — Greece & Balkans ─────────────────────────
    "https://greekreporter.com",
    "https://balkangreenenergynews.com",
    "https://energynews.oedigital.com",
    "https://www.reuters.com",
    "https://www.spglobal.com",
    "https://www.ft.com",
    "https://www.euronews.com",
    # ── RES / Technical ──────────────────────────────────────────
    "https://www.pv-magazine.com/tag/greece/",
    "https://renewablesnow.com/topic/greece/",
    "https://www.euractiv.com/section/energy/",
    "https://www.euronews.com/tag/energy",
    # ── Regulators / Authorities ─────────────────────────────────
    "https://ypen.gov.gr/category/anakoinoseis/",
    "https://www.admie.gr/en/news",
    "https://www.raae.gr/anakoinoseis/",
    # ── Energy Efficiency — Greece ───────────────────────────────
    "https://exoikonomo2025.gov.gr/",
    "https://www.ot.gr/category/green/eksoikonomisi/",
    "https://www.skai.gr/tags/eksoikonomisi-energeias",
    "https://www.topics.gr/diafora/eksoikonomhsh-energeias/",
    # ── Energy Efficiency — EU / International ───────────────────
    "https://www.bpie.eu/news/",
    "https://www.aceee.org/news",
    "https://www.eceee.org/all-news/news/",
    "https://energy.ec.europa.eu/news_en",
    "https://build-up.ec.europa.eu/en/",
    "https://cinea.ec.europa.eu/news-events/news_en",
    # ── Solar Thermal / CHP / Industrial EE  [new in v2] ─────────
    "https://www.solarthermalworld.org/news/",
    "https://www.iea.org/news",
    "https://www.facilitiesdive.com/",
    "https://www.heatpumpingtechnologies.org/news/",
]

# ══════════════════════════════════════════════════════════════════
#  TEXT NORMALISATION
# ══════════════════════════════════════════════════════════════════
def normalize(text: str) -> str:
    """Lowercase + strip Greek diacritics for accent-insensitive matching."""
    if not text:
        return ""
    t = text.lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t)
                if unicodedata.category(c) != "Mn")
    return t

# ══════════════════════════════════════════════════════════════════
#  KEYWORDS / GROUPS / WEIGHTS
# ══════════════════════════════════════════════════════════════════
KEYWORDS: List[str] = [
    # General energy / market
    "ενεργεια", "ενεργειακη αγορα", "ενεργειακο κοστος", "kwh", "mwh",
    "τιμολογια ρευματος", "χονδρεμπορικη", "χρηματιστηριο ενεργειας",
    "dam", "day ahead",
    # Grid / networks
    "ηλεκτρ", "αδμηε", "δεδδηε", "διασυνδεση", "interconnector",
    "smart grid", "smart meters",
    # PV
    "φωτοβολ", "φβ", "pv", "πανελ", "inverter", "net metering",
    "αυτοκαταναλωση", "zero feed in", "net billing",
    # Wind
    "αιολικ", "wind", "ανεμογεννητρ", "turbine",
    "onshore wind", "offshore wind", "repowering",
    # Storage
    "μπαταρ", "battery", "bess", "soc", "lfp", "nmc",
    "flow battery", "αντλησιοταμιευση", "pumped storage",
    # Hydro
    "υδροηλεκτρ",
    # Gas / Hydrocarbons
    "φυσικο αεριο", "gas", "lng", "fsru", "αγωγος", "pipeline",
    "eastmed", "tap", "igb", "πετρελ", "κοιτασμα",
    # Buildings / EE — residential & commercial
    "εξοικονομηση", "ενεργειακη αναβαθμιση", "εξοικονομω",
    "energy efficiency", "ενεργειακη αποδοση",
    "heat pump", "αντλια θερμοτητας",
    "θερμικη μονωση", "u-value", "building envelope",
    "hvac", "led", "bems", "retrofit",
    "esco", "epc", "m&v", "ipmvp", "iso 50001",
    # Solar Thermal / CHP  [new]
    "solar thermal", "ηλιοθερμικ", "cst", "concentrating solar",
    "παραβολικ κατοπτρ", "parabolic trough", "process heat",
    "chp", "συμπαραγωγη", "cogeneration", "combined heat and power",
    "τριπαραγωγη", "trigeneration", "orc", "organic rankine",
    # ESCO / EPC  [new]
    "energy performance contract", "ενεργειακη συμβαση",
    "guaranteed savings", "εγγυημενη εξοικονομηση", "energy services",
    # EU Funding  [new]
    "innovation fund", "life program", "life clean energy",
    "ταμειο ανακαμψης", "recovery fund", "rrf", "εσπα",
    "horizon europe", "cbam", "κοινωνικο κλιματικο ταμειο",
    "social climate fund", "accelerateeu", "accelerate eu",
    # Industrial Decarbonisation  [new]
    "αποανθρακοποιηση βιομηχανια", "industrial decarbonization",
    "βιομηχανικη ενεργεια", "industrial energy",
    "energy intensive industry", "net zero industry",
    "clean industrial deal",
    # Hydrogen
    "πρασινο υδρογονο", "green hydrogen", "electrolyzer",
    "fuel cell", "power to x",
    # Policy / Market design
    "υπεν", "ypen", "ρααευ", "ppa", "cfd", "fit", "auctions", "ets",
]

NEGATIVE: List[str] = [
    "αθλη", "πολιτισ", "ψυχαγωγ", "μαγειρ", "συνταγ", "μοδα",
    "υγεια", "πανδημ", "κορονο", "τουρισ", "αυτοκινητ",
    "sports", "entertainment",
]

# Weights rebalanced for Enerwave EE / industrial focus
WEIGHTS: dict = {
    "efficiency":        6,   # ↑↑  core business
    "heatpump":          5,   # ↑↑
    "solar_thermal":     5,   # NEW — SUNBREWED / CST service line
    "chp_cogen":         5,   # NEW — CHP / trigeneration service line
    "esco_epc":          5,   # NEW — contractual EE models
    "eu_funding":        5,   # NEW — funding / programme intelligence
    "industrial_decarb": 4,   # NEW — target sector
    "policy":            4,
    "gas":               3,
    "pv":                3,   # ↓  less direct for Enerwave
    "bess":              3,
    "wind":              2,   # ↓↓  not a core Enerwave service
}

GROUPS: dict = {
    "efficiency": [
        "εξοικονομηση", "ενεργειακη αναβαθμιση", "εξοικονομω",
        "energy efficiency", "ενεργειακη αποδοση", "efficient",
        "energy audit", "ενεργειακος ελεγχος",
        "bems", "ems", "bas", "building automation",
        "commissioning", "retrocommissioning",
        "θερμικη μονωση", "u-value", "building envelope",
        "hvac", "hvac optimization", "air sealing", "airtightness",
        "retrofit", "led", "led lighting", "vfd",
        "variable speed drive", "ie3", "ie4",
        "heat recovery", "waste heat",
    ],
    "heatpump": [
        "heat pump", "αντλια θερμοτητας", "αντλιες θερμοτητας",
        "air-to-water", "air to water", "geothermal heat pump",
        "ground source", "district heating",
    ],
    "solar_thermal": [
        "solar thermal", "ηλιοθερμικ", "cst",
        "concentrating solar", "παραβολικ κατοπτρ",
        "parabolic trough", "process heat",
        "θερμοτητα διεργασιας", "industrial heat",
        "flat plate collector", "vacuum tube",
        "ηλιακη θερμοτητα", "solar process heat",
    ],
    "chp_cogen": [
        "chp", "συμπαραγωγη", "cogeneration",
        "combined heat and power", "τριπαραγωγη",
        "trigeneration", "orc", "organic rankine",
        "micro-chp", "biomass chp",
    ],
    "esco_epc": [
        "esco", "epc", "energy performance contract",
        "ενεργειακη συμβαση", "guaranteed savings",
        "εγγυημενη εξοικονομηση", "shared savings",
        "energy services", "ενεργειακες υπηρεσιες",
        "m&v", "measurement and verification", "ipmvp", "iso 50001",
    ],
    "eu_funding": [
        "innovation fund", "life program", "life clean energy",
        "ταμειο ανακαμψης", "recovery fund", "rrf", "εσπα",
        "horizon europe", "cbam",
        "κοινωνικο κλιματικο ταμειο", "social climate fund",
        "accelerateeu", "accelerate eu",
        "κρατικες ενισχυσεις", "state aid energy",
    ],
    "industrial_decarb": [
        "αποανθρακοποιηση βιομηχανια", "industrial decarbonization",
        "βιομηχανικη ενεργεια", "industrial energy",
        "energy intensive industry", "net zero industry",
        "clean industrial deal", "βιομηχανικη μεταβαση",
        "deep renovation", "heavy industry",
    ],
    "pv": [
        "φωτοβολ", "φβ", "pv", "πανελ", "inverter",
        "net metering", "αυτοκαταναλωση", "zero feed in",
        "net billing", "virtual net billing",
    ],
    "bess": [
        "μπαταρ", "battery", "bess", "soc", "state of charge",
        "round trip efficiency", "lfp", "nmc", "flow battery",
        "αντλησιοταμιευση", "pumped storage",
    ],
    "wind": [
        "αιολικ", "wind", "ανεμογεννητρ", "turbine",
        "onshore wind", "offshore wind", "repowering", "wind farm",
    ],
    "gas": [
        "φυσικο αεριο", "gas", "lng", "fsru", "αγωγος",
        "pipeline", "eastmed", "tap", "igb",
        "upstream", "exploration", "κοιτασμα", "πετρελ", "διυλιστ",
    ],
    "policy": [
        "υπεν", "ypen", "ρααευ", "ρυθμιστικη αρχη",
        "auctions", "fit", "cfd", "ppa", "ets",
    ],
}

# Display order for thematic report sections
THEMES: List[Tuple[str, List[str]]] = [
    ("⚡ Εξοικονόμηση & Ενεργειακή Αναβάθμιση",   ["efficiency", "heatpump", "esco_epc"]),
    ("☀️  Ηλιοθερμικά & Φωτοβολταϊκά",             ["solar_thermal", "pv"]),
    ("💰 Χρηματοδοτήσεις & Πολιτική",               ["eu_funding", "policy"]),
    ("🏭 Βιομηχανία & Συμπαραγωγή (CHP)",           ["chp_cogen", "industrial_decarb"]),
    ("🔋 Αποθήκευση & Αιολικά",                      ["bess", "wind"]),
    ("⛽ Αέριο, Πετρέλαιο & Αγορές",                ["gas"]),
    ("🌐 Γενικά Ενεργειακά",                         []),  # catch-all
]

# ── Helpers ────────────────────────────────────────────────────────
def is_energy_title(title: str) -> bool:
    t = normalize(title)
    if any(n in t for n in NEGATIVE):
        return False
    return any(k in t for k in KEYWORDS)

def score_title(title: str) -> int:
    t = normalize(title)
    score = 0
    for group, words in GROUPS.items():
        if any(w in t for w in words):
            score += WEIGHTS.get(group, 1)
    if any(w in t for w in ["ενεργεια", "ηλεκτρ"]):
        score += 1
    return score

def dominant_group(title: str) -> str:
    """Return the highest-weighted group that matches the title."""
    t = normalize(title)
    best_group, best_weight = "", 0
    for group, words in GROUPS.items():
        if any(w in t for w in words):
            w = WEIGHTS.get(group, 1)
            if w > best_weight:
                best_group, best_weight = group, w
    return best_group

def theme_index(title: str) -> int:
    """Return index into THEMES for this title (last bucket = catch-all)."""
    g = dominant_group(title)
    for i, (_, groups) in enumerate(THEMES):
        if g in groups:
            return i
    return len(THEMES) - 1

# ══════════════════════════════════════════════════════════════════
#  HTTP / SCRAPING
# ══════════════════════════════════════════════════════════════════
HEADERS = {
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

def _absolutize(base: str, href: str) -> str:
    try:
        return urljoin(base, href)
    except Exception:
        return href

def _is_useful_text(text: str) -> bool:
    t = normalize(text)
    if len(t) < 8:
        return False
    bad = ["read more", "περισσοτερα", "share", "mailto:", "javascript:"]
    return not any(b in t for b in bad)

def scrape_site(url: str) -> List[Tuple[str, str]]:
    """Return de-duplicated (title, link) list from a single site."""
    if url in SKIP_SITES:
        return []
    try:
        r = _get_session().get(url, headers=HEADERS, timeout=SITE_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, _BS_PARSER)
        seen:    set                    = set()
        results: List[Tuple[str, str]] = []
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            href  = a["href"]
            if not title or not href:
                continue
            if not _is_useful_text(title):
                continue
            link = _absolutize(url, href)
            if link.startswith("#"):
                continue
            key = (normalize(title), normalize(link))
            if key in seen:
                continue
            seen.add(key)
            results.append((title, link))
        return results
    except Exception as e:
        print(f"[WARN] {url}: {e}", file=sys.stderr)
        return []

# ══════════════════════════════════════════════════════════════════
#  DATE EXTRACTION
# ══════════════════════════════════════════════════════════════════
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
    for time_tag in soup.find_all("time"):
        v = time_tag.get("datetime") or time_tag.get_text(strip=True)
        if v:
            candidates.append(v)
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            objs = data if isinstance(data, list) else [data]
            for obj in objs:
                if isinstance(obj, dict):
                    for key in ("datePublished", "dateCreated", "dateModified"):
                        if obj.get(key):
                            candidates.append(obj[key])
        except Exception:
            pass
    for raw in candidates:
        dt = _try_parse_dt(raw)
        if dt:
            return dt
    return None

def _fetch_article_dt(url: str) -> Optional[datetime.datetime]:
    try:
        r = _get_session().get(url, headers=HEADERS, timeout=DATE_TIMEOUT)
        r.raise_for_status()
        return _extract_dt_from_html(r.text)
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════════
#  CROSS-SITE DEDUPLICATION  (Jaccard on normalised title tokens)
# ══════════════════════════════════════════════════════════════════
_STOP: frozenset = frozenset({
    "η", "ο", "τα", "το", "της", "στη", "στο", "για", "και", "με",
    "που", "στα", "του", "των", "εν", "the", "a", "an", "of", "in",
    "to", "for", "on", "at", "by", "is", "are", "as",
})

def _tokens(title: str) -> frozenset:
    return frozenset(normalize(title).split()) - _STOP

def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def dedup_cross_site(
    articles: List[Tuple[str, str, str]]
) -> List[Tuple[str, str, str]]:
    """
    Collapse near-duplicate titles (Jaccard ≥ 0.65) across sites,
    keeping the highest-scored version.
    Input/output: [(title, link, site), ...]
    """
    result: List[Tuple[str, str, str]] = []
    tsets:  List[frozenset]            = []
    for title, link, site in articles:
        tset  = _tokens(title)
        score = score_title(title)
        merged = False
        for i, existing in enumerate(tsets):
            if _jaccard(tset, existing) >= 0.65:
                if score > score_title(result[i][0]):
                    result[i] = (title, link, site)
                    tsets[i]  = tset
                merged = True
                break
        if not merged:
            result.append((title, link, site))
            tsets.append(tset)
    return result

# ══════════════════════════════════════════════════════════════════
#  ARTICLE TYPE ALIAS
# ══════════════════════════════════════════════════════════════════
# (title, link, site, published_dt)
Article = Tuple[str, str, str, Optional[datetime.datetime]]

# ══════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════
def collect_and_enrich() -> List[Article]:
    """
    1. Scrape all sites.
    2. Filter for energy relevance.
    3. Cross-site dedup.
    4. Parallel date enrichment for top MAX_DATE_FETCH by score.
    5. Age filter.
    6. Final sort (date desc, then score desc).
    """
    # Step 1–2: Scrape + filter
    raw: List[Tuple[str, str, str]] = []
    for site in SITES:
        print(f"[INFO] Scraping {site} …", flush=True)
        for title, link in scrape_site(site):
            if is_energy_title(title):
                raw.append((title, link, site))
        time.sleep(0.3)   # politeness

    # Step 3: Cross-site dedup
    raw = dedup_cross_site(raw)
    print(f"[INFO] After dedup: {len(raw)} unique articles", flush=True)

    # Step 4: Sort by score, then parallel date enrichment
    raw.sort(key=lambda x: score_title(x[0]), reverse=True)
    top  = raw[:MAX_DATE_FETCH]
    rest = raw[MAX_DATE_FETCH:]

    enriched: List[Article] = []

    def _enrich(item: Tuple[str, str, str]) -> Article:
        title, link, site = item
        return (title, link, site, _fetch_article_dt(link))

    with ThreadPoolExecutor(max_workers=DATE_WORKERS) as ex:
        future_to_item = {ex.submit(_enrich, item): item for item in top}
        for fut in as_completed(future_to_item):
            orig = future_to_item[fut]
            try:
                enriched.append(fut.result())
            except Exception:
                enriched.append((orig[0], orig[1], orig[2], None))

    enriched += [(t, l, s, None) for t, l, s in rest]

    # Step 5: Age filter — drop articles with a known date older than MAX_AGE_DAYS
    if MAX_AGE_DAYS > 0:
        cutoff = datetime.datetime.now(tz=ATHENS_TZ) - datetime.timedelta(days=MAX_AGE_DAYS)
        enriched = [
            a for a in enriched
            if a[3] is None or a[3] >= cutoff    # keep unknown dates
        ]

    # Step 6: Sort — dated articles first (newest), then undated by score
    def _sort_key(a: Article) -> Tuple:
        dt    = a[3] or datetime.datetime.min.replace(tzinfo=ZoneInfo("UTC"))
        score = score_title(a[0])
        return (dt, score)

    enriched.sort(key=_sort_key, reverse=True)
    return enriched

# ══════════════════════════════════════════════════════════════════
#  REPORT BUILDERS
# ══════════════════════════════════════════════════════════════════
def _fmt_dt(dt: Optional[datetime.datetime]) -> str:
    return dt.strftime("%d/%m %H:%M") if dt else "—"

def _short_site(site: str) -> str:
    return (site.replace("https://www.", "")
               .replace("https://", "")
               .split("/")[0])

def _grouped(articles: List[Article]) -> List[List[Article]]:
    """Split articles into len(THEMES) buckets based on dominant group."""
    buckets: List[List[Article]] = [[] for _ in THEMES]
    for a in articles:
        buckets[theme_index(a[0])].append(a)
    return buckets

# ── Plain text ─────────────────────────────────────────────────────
def build_text_report(articles: List[Article]) -> str:
    now = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")
    lines = [f"🔋 DAILY ENERGY NEWS — {now} (Europe/Athens)", ""]

    lines += [
        "═" * 62,
        f"🔝  TOP {MAX_TOP} HIGHLIGHTS",
        "═" * 62,
    ]
    for a in articles[:MAX_TOP]:
        title, link, site, dt = a
        lines.append(f"  [{score_title(title):2d}] [{_fmt_dt(dt)}]  {title}")
        lines.append(f"        {link}")
        lines.append("")

    buckets = _grouped(articles)
    for (theme_name, _), bucket in zip(THEMES, buckets):
        if not bucket:
            continue
        lines += ["─" * 62, theme_name, "─" * 62]
        for title, link, site, dt in bucket:
            src = _short_site(site)
            lines.append(f"  [{score_title(title):2d}] [{_fmt_dt(dt)}]  {title}  «{src}»")
            lines.append(f"        {link}")
        lines.append("")

    return "\n".join(lines)

# ── HTML ───────────────────────────────────────────────────────────
def build_html_report(articles: List[Article]) -> str:
    now = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")

    css = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
           color: #1a1a1a; background: #f0f2f5; padding: 20px; }
    .card { background: #fff; border-radius: 10px; padding: 20px;
            margin-bottom: 16px; box-shadow: 0 1px 5px rgba(0,0,0,.07); }
    h1    { font-size: 22px; color: #0d47a1; }
    .meta { color: #777; font-size: 12px; margin-top: 4px; }
    h2    { font-size: 14px; font-weight: 700; color: #333; margin-bottom: 12px;
            border-bottom: 2px solid #e3e8f0; padding-bottom: 6px; }
    .item { margin: 7px 0; display: flex; align-items: baseline;
            gap: 6px; flex-wrap: wrap; }
    .score { min-width: 26px; border-radius: 4px; padding: 2px 6px;
             font-size: 11px; font-weight: 700; text-align: center;
             flex-shrink: 0; background: #e8f0fe; color: #1565c0; }
    .score.hi { background: #1565c0; color: #fff; }
    a   { color: #0d47a1; text-decoration: none; font-size: 13px; }
    a:hover { text-decoration: underline; }
    .dt  { color: #bbb; font-size: 11px; white-space: nowrap; }
    .src { color: #ccc; font-size: 10px; }
    """

    def badge(score: int) -> str:
        cls = "score hi" if score >= 8 else "score"
        return f'<span class="{cls}">{score}</span>'

    def item_html(a: Article) -> str:
        title, link, site, dt = a
        s   = score_title(title)
        src = _short_site(site)
        return (
            f'<div class="item">{badge(s)}'
            f'<a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>'
            f'<span class="dt">{_fmt_dt(dt)}</span>'
            f'<span class="src">{src}</span></div>'
        )

    parts = [
        '<div class="card">',
        '  <h1>🔋 DAILY ENERGY NEWS</h1>',
        f'  <p class="meta">Europe/Athens &middot; {now} &middot; {len(articles)} articles</p>',
        '</div>',
    ]

    # Top Highlights
    parts += ['<div class="card">', f'<h2>🔝 Top {MAX_TOP} Highlights</h2>']
    for a in articles[:MAX_TOP]:
        parts.append(item_html(a))
    parts.append('</div>')

    # Thematic sections
    for (theme_name, _), bucket in zip(THEMES, _grouped(articles)):
        if not bucket:
            continue
        parts += ['<div class="card">', f'<h2>{theme_name}</h2>']
        for a in bucket:
            parts.append(item_html(a))
        parts.append('</div>')

    return (
        "<!doctype html><html>"
        "<head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<style>{css}</style></head>"
        f"<body>{''.join(parts)}</body></html>"
    )

# ══════════════════════════════════════════════════════════════════
#  EMAIL
# ══════════════════════════════════════════════════════════════════
def send_email_html(subject: str, body_text: str, body_html: str) -> None:
    EMAIL_USERNAME  = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")
    EMAIL_CC        = os.getenv("EMAIL_CC",  "").strip()
    EMAIL_BCC       = os.getenv("EMAIL_BCC", "").strip()
    SMTP_SERVER     = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT       = int(os.getenv("SMTP_PORT", "587"))

    if not (EMAIL_USERNAME and EMAIL_PASSWORD and EMAIL_RECIPIENT):
        raise RuntimeError(
            "Missing env vars: EMAIL_USERNAME / EMAIL_PASSWORD / EMAIL_RECIPIENT"
        )

    to_list   = [x.strip() for x in EMAIL_RECIPIENT.split(",") if x.strip()]
    cc_list   = [x.strip() for x in EMAIL_CC.split(",")        if x.strip()]
    bcc_list  = [x.strip() for x in EMAIL_BCC.split(",")       if x.strip()]
    all_rcpts = to_list + cc_list + bcc_list
    if not all_rcpts:
        raise RuntimeError("EMAIL_RECIPIENT is empty.")

    msg = MIMEMultipart("alternative")
    try:
        local, domain = EMAIL_USERNAME.split("@", 1)
        msg["From"] = str(Address(display_name="Daily Energy News | Enerwave",
                                  username=local, domain=domain))
    except Exception:
        msg["From"] = EMAIL_USERNAME

    msg["To"]         = ", ".join(to_list)
    if cc_list:
        msg["Cc"]     = ", ".join(cc_list)
    msg["Subject"]    = subject
    msg["Date"]       = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html",  "utf-8"))

    attempts = [
        ("STARTTLS", SMTP_SERVER, SMTP_PORT),
        ("SSL",      SMTP_SERVER, 465),
    ]
    last_exc = None
    for mode, host, port in attempts:
        for _ in range(2):
            server = None
            try:
                if mode == "STARTTLS":
                    server = smtplib.SMTP(host, port, timeout=20)
                    server.ehlo(); server.starttls(); server.ehlo()
                else:
                    server = smtplib.SMTP_SSL(host, port, timeout=20)
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.sendmail(EMAIL_USERNAME, all_rcpts, msg.as_string())
                return
            except Exception as e:
                last_exc = e
                time.sleep(2)
            finally:
                try:
                    if server:
                        server.quit()
                except Exception:
                    pass
    raise RuntimeError(f"Email failed after all retries: {last_exc}")

# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    articles = collect_and_enrich()
    print(f"[INFO] Final article count: {len(articles)}", flush=True)

    if not articles:
        if os.getenv("SEND_EMPTY", "false").lower() == "true":
            msg = "No energy news found today."
            send_email_html("Daily Energy News — No results", msg, f"<p>{msg}</p>")
        else:
            print("[INFO] No articles — skipping email (set SEND_EMPTY=true to override).")
        return

    today   = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y")
    subject = f"Energy News | Enerwave | {today} | {len(articles)} articles"

    try:
        send_email_html(subject, build_text_report(articles), build_html_report(articles))
        print("📨 Email sent successfully!", flush=True)
    except Exception as e:
        print(f"❌ Email failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
