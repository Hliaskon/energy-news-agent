
import os
import sys
import time
import datetime
import unicodedata
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# -----------------------------
# 1) ΡΥΘΜΙΣΕΙΣ / ΠΗΓΕΣ
# -----------------------------
SITES = [
    # ---- Core ελληνικά ενεργειακά sites ----
    "https://www.energypress.gr/",
    "https://www.naftemporiki.gr/energy/",
    "https://www.ot.gr/category/energeia/",
    "https://www.capital.gr/energia",
    "https://www.moneyreview.gr/category/business/energy/",
    "https://www.imerisia.gr/energeia",
    "https://www.cnn.gr/oikonomia/energeia",
    "https://www.kathimerini.gr/economy/energy/",
    "https://www.powergame.gr/category/energeia/",
    "https://www.euro2day.gr/news/economy/energeia",
    "https://www.liberal.gr/energeia",
    "https://www.energyin.gr/",
    "https://ecotec.gr/category/energy/",
    "https://www.greenagenda.gr/category/energy/",
    "https://energynews.gr/",

    # ---- Διεθνή sites που καλύπτουν Ελλάδα ----
    "https://greekreporter.com/greek-news/energy/",
    "https://balkangreenenergynews.com/country/greece/",
    "https://energynews.oedigital.com/greece",
    "https://www.reuters.com/world/europe/",
    "https://www.bloomberg.com/energy",
    "https://www.spglobal.com/commodityinsights/en",
    "https://www.ft.com/stream/6d801c42-fd6a-4e71-af32-d398e90e9b5d",  # FT Energy stream

    # ---- ΑΠΕ / Τεχνική ενημέρωση ----
    "https://www.pv-magazine.com/tag/greece/",
    "https://renewablesnow.com/topic/greece/",
    "https://energymag.gr/",
    "https://www.euractiv.com/section/energy/",
    "https://www.euronews.com/tag/energy",

    # ---- Οργανισμοί / Αρχές με ενεργειακά νέα ----
    "https://ypen.gov.gr/category/anakoinoseis/",
    "https://www.admie.gr/en/news",
    "https://www.raae.gr/anakoinoseis/"
]

# -----------------------------
# 2) KEYWORDS / NEGATIVE / SCORING
# -----------------------------
def normalize(text: str) -> str:
    """
    Μετατρέπει σε lowercase και αφαιρεί ελληνικούς τόνους/διακριτικά.
    Παράδειγμα: 'Ενέργεια' -> 'ενεργεια'
    """
    if not text:
        return ""
    t = text.lower()
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    return t

KEYWORDS = [
    # --- Γενική ενέργεια & αγορά (12) ---
    "ενεργεια", "ενεργειακη αγορα", "ενεργειακο κοστος", "κιλοβατωρα", "kwh", "mwh",
    "τιμολογια ρευματος", "προμηθευτες ρευματος", "χονδρεμπορικη", "χρηματιστηριο ενεργειας",
    "dam", "day ahead",

    # --- Ηλεκτρισμος & δικτυα (10) ---
    "ηλεκτρ", "δικτυο μεταφορας", "δικτυο διανομης", "αδμηε", "δεδδηε",
    "διασυνδεση", "interconnector", "ευσταθεια δικτυου", "smart grid", "smart meters",

    # --- Φωτοβολταικα / ηλιακη (12) ---
    "φωτοβολ", "φβ", "pv", "πανελ", "modules", "inverter", "μετατροπ", "string", "array",
    "net metering", "αυτοκαταναλωση", "zero feed in",

    # --- Αιολικα (8) ---
    "αιολικ", "wind", "ανεμογεννητρ", "turbine", "onshore wind", "offshore wind",
    "repowering", "wind farm",

    # --- Αποθηκευση ενεργειας (12) ---
    "μπαταρ", "battery", "bess", "soc", "state of charge", "round trip efficiency",
    "li ion", "lfp", "nmc", "flow battery", "αντλησιοταμιευση", "pumped storage",

    # --- Υδροηλεκτρικα (6) ---
    "υδροηλεκτρ", "ταμιευτηρ", "francis", "pelton", "υδροηλεκτρικη ισχυς", "υδατινοι ποροι",

    # --- Φυσικο αεριο & υδρογονανθρακες (14) ---
    "φυσικο αεριο", "gas", "lng", "fsru", "αγωγος", "pipeline",
    "eastmed", "tap", "igb", "upstream", "exploration", "κοιτασμα", "πετρελ", "διυλιστ",

    # --- Θερμανση / κτιρια / αποδοτικοτητα (8) ---
    "εξοικονομηση", "ενεργειακη αναβαθμιση", "heat pump", "αντλια θερμοτητας",
    "district heating", "τηλεθερμανση", "ενεργειακη κλαση", "θερμικη μονωση",

    # --- Ρυθμιση, πολιτικη & αγορα (10) ---
    "υπεν", "ypen", "ρααευ", "ρυθμιστικη αρχη", "δημοπρασιες απε", "auctions",
    "fit", "cfd", "ppa", "ets",

    # --- Υδρογονο & νεα τεχνολογια (8) ---
    "πρασινο υδρογονο", "green hydrogen", "electrolyzer", "ηλεκτρολυτ",
    "fuel cell", "κυψελη καυσιμου", "power to x", "αποανθρακοποιηση"
]

