"""
config.py — Central configuration for all Enerwave energy news scripts.
Edit ONLY this file to add/remove sites, keywords, or adjust weights.
"""

from typing import Dict, List, Tuple

# ══════════════════════════════════════════════════════════════
#  SITE LISTS  (split by purpose)
# ══════════════════════════════════════════════════════════════

# Used by: weekly_digest.py, market_alert.py
GR_SITES: List[str] = [
    "https://www.energypress.gr",
    "https://www.naftemporiki.gr",
    "https://www.ot.gr",
    "https://www.capital.gr",
    "https://www.powergame.gr",
    "https://www.euro2day.gr",
    "https://www.businessdaily.gr/",
    "https://www.worldenergynews.gr/",
    "https://energymag.gr/",
    "https://www.energyin.gr/",
    "https://ecotec.gr",
    "https://www.greenagenda.gr",
    "https://energynews.gr/",
    "https://ypodomes.com/",
    "https://www.financialreport.gr/",
    "https://www.energia.gr/",
    "https://www.enallaktiki.gr/",
    "https://www.haee.gr/news/",
    "https://helapco.gr/news/",
    "https://www.eletaen.gr/",
    "https://www.iene.eu/",
    "https://www.dei.gr/el/category/news/",
    "https://www.hedno.gr/gr/press",
    "https://www.metlen.com/gr/news-media",
    # Regulatory / Gov
    "https://ypen.gov.gr/category/anakoinoseis/",
    "https://www.admie.gr/en/news",
    "https://www.raaey.gr/energeia/anakoinoseis/",
    # NOTE: was "raae.gr" — outdated domain. The regulator was renamed
    # ΡΑΕ → ΡΑΑΕΥ in March 2023; raaey.gr is the current site (verified
    # 26/08/2026). Correcting this may surface regulator news that was
    # silently never coming through before.
    # EE-specific building/renovation portal — verified active with current
    # (Aug 2026) content, wasn't previously covered. Directly on-topic for
    # your core "ενεργειακή αναβάθμιση κτιρίων" focus.
    "https://news.b2green.gr/",
    # EE programs
    "https://exoikonomo2025.gov.gr/",
    "https://www.ot.gr/category/green/eksoikonomisi/",
    "https://www.skai.gr/tags/eksoikonomisi-energeias",
    "https://www.topics.gr/diafora/eksoikonomhsh-energeias/",
    # Balkan / regional (Greece-relevant)
    "https://greekreporter.com",
    "https://balkangreenenergynews.com",
]

# Used by: weekly_digest.py only (international context)
INTL_SITES: List[str] = [
    "https://www.euractiv.com/section/energy/",
    "https://www.eceee.org/all-news/news/",
    "https://www.aceee.org/news",
    "https://www.bpie.eu/news/",
    "https://www.solarthermalworld.org/news/",
    "https://www.iea-shc.org/news",
    "https://estif.org/news/",
    "https://www.euroheat.org/news/",
    "https://energynews.oedigital.com",
    "https://www.pv-magazine.com/tag/greece/",
    "https://energy.ec.europa.eu/news_en",
    "https://build-up.ec.europa.eu/en/news-and-events",
    "https://www.power-technology.com/category/energy-efficiency/",
    "https://www.facilitiesdive.com/",
]

# Used by: funding_monitor.py only
FUNDING_SITES: List[str] = [
    # EU Funding
    "https://cinea.ec.europa.eu/programmes/life_en",
    "https://cinea.ec.europa.eu/news-events/news_en",
    "https://eic.ec.europa.eu/eic-funding-opportunities_en",
    "https://energy.ec.europa.eu/funding-and-contracts/funding/innovation-fund_en",
    "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search",
    # ΕΣΠΑ / Greek national
    "https://www.espa.gr/el/pages/staticEspaNews.aspx",
    "https://www.antagonistikotita.gr/anakoinoseis/",
    "https://www.efepae.gr/front.aspx/news",
    "https://www.mindev.gov.gr/category/deltia-typou/",
    "https://exoikonomo2025.gov.gr/",
    # Energy-specific funding news
    "https://www.worldenergynews.gr/",
    "https://energymag.gr/",
    "https://ypen.gov.gr/category/anakoinoseis/",
]

