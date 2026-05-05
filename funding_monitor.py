#!/usr/bin/env python3
"""
funding_monitor.py — Enerwave Funding Call Monitor
────────────────────────────────────────────────────
Runs daily. Scrapes EU and Greek funding portals.
Sends an email alert ONLY when new relevant calls are found.
Persists seen URLs in state/seen_funding.json so no duplicates.

GitHub Actions workflow commits state/seen_funding.json back to repo
after each run — this is the persistence mechanism.
"""

import json
import os
import sys
import time
import datetime
from typing import Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from config import (
    FUNDING_SITES, FUNDING_CALL_KEYWORDS,
    FUNDING_TOPIC_KEYWORDS, TOPIC_COLOUR,
)
from common.http_utils import scrape_site, fetch_article_dt, short_site, ATHENS_TZ
from common.text_utils import normalize
from common.email_utils import send_email

# ── State file path (committed back to repo by the workflow) ──────────
STATE_FILE = "state/seen_funding.json"

# ── Scoring threshold — only calls scoring ≥ this are emailed ─────────
MIN_RELEVANCE = 2


# ══════════════════════════════════════════════════════════════
#  STATE  (seen URLs persisted in repo)
# ══════════════════════════════════════════════════════════════
def load_seen() -> Set[str]:
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("seen_urls", []))
    except Exception:
        return set()


def save_seen(seen: Set[str]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "seen_urls": sorted(seen),
                "last_updated": datetime.datetime.now(
                    tz=ATHENS_TZ
                ).isoformat(),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


# ══════════════════════════════════════════════════════════════
#  RELEVANCE SCORING
# ══════════════════════════════════════════════════════════════
def is_funding_call(title: str) -> bool:
    """True if the title looks like a funding call / program announcement."""
    t = normalize(title)
    return any(k in t for k in FUNDING_CALL_KEYWORDS)


def relevance_score(title: str) -> int:
    """0–N: how relevant this call is to Enerwave topics."""
    t = normalize(title)
    return sum(1 for k in FUNDING_TOPIC_KEYWORDS if k in t)


# ══════════════════════════════════════════════════════════════
#  PIPELINE
# ══════════════════════════════════════════════════════════════
def collect_new_calls(seen: Set[str]) -> List[Dict]:
    """Scrape all funding sites, return only new relevant calls."""
    new_calls: List[Dict] = []
    raw: List[Tuple[str, str, str]] = []

    for site in FUNDING_SITES:
        print(f"[INFO] Scanning {site} …", file=sys.stderr)
        for title, link in scrape_site(site):
            raw.append((title, link, site))
        time.sleep(0.4)

    seen_links: Set[str] = set(seen)
    for title, link, site in raw:
        norm_link = normalize(link)[:150]
        if norm_link in seen_links:
            continue
        if not is_funding_call(title):
            continue
        score = relevance_score(title)
        if score < MIN_RELEVANCE:
            continue
        seen_links.add(norm_link)
        published_dt = fetch_article_dt(link)
        new_calls.append({
            "title":        title,
            "link":         link,
            "site":         site,
            "score":        score,
            "published_dt": published_dt,
        })

    # Sort: most relevant first
    new_calls.sort(key=lambda x: x["score"], reverse=True)
    return new_calls, seen_links


# ══════════════════════════════════════════════════════════════
#  REPORT BUILDERS
# ══════════════════════════════════════════════════════════════
def _fmt(dt: Optional[datetime.datetime]) -> str:
    return dt.strftime("%d/%m/%Y") if dt else "—"


def build_text(calls: List[Dict]) -> str:
    today = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")
    lines = [
        f"💶 FUNDING ALERT — {len(calls)} new call(s) — {today}",
        "=" * 56, "",
    ]
    for c in calls:
        lines += [
            f"[relevance: {c['score']}] {c['title']}",
            f"  Date: {_fmt(c['published_dt'])}",
            f"  Source: {short_site(c['site'])}",
            f"  Link: {c['link']}",
            "",
        ]
    return "\n".join(lines)


def build_html(calls: List[Dict]) -> str:
    today = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y %H:%M")
    colour = TOPIC_COLOUR.get("funding", "#c0392b")

    style = """
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
       color: #1a1a2e; background: #f4f5f7; margin: 0; padding: 16px; }
.wrap { max-width: 760px; margin: 0 auto; }
.banner { background: #c0392b; color: #fff; border-radius: 8px 8px 0 0;
          padding: 14px 18px; }
.banner h1 { margin: 0; font-size: 20px; }
.banner .ts { font-size: 12px; opacity: .8; margin-top: 4px; }
.body { background: #fff; border-radius: 0 0 8px 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,.1); overflow: hidden; }
.call { padding: 12px 18px; border-bottom: 1px solid #f0f0f0; }
.call:last-child { border-bottom: none; }
.badge { display: inline-block; background: #fdecea; color: #c0392b;
         border: 1px solid #f5b7b1; border-radius: 4px;
         padding: 1px 6px; font-size: 11px; margin-right: 6px; }
a { color: #0366d6; font-size: 14px; font-weight: 600;
    text-decoration: none; line-height: 1.4; }
a:hover { text-decoration: underline; }
.meta { color: #999; font-size: 11px; margin-top: 4px; }
    """

    rows = "".join(
        f"<div class='call'>"
        f"<span class='badge'>relevance {c['score']}</span>"
        f"<a href='{c['link']}' target='_blank' rel='noopener noreferrer'>"
        f"{c['title']}</a>"
        f"<div class='meta'>"
        f"{_fmt(c['published_dt'])} · {short_site(c['site'])}"
        f"</div></div>"
        for c in calls
    )

    return (
        "<!doctype html><html>"
        "<head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width'>"
        f"<style>{style}</style></head>"
        "<body><div class='wrap'>"
        f"<div class='banner'>"
        f"<h1>💶 Funding Alert — {len(calls)} new call(s)</h1>"
        f"<div class='ts'>{today} · Enerwave</div>"
        f"</div>"
        f"<div class='body'>{rows}</div>"
        "</div></body></html>"
    )


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
def main() -> None:
    seen = load_seen()
    new_calls, updated_seen = collect_new_calls(seen)

    # Always persist state (even if no new calls, seen set grows)
    save_seen(updated_seen)
    print(
        f"[INFO] {len(new_calls)} new funding call(s) found.",
        file=sys.stderr,
    )

    if not new_calls:
        print("ℹ️  No new funding calls — no email sent.")
        return

    today   = datetime.datetime.now(tz=ATHENS_TZ).strftime("%d/%m/%Y")
    subject = f"💶 Funding Alert {today} — {len(new_calls)} new call(s) · Enerwave"

    try:
        send_email(subject, build_text(new_calls), build_html(new_calls))
        print(f"📨  Funding alert sent ({len(new_calls)} calls).")
    except Exception as exc:
        print(f"❌  Email failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