NEGATIVE = [
    # αποφυγή άσχετων θεμάτων
    "αθλη", "πολιτισ", "ψυχαγωγ", "μαγειρ", "συνταγ", "μοδα",
    "καιρος", "υγεια", "πανδημ", "κορονο", "τουρισ", "αυτοκινητ",
    "sports", "entertainment"
]

WEIGHTS = {
    "pv": 3,
    "bess": 3,
    "wind": 2,
    "gas": 2,
    "policy": 1
}

GROUPS = {
    "pv": ["φωτοβολ", "φβ", "pv", "πανελ", "inverter", "net metering", "αυτοκαταναλωση", "zero feed in"],
    "bess": ["μπαταρ", "battery", "bess", "soc", "state of charge", "round trip efficiency", "lfp", "nmc", "flow battery"],
    "wind": ["αιολικ", "wind", "ανεμογεννητρ", "turbine", "onshore wind", "offshore wind", "repowering", "wind farm"],
    "gas": ["φυσικο αεριο", "gas", "lng", "fsru", "αγωγος", "pipeline", "eastmed", "tap", "igb"],
    "policy": ["υπεν", "ypen", "ρααευ", "ρυθμιστικη αρχη", "ppa", "cfd", "fit", "auctions", "ets"]
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


# -----------------------------
# 3) SCRAPING
# -----------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36"
}

def absolutize(base: str, href: str) -> str:
    try:
        return urljoin(base, href)
    except Exception:
        return href

def is_probably_article_text(text: str) -> bool:
    """
    Φιλτράρει πολύ μικρά/άσχετα κείμενα (π.χ. 'Read more', 'Share', κ.λπ.)
    """
    t = normalize(text)
    if len(t) < 8:
        return False
    bad_fragments = ["read more", "περισσοτερα", "share", "mailto:", "javascript:"]
    if any(b in t for b in bad_fragments):
        return False
    return True

def scrape_site(url: str, timeout: int = 12) -> list[tuple[str, str]]:
    """
    Επιστρέφει λίστα (title, link) από ένα site.
    """
    results: list[tuple[str, str]] = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Πάρε όλα τα <a> με href και κάποιο κείμενο
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            href = a["href"]

            if not title or not href:
                continue
            if not is_probably_article_text(title):
                continue

            link = absolutize(url, href)
            # ακυρώνουμε αν είναι anchor στο ίδιο page
            if link.startswith("#"):
                continue

            results.append((title, link))

        # μικρό debouncing/dedup
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


# -----------------------------
# 4) ΦΙΛΤΡΟ & ΤΑΞΙΝΟΜΗΣΗ
# -----------------------------
def filter_energy_news(news_list: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    Δέχεται [(title, link)] και επιστρέφει μόνο ενεργειακά, χωρίς διπλότυπα,
    ταξινομημένα κατά score (desc).
    """
    seen_links = set()
    filtered: list[tuple[str, str]] = []

    for title, link in news_list:
        if not title or not link:
            continue
        if is_energy_title(title):
            ln = normalize(link)
            if ln in seen_links:
                continue
            seen_links.add(ln)
            filtered.append((title, link))

    filtered.sort(key=lambda x: score_title(x[0]), reverse=True)
    return filtered


# -----------------------------
# 5) REPORT & EMAIL
# -----------------------------
def build_report(news_dict: dict[str, list[tuple[str, str]]]) -> str:
    today = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [f"🔋 DAILY ENERGY NEWS REPORT — {today}", ""]
    for site, items in news_dict.items():
        lines.append(f"============================")
        lines.append(f"SITE: {site}")
        lines.append(f"============================")
        lines.append("")
        if not items:
            lines.append("❗ Δεν βρέθηκαν ενεργειακές ειδήσεις.")
            lines.append("")
        else:
            for title, link in items:
                score = score_title(title)
                lines.append(f"• ({score}) {title}")
                lines.append(f"  {link}")
                lines.append("")
    return "\n".join(lines)


def send_email(subject: str, body: str) -> None:
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")

    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

    if not EMAIL_USERNAME or not EMAIL_PASSWORD or not EMAIL_RECIPIENT:
        raise RuntimeError("Λείπουν τα env vars: EMAIL_USERNAME / EMAIL_PASSWORD / EMAIL_RECIPIENT")

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USERNAME
    msg["To"] = EMAIL_RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    server.sendmail(EMAIL_USERNAME, EMAIL_RECIPIENT, msg.as_string())
    server.quit()


# -----------------------------
# 6) MAIN
# -----------------------------
def main():
    all_results: dict[str, list[tuple[str, str]]] = {}
    for site in SITES:
        print(f"[INFO] Scraping {site} ...")
        raw = scrape_site(site)
        filt = filter_energy_news(raw)
        all_results[site] = filt
        time.sleep(0.5)  # ευγένεια προς sites

    report = build_report(all_results)
    print(report)

    try:
        send_email("Daily Energy News Report", report)
        print("📨 Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()