# ══════════════════════════════════════════════════════════════
#  SCORING WEIGHTS  (Enerwave-specific)
# ══════════════════════════════════════════════════════════════
WEIGHTS: Dict[str, int] = {
    "competitors":      7,  # highest — you always want to see competitor moves
    "esco":             5,
    "solar_th":         5,
    "funding":          5,
    "efficiency":       5,
    "pv":               5,  # raised from 2 — explicit priority per user request
    "bess":             5,  # raised from 3 — explicit priority per user request
    "ppa":              5,  # new
    "demand_response":  5,  # new
    "chp":              4,
    "industrial":       4,
    "policy":           4,
    "heatpump":         3,
    "gas":              3,
    "wind":             2,
}

# ══════════════════════════════════════════════════════════════
#  KEYWORD GROUPS  (for scoring + topic assignment)
# ══════════════════════════════════════════════════════════════
GROUPS: Dict[str, List[str]] = {
    "esco": [
        "esco", "epc", "energy performance contract",
        "energy service", "εξοικονομω μεσω παροχων",
        "καθεστως επιβολης υποχρεωσης ενεργειακης αποδοσης",
    ],
    "solar_th": [
        "solar thermal", "ηλιοθερμικ", "ηλιακη θερμοτητα",
        "parabolic trough", "παραβολικα κατοπτρα", "cst",
        "concentrating solar", "solar heat", "process steam",
        "ατμος παραγωγης", "ηλιακο θερμικο", "sunbrewed",
    ],
    "funding": [
        "εσπα", "espa", "ταμειο ανακαμψης", "recovery fund", "rrf",
        "innovation fund", "if26", "life program", "life clean energy",
        "horizon europe", "ευρωπαϊκα ταμεια",
        "ανταγωνιστικοτητα 2021", "αλλαζω συστημα θερμανσης",
        "εξοικονομω 2025", "εσπα ενεργεια", "cinea",
        # NOTE: removed bare "χρηματοδοτηση", "επιδοτηση", "προγραμμα", "δραση" —
        # these generic words were matching non-energy articles (bonds, corporate
        # financing, unrelated EU programmes) any time they mentioned funding.
        # Kept only as compound phrases below, which require energy context.
        "χρηματοδοτηση φωτοβολταϊκων", "χρηματοδοτηση εργων ενεργειακης",
        "επιδοτηση αντλιας θερμοτητας", "επιδοτηση φωτοβολταϊκων",
        "προγραμμα εξοικονομω", "δραση εξοικονομω",
    ],
    "efficiency": [
        "εξοικονομηση", "ενεργειακη αναβαθμιση", "εξοικονομω",
        "energy efficiency", "efficient", "energy audit",
        "ενεργειακος ελεγχος", "θερμικη μονωση", "μονωση",
        "u-value", "building envelope", "hvac", "retrofit", "led",
        "bems", "ems", "bas", "building automation",
        "commissioning", "retrocommissioning", "iso 50001",
        "m&v", "ipmvp", "ενεργειακη κλαση",
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
    "policy": [
        "υπεν", "ypen", "ρααευ", "ppa", "cfd",
        "fit", "auctions", "ets", "cbam", "νομοσχεδιο",
        "κανονισμος", "οδηγια ευρωπαϊκη",
    ],
    "bess": [
        "μπαταρ", "battery", "bess",
        "αντλησιοταμιευση", "pumped storage", "lfp",
    ],
    "pv": [
        "φωτοβολ", "φβ", "pv", "net metering", "net billing",
        "αυτοκαταναλωση", "zero feed in", "virtual net billing",
        "φωτοβολταϊκα μπαλκονιου",
    ],
    "wind": [
        "αιολικ", "wind", "ανεμογεννητρ", "turbine",
        "offshore wind", "repowering",
    ],
    "gas": [
        "φυσικο αεριο", "gas", "lng", "fsru",
        "αγωγος", "pipeline", "eastmed",
    ],
    "ppa": [
        "ppa", "power purchase agreement", "corporate ppa", "cppa",
        "συμβαση αγορας ενεργειας", "διμερης συμβαση ενεργειας",
    ],
    "demand_response": [
        "demand response", "διαχειριση ζητησης", "αποκριση ζητησης",
        "load shifting", "load shedding", "flexibility market",
        "αγορα ευελιξιας", "aggregator", "συσσωρευτης φορτιου",
    ],
    # Sourced from Competition_Info.xlsx, column D ("COMPETITOR"), 25/08/2026.
    # NOTE: a few names are short/generic tokens (see caveats below the dict) —
    # review after the first couple of runs for false-positive hits.
    "competitors": [
        "dimkat", "enerca", "malamoulis", "malko", "mgd", "novenergy",
        "big solar", "pv maint", "redex", "sunel", "greenvolt",
        "αεναος", "βαρνας ετε", "βιεντερ", "εν.τε", "εναυσις",
        "ηλιατορας", "κρατωρ", "κχκ solar", "σπυροπουλος αε",
    ],
}
# Caveats on the competitors list (flag for review, not auto-fixed):
#  - "K&m" from the sheet was excluded: 2 letters + ampersand is too short/
#    ambiguous to match safely (near-certain false positives). If this is a
#    real competitor, give me a longer distinguishing phrase (e.g. full legal
#    name) and I'll add it.
#  - "NRG(Big Solar)" was mapped to "big solar" only — the bare "NRG" token
#    was dropped for the same short/ambiguous reason (matches unrelated
#    "NRG Energy" US-market headlines, etc.).
#  - "with GreenVolt" in the sheet reads like a partial comment, not a company
#    name — mapped to "greenvolt"; confirm this is correct.
#  - "ΕΝ.ΤΕ" contains a period that normalize() won't treat specially; "εν.τε"
#    as a substring is fairly safe but double-check after first run.

# Flat list of all keywords for fast pre-filter
ALL_KEYWORDS: List[str] = list({kw for kws in GROUPS.values() for kw in kws}) + [
    "ενεργεια", "ενεργειακη αγορα", "ενεργειακο κοστος",
    "kwh", "mwh", "τιμολογια ρευματος", "day ahead",
    "ηλεκτρ", "αδμηε", "δεδδηε", "διασυνδεση",
    "πετρελ", "διυλιστ", "κοιτασμα",
    "πρασινο υδρογονο", "green hydrogen", "αποανθρακοποιηση",
]

NEGATIVE_KEYWORDS: List[str] = [
    "αθλη", "πολιτισ", "ψυχαγωγ", "μαγειρ", "συνταγ", "μοδα",
    "καιρος", "υγεια", "πανδημ", "κορονο", "τουρισ",
    "sports", "entertainment", "ποδοσφαιρ", "κινηματογραφ",
    # added after 17/08–25/08/2026 digest review — generic finance/pop-culture
    # noise that was slipping in via broad "funding" keywords or blob titles
    "bitcoin", "κρυπτονομισμ", "crypto", "ταινια", "σκηνοθετ",
    "ομολογ", "netflix", "spotify", "nba", "cruise", "recipe",
]

# Topic display order (most Enerwave-relevant first).
# Reordered 25/08/2026 per explicit priority: competitors always first,
# then EE / PV / BESS / PPA / demand response, then the existing ESCO /
# solar-thermal / industrial core, then the rest.
TOPIC_PRIORITY: List[str] = [
    "competitors", "efficiency", "pv", "bess",
    "ppa", "demand_response",
    "esco", "solar_th", "industrial", "chp",
    "funding", "heatpump", "policy", "wind", "gas",
]

# Emoji + label per topic
TOPIC_META: Dict[str, Tuple[str, str]] = {
    "competitors":      ("🎯", "Ανταγωνιστές"),
    "efficiency":       ("🏢", "Εξοικονόμηση Ενέργειας & Κτίρια"),
    "esco":             ("📋", "ESCO / EPC / Χρηματοδοτικά Μοντέλα"),
    "solar_th":         ("☀️",  "Ηλιοθερμικά & Βιομηχανική Θερμότητα"),
    "chp":              ("⚡", "Συμπαραγωγή (CHP / Τριπαραγωγή)"),
    "industrial":       ("🏭", "Βιομηχανική Ενεργειακή Αποδοτικότητα"),
    "funding":          ("💶", "ΕΣΠΑ & EU Funding"),
    "heatpump":         ("🌡️",  "Αντλίες Θερμότητας"),
    "pv":               ("🌞", "Φωτοβολταϊκά"),
    "bess":             ("🔋", "Αποθήκευση Ενέργειας"),
    "ppa":              ("📄", "PPA"),
    "demand_response":  ("📉", "Demand Response"),
    "wind":             ("💨", "Αιολική Ενέργεια"),
    "gas":              ("⛽", "Φυσικό Αέριο & LNG"),
    "policy":           ("🏛️",  "Πολιτική & Ρύθμιση"),
    "other":            ("📰", "Γενικά Ενεργειακά"),
}

TOPIC_COLOUR: Dict[str, str] = {
    "competitors":      "#8e0038",
    "efficiency":       "#1a7a4a",
    "esco":             "#0d5c35",
    "solar_th":         "#c67000",
    "chp":              "#5a3e9e",
    "industrial":       "#2d6a9f",
    "funding":          "#c0392b",
    "heatpump":         "#b84a00",
    "pv":               "#e07b00",
    "bess":             "#1a5276",
    "ppa":              "#4a4a8a",
    "demand_response":  "#8a5a00",
    "wind":             "#117a65",
    "gas":              "#6c3483",
    "policy":           "#1f618d",
    "other":            "#555555",
    "top":              "#0f3460",
}

# ══════════════════════════════════════════════════════════════
#  FUNDING CALL KEYWORDS  (used only by funding_monitor.py)
# ══════════════════════════════════════════════════════════════
# Must appear in title/snippet to be considered a funding call
FUNDING_CALL_KEYWORDS: List[str] = [
    # English
    "call for proposals", "open call", "funding opportunity",
    "grant", "application deadline", "submit application",
    "innovation fund", "life programme", "life clean energy",
    "horizon europe", "eic accelerator", "cinea",
    "tender", "procurement",
    # Greek
    "προσκληση υποβολης", "ανοιχτη προσκληση",
    "εξοικονομω", "αλλαζω", "χρηματοδοτηση",
    "επιδοτηση", "επιχορηγηση", "δραση",
    "ταμειο ανακαμψης", "εσπα", "προγραμμα",
    "υποβολη αιτησεων", "καταληκτικη ημερομηνια",
    "προϋπολογισμος", "δικαιουχοι",
]

# Topics Enerwave cares about in funding calls
FUNDING_TOPIC_KEYWORDS: List[str] = [
    # Core Enerwave services
    "solar thermal", "ηλιοθερμικ", "process heat", "industrial heat",
    "esco", "epc", "energy performance",
    "cogeneration", "chp", "συμπαραγωγη",
    "energy efficiency", "εξοικονομηση", "ενεργειακη αναβαθμιση",
    "heat pump", "αντλια θερμοτητας",
    "district heating", "τηλεθερμανση",
    "building renovation", "ανακαινιση",
    "smart building", "bems",
    "vfd", "heat recovery", "ανακτηση θερμοτητας",
    # General energy that may be relevant
    "renewable", "ανανεωσιμ", "decarbonisation", "αποανθρακοποιηση",
    "green hydrogen", "πρασινο υδρογονο",
]
