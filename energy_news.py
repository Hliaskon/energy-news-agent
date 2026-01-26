
import os
import sys
import time
import json
import datetime
import unicodedata
from urllib.parse import urljoin
from typing import List, Tuple, Dict

# HTTP & parsing
import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None

from bs4 import BeautifulSoup

# Email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.headerregistry import Address
from email.utils import formatdate, make_msgid

# Dates
from dateutil import parser as dateparser
from zoneinfo import ZoneInfo  # stdlib (Python ≥3.9)

# --------------------------------
# Sources
# --------------------------------
SITES = [
    # ---- Core ελληνικά ενεργειακά sites ----
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

    # ---- Διεθνή sites που καλύπτουν Ελλάδα ----
    "https://greekreporter.com",
    "https://balkangreenenergynews.com",
    "https://energynews.oedigital.com",
    "https://www.reuters.com",
    "https://www.bloomberg.com",
    "https://www.spglobal.com",
    "https://www.ft.com",
     "https://www.euronews.com",

    # ---- ΑΠΕ / Τεχνική ενημέρωση ----
    "https://www.pv-magazine.com/tag/greece/",
    "https://renewablesnow.com/topic/greece/",
    "https://energymag.gr/",
    "https://www.euractiv.com/section/energy/",
    "https://www.euronews.com/tag/energy",

    # ---- Οργανισμοί / Αρχές ----
    "https://ypen.gov.gr/category/anakoinoseis/",
    "https://www.admie.gr/en/news",
    "https://www.raae.gr/anakoinoseis/",


    
    # --- Energy efficiency heavy sources (GR/EU/Intl) ---

    # Greece / GR-focused EE
    "https://exoikonomo2025.gov.gr/",                               # Official Exoikonomo portal [1](https://exoikonomo2025.gov.gr/)
    "https://www.ot.gr/category/green/eksoikonomisi/",              # OT - Exoikonomisi section [2](https://www.ot.gr/category/green/eksoikonomisi/)
    "https://www.skai.gr/tags/eksoikonomisi-energeias",             # SKAI EE tag [3](https://www.skai.gr/tags/eksoikonomisi-energeias)
    "https://www.insider.gr/epiheiriseis/367163/exoikonomisi-energeias-poia-programmata-pairnoyn-paratasi",  # Insider feature [4](https://www.insider.gr/epiheiriseis/367163/exoikonomisi-energeias-poia-programmata-pairnoyn-paratasi)
    "https://www.newmoney.gr/roh/palmos-oikonomias/energeia/exikonomisi-energias-pia-programmata-piran-paratasi-oles-i-imerominies/",  # Newmoney recap [5](https://www.newmoney.gr/roh/palmos-oikonomias/energeia/exikonomisi-energias-pia-programmata-piran-paratasi-oles-i-imerominies/)
    "https://greekreporter.com/2025/12/17/aging-homes-funding-gaps-greece-energy-efficiency-risks/",         # GreekReporter analysis [6](https://greekreporter.com/2025/12/17/aging-homes-funding-gaps-greece-energy-efficiency-risks/)
    "https://www.dnews.gr/eidhseis/news-in-english/537235/greece-unveils-ambitious-roadmap-to-cut-energy-use-in-buildings-by-2030",    # DNews roadmap [7](https://www.dnews.gr/eidhseis/news-in-english/537235/greece-unveils-ambitious-roadmap-to-cut-energy-use-in-buildings-by-2030)
    "https://en.protothema.gr/2025/01/19/four-e1-billion-programs-to-kick-start-energy-efficiency-upgrades-in-2025/",                  # ProtoThema EN [8](https://en.protothema.gr/2025/01/19/four-e1-billion-programs-to-kick-start-energy-efficiency-upgrades-in-2025/)
    "https://www.tovima.com/society/greece-launches-energy-efficiency-programs/",                            # ToVima EN summary [9](https://www.tovima.com/society/greece-launches-energy-efficiency-programs/)
    "https://www.topics.gr/diafora/eksoikonomhsh-energeias/",                                               # Topics.gr aggregator [10](https://www.topics.gr/diafora/eksoikonomhsh-energeias/)

    # EU / Institutions / Knowledge hubs
    "https://energy.ec.europa.eu/news/energy-efficiency-new-impetus-reduce-energy-consumption-2025-05-21_en", # DG ENER news [11](https://energy.ec.europa.eu/news/energy-efficiency-new-impetus-reduce-energy-consumption-2025-05-21_en)
    "https://energy.ec.europa.eu/news/focus-reaching-eus-energy-efficiency-target-2025-07-15_en",             # DG ENER focus [12](https://energy.ec.europa.eu/news/focus-reaching-eus-energy-efficiency-target-2025-07-15_en)
    "https://cinea.ec.europa.eu/news-events/news/life-shows-path-energy-efficiency-c4e-forum-2025-06-06_en",  # CINEA LIFE/C4E [13](https://cinea.ec.europa.eu/news-events/news/life-shows-path-energy-efficiency-c4e-forum-2025-06-06_en)
    "https://cinea.ec.europa.eu/index_en",                                                                     # CINEA hub [14](https://cinea.ec.europa.eu/index_en)
    "https://build-up.ec.europa.eu/en/news-and-events/news/greeces-programmes-sustainable-heating-and-energy-efficiency",               # BUILD UP Greece EE [15](https://build-up.ec.europa.eu/en/news-and-events/news/greeces-programmes-sustainable-heating-and-energy-efficiency)
    "https://build-up.ec.europa.eu/en/resources-and-tools/publications/energy-efficiency-2024-ieas-annual-analysis-global-energy",      # BUILD UP | IEA EE 2024 [16](https://build-up.ec.europa.eu/en/resources-and-tools/publications/energy-efficiency-2024-ieas-annual-analysis-global-energy)
    "https://www.bpie.eu/news/",                                                                              # BPIE news stream [17](https://www.bpie.eu/news/)

    # International EE analytics
    "https://www.iea.org/news/global-progress-on-energy-efficiency-picks-up-in-2025",                         # IEA EE 2025 update [18](https://www.iea.org/news/global-progress-on-energy-efficiency-picks-up-in-2025)
    "https://www.power-technology.com/news/global-energy-efficiency-progress-2025-iea/",                      # Coverage of IEA EE 2025 [19](https://www.power-technology.com/news/global-energy-efficiency-progress-2025-iea/)
    "https://www.aceee.org/news",                                                                             # ACEEE news/blogs [20](https://www.aceee.org/news)
    "https://www.eceee.org/all-news/news/",                                                                   # eceee news feed [21](https://www.eceee.org/all-news/news/news-2025/us-scorecard-energy-efficiency-upgrades-help-struggling-families-but-most-states-lagging/)

    # Standards / HVAC (useful efficiency context)
    "https://www.ashrae.org/about/news/2024/ashrae-s-new-edition-of-residential-energy-performance-standard-sets-bold-ghg-reduction-and-ieq-targets",  # ASHRAE 90.2-2024 [22](https://www.ashrae.org/about/news/2024/ashrae-s-new-edition-of-residential-energy-performance-standard-sets-bold-ghg-reduction-and-ieq-targets)
    "https://www.facilitiesdive.com/news/ashrae-updates-standard-100-energy-efficiency-existing-buildings-decarbonization/704922/",                    # ASHRAE 100-2024 [23](https://www.facilitiesdive.com/news/ashrae-updates-standard-100-energy-efficiency-existing-buildings-decarbonization/704922/)

    
]

