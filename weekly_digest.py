#!/usr/bin/env python3
"""
weekly_digest.py — Enerwave Weekly Energy Digest
──────────────────────────────────────────────────
Runs every Monday at 08:00 UTC (10:00 EET / 11:00 EEST).
Covers GR + international sites.
Score ≥ 3. Lookback: 7 days.
Organised by topic. Always sends (full week summary).
"""

import os
import sys
import time
import datetime
from typing import Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from config import (
    GR_SITES, INTL_SITES,
    TOPIC_PRIORITY, TOPIC_META, TOPIC_COLOUR,
)
from common.http_utils import scrape_site, fetch_article_dt, short_site, ATHENS_TZ
from common.text_utils import normalize, is_energy_title, score_title, assign_topic, Article
from common.email_utils import send_email

MIN_SCORE     = 3
MAX_AGE_DAYS  = 7
MAX_DT_FETCH  = 35
TOP_N         = 10

# International sites: apply a stricter filter — only topics Enerwave cares about
INTL_REQUIRED_TOPICS = {
    "esco", "solar_th", "chp", "industrial",
    "efficiency", "funding", "heatpump",
}


# ══════════════════════════════════════════════════════════════
#  PIPELINE
# ══════════════════════════════════════════════════════════════
def collect() -> List[Article]:
    raw: List[Tuple[str, str, str, bool]] = []  # title, link, site, is_intl

    all_sites = [(s, False) for s in GR_SITES] + [(s, True) for s in INTL_SITES]
    for site, is_intl in all_sites:
        print(f"[INFO] Scraping {site} …", file=sys.stderr)
        for title, link in scrape_site(site):
            raw.append((title, link, site, is_intl))
        time.sleep(0.4)

    seen_links:  Set[str] = set()
    seen_titles: Set[str] = set()
    articles: List[Article] = []

    for title, link, site, is_intl in raw:
        if not is_energy_title(title):
            continue
        sc    = score_title(title)
        topic = assign_topic(title)

        if sc < MIN_SCORE:
            continue
        # International: only Enerwave-core topics
        if is_intl and topic not in INTL_REQUIRED_TOPICS:
            continue

        nl = normalize(link)[:140]
        nt = normalize(title)[:100]
        if nl in seen_links or nt in seen_titles:
            continue
        seen_links.add(nl)
        seen_titles.add(nt)
        articles.append(Article(
            title=title, link=link, site=site,
            score=sc, topic=topic,
        ))

    # Enrich with dates
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
    lines = [f"🔋 WEEKLY ENERGY DIGEST — {today}", "=" * 56, ""]

    lines += [f"⭐  TOP {TOP_N} OF THE WEEK", "─" * 40, ""]
    for a in articles[:TOP_N]:
        lines += [
            f"• [{_fmt(a.published_dt)}] (s:{a.score}) {a.title}",
            f"  {a.link}",
            "",
        ]

    buckets: Dict[str, List[Article]] = {}
    for a in articles:
        buckets.setdefault(a.topic, []).append(a)

    for key in TOPIC_PRIORITY + ["other"]:
        items = buckets.get(key)
        if not items:
            continue
        emoji, label = TOPIC_META.get(key, ("📰", key))
        lines += [f"\n{emoji}  {label.upper()}", "─" * 40, ""]
        for a in items:
            lines += [
                f"• [{_fmt(a.published_dt)}] (s:{a.score}) {a.title}",
                f"  {a.link}  [{short_site(a.site)}]",
                "",
            ]
    return "\n".join(lines)


def build_html(articles: List[Article]) -> str:
    today = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")

    style = """
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
       color: #1a1a2e; background: #f4f5f7; margin: 0; padding: 16px; }
.wrap { max-width: 860px; margin: 0 auto; }
.banner { background: #0f3460; color: #fff; border-radius: 8px 8px 0 0;
          padding: 16px 20px; }
.banner h1 { margin: 0; font-size: 22px; }
.banner .sub { font-size: 12px; opacity: .75; margin-top: 4px; }
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

    def _sec(key: str, items: List[Article], colour: str,
             emoji: str, label: str) -> str:
        rows = "".join(
            f"<div class='item'>"
            f"<span class='sc'>{a.score}</span>"
            f"<div class='ib'>"
            f"<a href='{a.link}' target='_blank' rel='noopener noreferrer'>"
            f"{a.title}</a>"
            f"<div class='meta'>"
            f"{_fmt(a.published_dt)} · {short_site(a.site)}"
            f"</div></div></div>"
            for a in items
        )
        return (
            f"<div class='sec'>"
            f"<div class='shdr' style='background:{colour}'>"
            f"{emoji} {label}</div>{rows}</div>"
        )

    # Top N section
    parts = [
        "<div class='wrap'>",
        "<div class='banner'>"
        "<h1>🔋 Weekly Energy Digest — Enerwave</h1>"
        f"<div class='sub'>{today} · {len(articles)} articles</div>"
        "</div>",
        _sec("top", articles[:TOP_N], TOPIC_COLOUR["top"],
             "⭐", f"Top {TOP_N} of the Week"),
    ]

    for key in TOPIC_PRIORITY + ["other"]:
        items = buckets.get(key)
        if not items:
            continue
        colour = TOPIC_COLOUR.get(key, "#555")
        emoji, label = TOPIC_META.get(key, ("📰", key))
        parts.append(_sec(key, items, colour, emoji, label))

    parts.append("</div>")
    return (
        "<!doctype html><html>"
        "<head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width'>"
        f"<style>{style}</style></head>"
        f"<body>{''.join(parts)}</body></html>"
    )


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
def main() -> None:
    articles = collect()
    total    = len(articles)
    print(f"[INFO] {total} articles for weekly digest.", file=sys.stderr)

    SEND_EMPTY = os.getenv("SEND_EMPTY", "false").lower() == "true"
    if not articles and not SEND_EMPTY:
        print("ℹ️  No articles found — no email sent.")
        return

    today   = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y")
    subject = f"🔋 Weekly Digest {today} — {total} articles · Enerwave"

    try:
        send_email(subject, build_text(articles), build_html(articles))
        print(f"📨  Weekly digest sent ({total} articles).")
    except Exception as exc:
        print(f"❌  Email failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
