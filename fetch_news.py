#!/usr/bin/env python3
"""
fetch_news.py — pulls headlines for the FULL coverage scope and writes news.json:
every ticker in universe.json (sector-tagged) plus the ETF symbols.

WHY THE TAGGING IS NOT "whatever feed it came from":
Yahoo's per-ticker feeds are noisy. NVDA's feed, for example, carries syndicated
Motley Fool / 24-7 Wall St / macro stories ("Is Coca-Cola a Buy?", "Social
Security move...", "Bitcoin ETF outflows...") that have nothing to do with NVDA.
The old code tagged a story with whatever ticker's feed it appeared in, so those
ended up labelled NVDA · Chips & Compute.

So we do NOT trust the source feed. We collect every story, then RE-TAG each one
purely by which of our companies its TITLE actually names — either the ticker
symbol ($NVDA, (NVDA), (NYSE:TSM)) or the company name (Nvidia, Micron, ...).
A story that names none of our companies is dropped from the AI feed entirely.
This also fixes mis-fed stories (e.g. "SpaceX Stock Began Trading", which Yahoo
served under GOOGL/META, now tags SPCX) and catches multi-company headlines
("Amazon vs. Microsoft" -> both).

Run:    .venv/bin/python fetch_news.py
Output: news.json  {as_of_utc, count, items:[{title,url,publisher,published,tickers,sectors}]}
"""

import os
import sys
import json
import time
import re
import datetime as dt
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from tickers import ETF_HOLDINGS

MAX_PER_SYMBOL = 6
MAX_ITEMS = 80

# =====================================================================
#  Company-name matching — decides if a headline is really about a ticker
# =====================================================================
# Trailing words we strip off a company name to get its everyday "core"
# name, e.g. "Honeywell International Inc" -> "Honeywell",
# "Micron Technology Inc" -> "Micron", "Lattice Semiconductor Corp" -> "Lattice".
SUFFIX = {
    "inc", "inc.", "incorporated", "corp", "corp.", "corporation", "co", "co.",
    "company", "ltd", "ltd.", "limited", "plc", "llc", "nv", "n.v.", "sa",
    "s.a.", "se", "ag", "adr", "holdings", "holding", "group", "technologies",
    "technology", "systems", "networks", "platforms", "software", "manufacturing",
    "semiconductor", "semiconductors", "solutions", "international", "trust",
    "pharmaceuticals", "services", "automation", "enterprise",
}
# ...but never let the core collapse down to one of these generic / geographic
# words (e.g. don't reduce "Taiwan Semiconductor Manufacturing" to "Taiwan").
GENERIC = {
    "taiwan", "american", "global", "general", "international", "advanced",
    "applied", "super", "digital", "trade", "check", "united", "national",
    "first", "data", "cloud", "micro", "power", "energy", "research",
    "business", "services",
}
# Extra hand-picked aliases the core-name rule can't derive (brands, short forms).
EXTRA = {
    "ARM":   ["Arm Holdings"],
    "GOOGL": ["Google", "Alphabet", "Waymo"],
    "AMZN":  ["Amazon", "AWS"],
    "META":  ["Meta", "Facebook"],
    "TSM":   ["TSMC", "Taiwan Semiconductor"],
    "AI":    ["C3.ai", "C3 AI"],
    "NXPI":  ["NXP"],
    "AMD":   ["AMD"],
    "SPCX":  ["SpaceX", "Space Exploration"],
    "MU":    ["Micron"],
}
# Replace the auto aliases entirely for names that collide with common English.
# "Snap" alone matches "stocks snap back", so only its distinctive brand counts.
NAME_OVERRIDE = {
    "SNAP": ["Snapchat"],
}
# Symbols that are also everyday words: never match them bare or in "(AI)" form
# — "(AI)" almost always means "artificial intelligence", not the C3.ai ticker.
# These tickers are matched only via $CASHTAG or their company name.
COMMON_SYM = {"AI", "ARM", "NOW", "PATH", "NET", "APP", "ALL", "ANY", "ARE", "ONE"}


def core_name(company):
    """Strip corporate suffixes to get the everyday company name."""
    toks = company.replace(",", " ").split()
    while len(toks) > 1:
        last = toks[-1].lower().strip(".")
        if last in SUFFIX:
            remain = toks[:-1]
            # don't collapse onto a single generic/geographic word
            if len(remain) == 1 and remain[0].lower() in GENERIC:
                break
            toks = remain
        else:
            break
    return " ".join(toks)


def aliases_for(sym, company):
    """The set of name strings that count as 'this headline is about <sym>'."""
    if sym in NAME_OVERRIDE:
        return set(NAME_OVERRIDE[sym])
    al = set()
    c = core_name(company.get(sym, ""))
    if len(c) >= 4:                 # too-short cores (e.g. "KLA") are ambiguous
        al.add(c)
    al.update(EXTRA.get(sym, []))
    return al