# --------------------------------
# Text normalization
# --------------------------------
ATHENS_TZ = ZoneInfo("Europe/Athens")

def normalize(text: str) -> str:
    """Lowercase + remove Greek accents/diacritics."""
    if not text:
        return ""
    t = text.lower()
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    return t

# --------------------------------
# Keywords / Negative / Scoring
# --------------------------------
KEYWORDS = [
    # General energy & market
    "ενεργεια", "ενεργειακη αγορα", "ενεργειακο κοστος", "κιλοβατωρα", "kwh", "mwh",
    "τιμολογια ρευματος", "προμηθευτες ρευματος", "χονδρεμπορικη", "χρηματιστηριο ενεργειας",
    "dam", "day ahead",

    # Networks
    "ηλεκτρ", "δικτυο μεταφορας", "δικτυο διανομης", "αδμηε", "δεδδηε",
    "διασυνδεση", "interconnector", "ευσταθεια δικτυου", "smart grid", "smart meters",

    # PV
    "φωτοβολ", "φβ", "pv", "πανελ", "modules", "inverter", "μετατροπ", "string", "array",
    "net metering", "αυτοκαταναλωση", "zero feed in",

    # Wind
    "αιολικ", "wind", "ανεμογεννητρ", "turbine", "onshore wind", "offshore wind",
    "repowering", "wind farm",

    # Storage
    "μπαταρ", "battery", "bess", "soc", "state of charge", "round trip efficiency",
    "li ion", "lfp", "nmc", "flow battery", "αντλησιοταμιευση", "pumped storage",

    # Hydro
    "υδροηλεκτρ", "ταμιευτηρ", "francis", "pelton", "υδροηλεκτρικη ισχυς", "υδατινοι ποροι",

    # Gas & hydrocarbons
    "φυσικο αεριο", "gas", "lng", "fsru", "αγωγος", "pipeline",
    "eastmed", "tap", "igb", "upstream", "exploration", "κοιτασμα", "πετρελ", "διυλιστ",

    # Buildings / Efficiency
    "εξοικονομηση", "ενεργειακη αναβαθμιση", "heat pump", "αντλια θερμοτητας",
    "district heating", "τηλεθερμανση", "ενεργειακη κλαση", "θερμικη μονωση",

    # Policy / Market design
    "υπεν", "ypen", "ρααευ", "ρυθμιστικη αρχη", "δημοπρασιες απε", "auctions",
    "fit", "cfd", "ppa", "ets",

    # Hydrogen & tech
    "πρασινο υδρογονο", "green hydrogen", "electrolyzer", "ηλεκτρολυτ",
    "fuel cell", "κυψελη καυσιμου", "power to x", "αποανθρακοποιηση",
    
   # Buildings / Efficiency (NEW block)
    "εξοικονομηση", "ενεργειακη αναβαθμιση", "εξοικονομω", "energy efficiency",
    "energy audit", "ενεργειακος ελεγχος", "esco", "epc", "m&v", "ipmvp",
    "iso 50001", "bems", "ems", "bas", "building automation",
    "commissioning", "retrocommissioning", "optimization",
    "θερμικη μονωση", "θερμογεφυρα", "u-value", "u value", "building envelope",
    "hvac", "hvac optimization", "heat pump", "αντλια θερμοτητας",
    "led", "led lighting", "φωτισμος led",
    "air sealing", "airtightness", "infiltration", "retrofit",
    "vfd", "variable speed drive", "inverter drive", "ie3", "ie4",
    "heat recovery", "waste heat",
]

