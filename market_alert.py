#!/usr/bin/env python3
"""
market_alert.py — Enerwave Greek Market Alert
───────────────────────────────────────────────
Runs Tuesday + Friday mornings.
Scrapes ONLY Greek sites.
Focuses on policy, regulations, Εξοικονομώ, pricing — things that
affect active projects or sales conversations.
Only sends email if high-scoring articles found (score ≥ MIN_SCORE).
No state persistence needed — always looks at the last 4 days.
"""

import os
import sys
import time
import datetime
from typing import Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from config import GR_SITES, TOPIC_PRIORITY, TOPIC_META, TOPIC_COLOUR
from common.http_utils import scrape_site, fetch_article_dt, short_site, ATHENS_TZ
from common.text_utils import normalize, is_energy_title, score_title, assign_topic, Article
from common.email_utils import send_email

# ── Only surface high-signal articles ────────────────────────────────
MIN_SCORE     = 4       # only articles scoring ≥ this
MAX_AGE_DAYS  = 4       # look back 4 days (covers Tue→Fri gap)
MAX_DT_FETCH  = 25      # max extra HTTP GETs for date enrichment
TOP_N         = 8       # items in top section

# ── Only these topics are relevant for a market alert ────────────────
ALERT_TOPICS  = {
    "esco", "solar_th", "chp", "industrial",
    "efficiency", "funding", "heatpump", "policy",
}


# ══════════════════════════════════════════════════════════════
#  PIPELINE
# ══════════════════════════════════════════════════════════════
def collect(sites: List[str]) -> List[Article]:
    raw: List[Tuple[str, str, str]] = []
    for site in sites:
        print(f"[INFO] Scanning {site} …", file=sys.stderr)
        for title, link in scrape_site(site):
            raw.append((title, link, site))
        time.sleep(0.4)

    seen_links: Set[str] = set()
    seen_titles: Set[str] = set()
    articles: List[Article] = []

    for title, link, site in raw:
        if not is_energy_title(title):
            continue
        nl = normalize(link)[:140]
        nt = normalize(title)[:100]
        if nl in seen_links or nt in seen_titles:
            continue
        sc = score_title(title)
        if sc < MIN_SCORE:
            continue
        topic = assign_topic(title)
        if topic not in ALERT_TOPICS:
            continue
        seen_links.add(nl)
        seen_titles.add(nt)
        articles.append(Article(
            title=title, link=link, site=site,
            score=sc, topic=topic,
        ))

    # Date enrichment
    articles.sort(key=lambda a: a.score, reverse=True)
    for i, art in enumerate(articles):
        if i >= MAX_DT_FETCH:
            break
        art.published_dt = fetch_article_dt(art.link)

    # Age filter
    now    = datetime.datetime.now(tz=ATHENS_TZ)
    cutoff = now - datetime.timedelta(days=MAX_AGE_DAYS)
    articles = [
        a for a in articles
        if a.published_dt is None or a.published_dt >= cutoff
    ]

    articles.sort(
        key=lambda a: (
            a.published_dt or datetime.datetime.min.replace(
                tzinfo=ZoneInfo("UTC")
            ),
            a.score,
        ),
        reverse=True,
    )
    return articles


# ══════════════════════════════════════════════════════════════
#  REPORT BUILDERS
# ══════════════════════════════════════════════════════════════
def _fmt(dt: Optional[datetime.datetime]) -> str:
    return dt.strftime("%d/%m %H:%M") if dt else "—"


def build_text(articles: List[Article]) -> str:
    today = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")
    lines = [
        f"🇬🇷 GREEK MARKET ALERT — {today}",
        f"Topics: EE | ESCO | Policy | Funding | Solar Thermal | CHP",
        "=" * 56, "",
    ]
    buckets: Dict[str, List[Article]] = {}
    for a in articles:
        buckets.setdefault(a.topic, []).append(a)

    for key in TOPIC_PRIORITY:
        items = buckets.get(key)
        if not items:
            continue
        emoji, label = TOPIC_META.get(key, ("📰", key))
        lines += [f"{emoji}  {label.upper()}", "─" * 40, ""]
        for a in items:
            lines += [
                f"• [{_fmt(a.published_dt)}] (s:{a.score}) {a.title}",
                f"  {a.link}",
                "",
            ]
    return "\n".join(lines)


def build_html(articles: List[Article]) -> str:
    today = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")

    style = """
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
       color: #1a1a2e; background: #f4f5f7; margin: 0; padding: 16px; }
.wrap { max-width: 800px; margin: 0 auto; }
.banner { background: #0f3460; color: #fff; border-radius: 8px 8px 0 0;
          padding: 14px 18px; }
.banner h1 { margin: 0; font-size: 20px; }
.banner .sub { font-size: 12px; opacity: .75; margin-top: 3px; }
.sec { background: #fff; border-radius: 8px; margin-top: 12px;
       box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden; }
.shdr { padding: 9px 14px; font-weight: 700; font-size: 13px; color: #fff; }
.item { padding: 8px 14px; border-bottom: 1px solid #f0f0f0;
        display: flex; gap: 8px; }
.item:last-child { border-bottom: none; }
.sc { min-width: 26px; text-align: center; background: #eef; color: #336;
      border: 1px solid #ccd; border-radius: 4px;
      padding: 1px 4px; font-size: 11px; flex-shrink: 0; }
.ib { flex: 1; }
a { color: #0366d6; text-decoration: none; font-size: 13px; line-height: 1.4; }
a:hover { text-decoration: underline; }
.meta { color: #999; font-size: 11px; margin-top: 3px; }
    """

    buckets: Dict[str, List[Article]] = {}
    for a in articles:
        buckets.setdefault(a.topic, []).append(a)

    def _sec(key: str) -> str:
        items = buckets.get(key)
        if not items:
            return ""
        colour = TOPIC_COLOUR.get(key, "#555")
        emoji, label = TOPIC_META.get(key, ("📰", key))
        rows = "".join(
            f"<div class='item'>"
            f"<span class='sc'>{a.score}</span>"
            f"<div class='ib'>"
            f"<a href='{a.link}' target='_blank' rel='noopener noreferrer'>"
            f"{a.title}</a>"
            f"<div class='meta'>{_fmt(a.published_dt)} · {short_site(a.site)}</div>"
            f"</div></div>"
            for a in items
        )
        return (
            f"<div class='sec'>"
            f"<div class='shdr' style='background:{colour}'>"
            f"{emoji} {label}</div>{rows}</div>"
        )

    sections = "".join(_sec(k) for k in TOPIC_PRIORITY)

    return (
        "<!doctype html><html>"
        "<head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width'>"
        f"<style>{style}</style></head>"
        "<body><div class='wrap'>"
        "<div class='banner'>"
        f"<h1>🇬🇷 Greek Market Alert</h1>"
        f"<div class='sub'>{today} · {len(articles)} articles · Enerwave</div>"
        "</div>"
        f"{sections}"
        "</div></body></html>"
    )


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
def main() -> None:
    articles = collect(GR_SITES)
    total    = len(articles)
    print(f"[INFO] {total} relevant GR articles found.", file=sys.stderr)

    if not articles:
        print("ℹ️  Nothing above threshold — no email sent.")
        return

    today   = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y")
    subject = f"🇬🇷 GR Market Alert {today} — {total} articles · Enerwave"

    try:
        send_email(subject, build_text(articles), build_html(articles))
        print(f"📨  Market alert sent ({total} articles).")
    except Exception as exc:
        print(f"❌  Email failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