def build_matcher(company):
    """Compile, once, the regex patterns that detect each ticker in a title."""
    matcher = {}
    for sym in company:
        pats = []
        s = re.escape(sym)
        # $TICKER cashtag — always an unambiguous ticker reference
        pats.append(re.compile(r"(?<![A-Za-z0-9])\$" + s + r"\b"))
        # (TICKER) or (NYSE:TICKER) — skip common-word tickers like "(AI)"
        if sym not in COMMON_SYM:
            pats.append(re.compile(r"[(:]\s*" + s + r"\b"))
        # bare UPPERCASE symbol — case-sensitive so "on"/"now"/"arm" don't match
        if len(sym) >= 3 and sym not in COMMON_SYM:
            pats.append(re.compile(r"(?<![A-Za-z0-9.$])" + s + r"(?![A-Za-z0-9])"))
        # company-name aliases — case-insensitive, whole-word
        for a in aliases_for(sym, company):
            pats.append(re.compile(r"(?<![A-Za-z0-9])" + re.escape(a) + r"(?![A-Za-z0-9])", re.I))
        matcher[sym] = pats
    return matcher


def title_tickers(text, matcher):
    """Tickers whose symbol or company name actually appears in the title."""
    hits = [sym for sym, pats in matcher.items() if any(p.search(text) for p in pats)]
    return sorted(set(hits))


GNEWS = "https://news.google.com/rss/search"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def headlines_for(symbol, company):
    """Google News RSS for the company's everyday name. Yahoo's news endpoints
    answer 429 or an empty list to our traffic (2026-10), so yfinance returns
    nothing; Google News RSS is keyless and carries the publisher and date."""
    q = urllib.parse.quote_plus(f'"{core_name(company) or symbol}" stock')
    r = requests.get(f"{GNEWS}?q={q}&hl=en-US&gl=US&ceid=US:en", headers=UA, timeout=20)
    if r.status_code == 429:
        time.sleep(20)
        r = requests.get(f"{GNEWS}?q={q}&hl=en-US&gl=US&ceid=US:en", headers=UA, timeout=20)
    r.raise_for_status()
    out = []
    for it in ET.fromstring(r.content).findall(".//item")[:MAX_PER_SYMBOL]:
        src = it.find("source")
        publisher = (src.text or "").strip() if src is not None else ""
        title = (it.findtext("title") or "").strip()
        if publisher and title.endswith(" - " + publisher):
            title = title[: -len(" - " + publisher)].strip()   # Google appends the outlet
        link = (it.findtext("link") or "").strip()
        if not title:
            continue
        try:
            published = parsedate_to_datetime(it.findtext("pubDate") or "") \
                .astimezone(dt.timezone.utc).isoformat(timespec="seconds")
        except Exception:
            published = ""
        out.append({"id": title.lower(), "title": title, "url": link,
                    "publisher": publisher, "published": published})
    return out


def main():
    uni = json.load(open(os.path.join(HERE, "universe.json")))
    company = {}                     # ticker -> company name (for matching)
    sector = {}                      # ticker -> bubble/sector id (for tags)
    for b in uni["bubbles"]:
        for t in b["tickers"]:
            company[t["ticker"]] = t.get("company", "")
            sector[t["ticker"]] = b["id"]
    matcher = build_matcher(company)

    # Feeds we PULL stories from (the source feed no longer decides the tags).
    scope = list(company) + list(ETF_HOLDINGS)
    seen = set()
    scope = [s for s in scope if not (s in seen or seen.add(s))]

    merged = {}                     # id -> story (title/url/publisher/published)
    failed = 0
    print(f"Pulling news for {len(scope)} symbols...")
    for sym in scope:
        try:
            for h in headlines_for(sym, company.get(sym, "")):
                merged.setdefault(h["id"], {k: h[k] for k in ("title", "url", "publisher", "published")})
        except Exception as e:
            failed += 1
            print(f"  {sym}: query failed — {type(e).__name__}: {e}")
        time.sleep(1.0)
    if not merged:
        # Never replace a populated feed with an empty one: fail loudly instead.
        print(f"ERROR: 0 stories collected ({failed}/{len(scope)} queries failed). "
              "news.json left unchanged.")
        sys.exit(1)

    # Re-tag every story by what its title actually names; drop the off-topic ones.
    items = []
    for m in merged.values():
        tickers = title_tickers(m["title"], matcher)
        if not tickers:             # names none of our companies -> not AI news
            continue
        sectors = sorted({sector[t] for t in tickers})
        items.append({**m, "tickers": tickers, "sectors": sectors})

    dropped = len(merged) - len(items)
    items = sorted(items, key=lambda x: x["published"] or "", reverse=True)[:MAX_ITEMS]
    payload = {
        "as_of_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
    }
    with open(os.path.join(HERE, "news.json"), "w") as f:
        json.dump(payload, f, indent=1)
    print(f"Wrote news.json — {len(items)} tagged stories "
          f"({len(merged)} collected, {dropped} dropped as off-topic).")


if __name__ == "__main__":
    main()