NEGATIVE = [
    "αθλη", "πολιτισ", "ψυχαγωγ", "μαγειρ", "συνταγ", "μοδα",
    "καιρος", "υγεια", "πανδημ", "κορονο", "τουρισ", "αυτοκινητ",
    "sports", "entertainment"
]

WEIGHTS = {"pv": 1, "bess": 2, "wind": 5, "gas": 4, "policy": 5, "heatpump": 2, "efficiency":3}
GROUPS = {
    "pv": ["φωτοβολ", "φβ", "pv", "πανελ", "inverter", "net metering", "αυτοκαταναλωση", "zero feed in","Net Billing","Virtual Net Billing"],
    "bess": ["μπαταρ", "battery", "bess", "soc", "state of charge", "round trip efficiency", "lfp", "nmc", "flow battery"],
    "wind": ["αιολικ", "wind", "ανεμογεννητρ", "turbine", "onshore wind", "offshore wind", "repowering", "wind farm"],
    "gas": ["φυσικο αεριο", "gas", "lng", "fsru", "αγωγος", "pipeline", "eastmed", "tap", "igb"],
    "policy": ["υπεν", "ypen", "ρααευ", "ρυθμιστικη αρχη", "ppa", "cfd", "fit", "auctions", "ets"],
    "heatpump": ["heat pump", "αντλια θερμοτητας", "hp", "air‑to‑water", "geothermal heat pump"],

"efficiency": [
        # General / programs
        "εξοικονομηση", "ενεργειακη αναβαθμιση", "εξοικονομω",
        "energy efficiency", "efficient",
        "energy audit", "ενεργειακος ελεγχος", "audit",
        "m&v", "measurement and verification", "ipmvp",
        "esco", "epc", "iso 50001",

        # Controls & systems
        "bems", "ems", "bas", "building automation",
        "commissioning", "retrocommissioning", "optimization",
        "smart thermostat", "θερμοστατης", "smart thermostats",

        # Industrial
        "vfd", "variable speed drive", "inverter drive", "αντιστροφεας",
        "ie3", "ie4", "υψηλης αποδοσης κινητηρας",
        "heat recovery", "ανακτηση θερμοτητας",
        "waste heat", "ανακτηση αποβλητης θερμοτητας",

        # Envelope & hvac
        "θερμικη μονωση", "μονωση", "θερμογεφυρα", "θερμογέφυρες",
        "u-value", "u value", "building envelope", "κελυφος",
        "hvac optimization", "hvac", "heat pump", "αντλια θερμοτητας",
        "air sealing", "airtightness", "infiltration", "retrofit",
        "led", "led lighting", "φωτισμος led", "υψηλης αποδοσης φωτισμος",
    ]

}

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
            score += WEIGHTS.get(group, 0)
    if any(w in t for w in ["ενεργεια", "ηλεκτρ"]):
        score += 1
    return score

