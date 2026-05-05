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
    "https://www.raae.gr/anakoinoseis/",
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
    "esco":       5,
    "solar_th":   5,
    "funding":    5,
    "efficiency": 5,
    "chp":        4,
    "industrial": 4,
    "policy":     4,
    "heatpump":   3,
    "bess":       3,
    "gas":        3,
    "pv":         2,
    "wind":       2,
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
        "χρηματοδοτηση", "επιδοτηση", "προγραμμα", "δραση",
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
}

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
]

# Topic display order (most Enerwave-relevant first)
TOPIC_PRIORITY: List[str] = [
    "esco", "solar_th", "chp", "industrial",
    "efficiency", "funding", "heatpump",
    "pv", "bess", "wind", "gas", "policy",
]

# Emoji + label per topic
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

TOPIC_COLOUR: Dict[str, str] = {
    "efficiency": "#1a7a4a",
    "esco":       "#0d5c35",
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
    "top":        "#0f3460",
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