# --------------------------------
# HTTP / Scraping
# --------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36"
}

# Prefer lxml if available; fallback to stdlib parser
_BS_PARSER = "lxml"
try:
    BeautifulSoup("<html></html>", _BS_PARSER)
except Exception:
    _BS_PARSER = "html.parser"

_SESSION = None
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
            s.mount("http://", HTTPAdapter(max_retries=retry))
            s.mount("https://", HTTPAdapter(max_retries=retry))
        _SESSION = s
    return _SESSION

def absolutize(base: str, href: str) -> str:
    try:
        return urljoin(base, href)
    except Exception:
        return href

def is_probably_article_text(text: str) -> bool:
    """Filter out very short/irrelevant link texts."""
    t = normalize(text)
    if len(t) < 8:
        return False
    bad_fragments = ["read more", "περισσοτερα", "share", "mailto:", "javascript:"]
    if any(b in t for b in bad_fragments):
        return False
    return True

def scrape_site(url: str, timeout: int = 12) -> List[Tuple[str, str]]:
    """Return list (title, link) from a site."""
    results: List[Tuple[str, str]] = []
    try:
        r = _get_session().get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, _BS_PARSER)
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            href = a["href"]
            if not title or not href:
                continue
            if not is_probably_article_text(title):
                continue
            link = absolutize(url, href)
            if link.startswith("#"):
                continue
            results.append((title, link))
        # dedup
        dedup = []
        seen = set()
        for t, l in results:
            key = (normalize(t), normalize(l))
            if key in seen:
                continue
            seen.add(key)
            dedup.append((t, l))
        return dedup
    except Exception as e:
        print(f"[WARN] Σφάλμα στο {url}: {e}", file=sys.stderr)
        return []

# --------------------------------
# Dates
# --------------------------------
def try_parse_dt(value: str):
    """Parse any date → Europe/Athens. If missing tz → assume UTC."""
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

def extract_published_dt_from_article(html: str):
    soup = BeautifulSoup(html, _BS_PARSER)
    candidates = []

    # 1) Meta tags
    for attr in ("property", "name"):
        for key in ("article:published_time", "og:updated_time", "pubdate", "publishdate",
                    "timestamp", "dc.date", "dc.date.issued", "date"):
            tag = soup.find("meta", {attr: key})
            if tag and tag.get("content"):
                candidates.append(tag.get("content"))

    # 2) <time> elements
    for time_tag in soup.find_all("time"):
        dtv = time_tag.get("datetime") or time_tag.get_text(strip=True)
        if dtv:
            candidates.append(dtv)

    # 3) JSON-LD
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            objs = data if isinstance(data, list) else [data]
            for obj in objs:
                if isinstance(obj, dict):
                    for key in ("datePublished", "dateCreated", "dateModified", "uploadDate"):
                        if obj.get(key):
                            candidates.append(obj[key])
        except Exception:
            pass

    for raw in candidates:
        dt = try_parse_dt(raw)
        if dt:
            return dt
    return None

def fetch_article_published_dt(url: str, timeout: int = 10):
    """Extra fetch on article page to extract publish date/time."""
    try:
        r = _get_session().get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return extract_published_dt_from_article(r.text)
    except Exception:
        return None

# --------------------------------
# Filter & sort
# --------------------------------
def filter_energy_news(news_list: List[Tuple[str, str]]) -> List[Tuple[str, str, datetime.datetime]]:
    """
    Return [(title, link, published_dt_athens)], sorted by published_dt (desc) and score (desc),
    with dedup and a limit on extra per-article fetches per site for performance.
    """
    seen_links = set()
    tmp: List[Tuple[str, str]] = []

    for title, link in news_list:
        if not title or not link:
            continue
        if is_energy_title(title):
            ln = normalize(link)
            if ln in seen_links:
                continue
            seen_links.add(ln)
            tmp.append((title, link))

    # sort by score first
    tmp.sort(key=lambda x: score_title(x[0]), reverse=True)

    # enrich with published_dt for the most relevant
    MAX_ARTICLES_FETCH_DT = 12
    enriched: List[Tuple[str, str, datetime.datetime]] = []

    for i, (title, link) in enumerate(tmp):
        published_dt = None
        if i < MAX_ARTICLES_FETCH_DT:
            published_dt = fetch_article_published_dt(link)
        enriched.append((title, link, published_dt))

    def sort_key(item):
        title, link, dt = item
        base_dt = dt or datetime.datetime.min.replace(tzinfo=ZoneInfo("UTC"))
        return (base_dt, score_title(title))

    enriched.sort(key=sort_key, reverse=True)
    return enriched

# --------------------------------
# Report builders (plain + HTML)
# --------------------------------
def fmt_dt(dt: datetime.datetime):
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"

def build_text_report(news_dict: Dict[str, List[Tuple[str, str, datetime.datetime]]]) -> str:
    today = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")
    lines = [f"🔋 DAILY ENERGY NEWS REPORT — {today} (Europe/Athens)", ""]
    for site, items in news_dict.items():
        lines.append(f"============================")
        lines.append(f"SITE: {site}")
        lines.append(f"============================")
        lines.append("")
        if not items:
            lines.append("❗ Δεν βρέθηκαν ενεργειακές ειδήσεις.")
            lines.append("")
        else:
            for title, link, published_dt in items:
                score = score_title(title)
                lines.append(f"• ({score}) [{fmt_dt(published_dt)}] {title}")
                lines.append(f"  {link}")
                lines.append("")
    return "\n".join(lines)

def build_html_report(news_dict: Dict[str, List[Tuple[str, str, datetime.datetime]]]) -> str:
    today = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")
    style = """
    body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:#222; }
    h1 { font-size: 20px; margin-bottom: 8px; }
    .ts { color:#555; font-size: 12px; margin-bottom: 16px; }
    .site { border-top:1px solid #eee; padding-top:12px; margin-top:12px; }
    .item { margin: 8px 0; }
    .score { display:inline-block; min-width:28px; background:#eef; color:#224; border:1px solid #ccd; border-radius:4px; padding:2px 6px; font-size:12px; margin-right:6px; }
    .dt { color:#666; font-size:12px; margin-left:4px; }
    a { color:#0366d6; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .empty { color:#a33; font-style: italic; }
    """
    parts = [f"<h1>🔋 DAILY ENERGY NEWS REPORT</h1>",
             f"<div class='ts'>Europe/Athens — {today}</div>"]
    for site, items in news_dict.items():
        parts.append(f"<div class='site'><strong>SITE:</strong> {site}</div>")
        if not items:
            parts.append("<div class='item empty'>❗ Δεν βρέθηκαν ενεργειακές ειδήσεις.</div>")
        else:
            for title, link, published_dt in items:
                score = score_title(title)
                dt_s = fmt_dt(published_dt)
                parts.append(
                    f"<div class='item'><span class='score'>{score}</span>"
                    f"<a href='{link}' target='_blank' rel='noopener noreferrer'>{title}</a>"
                    f"<span class='dt'>[{dt_s}]</span></div>"
                )
    html = f"<!doctype html><html><head><meta charset='utf-8'><style>{style}</style></head><body>{''.join(parts)}</body></html>"
    return html

# --------------------------------
# Email (HTML + plain fallback)
# --------------------------------
def send_email_html(subject: str, body_text: str, body_html: str) -> None:
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")  # comma-separated supported
    EMAIL_CC = os.getenv("EMAIL_CC", "").strip()
    EMAIL_BCC = os.getenv("EMAIL_BCC", "").strip()
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

    if not EMAIL_USERNAME or not EMAIL_PASSWORD or not EMAIL_RECIPIENT:
        raise RuntimeError("Missing env vars: EMAIL_USERNAME / EMAIL_PASSWORD / EMAIL_RECIPIENT")

    to_list = [x.strip() for x in EMAIL_RECIPIENT.split(",") if x.strip()]
    cc_list = [x.strip() for x in EMAIL_CC.split(",") if x.strip()]
    bcc_list = [x.strip() for x in EMAIL_BCC.split(",") if x.strip()]
    all_rcpts = to_list + cc_list + bcc_list
    if not all_rcpts:
        raise RuntimeError("EMAIL_RECIPIENT is empty.")

    # MIME alternative (plain + HTML)
    msg = MIMEMultipart("alternative")
    try:
        local, domain = EMAIL_USERNAME.split("@", 1)
        msg["From"] = str(Address(display_name="Daily Energy News Agent", username=local, domain=domain))
    except Exception:
        msg["From"] = EMAIL_USERNAME
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()

    # Attach plain and HTML versions
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    # SMTP with STARTTLS then SSL fallback
    attempts = [("STARTTLS", SMTP_SERVER, SMTP_PORT), ("SSL", SMTP_SERVER, 465)]
    last_exc = None
    for mode, host, port in attempts:
        for _try in range(2):
            server = None
            try:
                if mode == "STARTTLS":
                    server = smtplib.SMTP(host, port, timeout=20)
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
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
                    if server is not None:
                        server.quit()
                except Exception:
                    pass
    raise RuntimeError(f"Failed to send email after retries: {last_exc}")

# --------------------------------
# MAIN
# --------------------------------
def main():
    all_results: Dict[str, List[Tuple[str, str, datetime.datetime]]] = {}

    for site in SITES:
        print(f"[INFO] Scraping {site} ...")
        raw = scrape_site(site)
        filt = filter_energy_news(raw)
        all_results[site] = filt
        time.sleep(0.5)  # politeness

    text_report = build_text_report(all_results)
    html_report = build_html_report(all_results)

    SEND_EMPTY = os.getenv("SEND_EMPTY", "false").lower() == "true"
    empty_total = all(len(items) == 0 for items in all_results.values())

    if SEND_EMPTY or (not empty_total):
        try:
            send_email_html("Daily Energy News Report (HTML)", text_report, html_report)
            print("📨 Email (HTML) sent successfully!")
        except Exception as e:
            print(f"❌ Failed to send email: {e}", file=sys.stderr)
    else:
        print("ℹ️ No energy news found — not sending email (set SEND_EMPTY=true to force).")

if __name__ == "__main__":
    main()
