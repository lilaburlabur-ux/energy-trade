#!/usr/bin/env python3
"""
fetch_tweets.py — @wallstengine (Wall St Engine) squawk, ENERGY TICKERS ONLY.

X's API is paywalled, so this reads the account's public RSS via keyless
Nitter mirrors (tried in order; all server-rendered, no key, no login).
Only posts cashtagging a ticker in OUR universe ($XOM, $OKLO, ...) are kept —
the account covers the whole market, we take the energy slice. Matches are
merged into tweets.json (deduped by status URL, newest 30 kept) so the feed
accumulates beyond the ~20 posts visible per fetch.

Fails soft: if every mirror is down, the existing tweets.json is left
untouched and the panel simply shows the last known posts.

Runs with the 5-min cloud quote refresh (refresh-data.yml).
"""

import json
import os
import re
import datetime as dt
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

import requests

HANDLE = "wallstengine"
# nitter.net retired its RSS (410) and privacyredirect 404s (2026-09-01);
# keep trying a spread — instances die and revive. xcancel needs an email
# whitelist for RSS readers; once granted it becomes the reliable one.
MIRRORS = ["https://nitter.net", "https://xcancel.com", "https://nitter.poast.org"]
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
CASHTAG = re.compile(r"\$([A-Za-z]{1,5})\b")


def universe_tickers():
    u = json.load(open("universe.json"))
    return {t["ticker"] for b in u["bubbles"] for t in b["tickers"]}


def fetch_items():
    """Try mirrors until one returns a REAL feed (>=1 item linking to a
    /status/ URL). Placeholder feeds (e.g. xcancel's whitelist notice) and
    partial responses are treated as mirror failures."""
    import xml.etree.ElementTree as ET
    for base in MIRRORS:
        try:
            r = requests.get(f"{base}/{HANDLE}/rss", timeout=20, headers=UA)
            if not (r.ok and "<rss" in r.text[:300]):
                continue
            root = ET.fromstring(r.text.lstrip())
            items = [it for it in root.findall(".//item")
                     if "/status/" in (it.findtext("link") or "")]
            if items:
                return items
        except Exception:
            continue
    return None


def main():
    items = fetch_items()
    if items is None:
        print("all mirrors down or placeholder feeds — keeping existing tweets.json")
        return

    uni = universe_tickers()

    fresh = []
    for it in items:
        title = re.sub(r"\s+", " ", (it.findtext("title") or "")).strip()
        link = it.findtext("link") or ""
        pub = it.findtext("pubDate") or ""
        tks = sorted({m.upper() for m in CASHTAG.findall(title)} & uni)
        if not tks:
            continue  # our tickers only — the whole point
        m = re.search(r"/status/(\d+)", link)
        if not m:
            continue
        url = f"https://x.com/{HANDLE}/status/{m.group(1)}"
        try:
            when = parsedate_to_datetime(pub).astimezone(dt.timezone.utc).isoformat(timespec="seconds")
        except Exception:
            when = None
        fresh.append({"text": title[:400], "time": when, "url": url, "tickers": tks})

    try:
        old = json.load(open("tweets.json")).get("items", [])
    except Exception:
        old = []
    seen = {t["url"] for t in fresh}
    merged = fresh + [t for t in old if t.get("url") not in seen]
    merged.sort(key=lambda t: t.get("time") or "", reverse=True)
    # prune fossils: an item older than 14 days no longer belongs in a live feed
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=14)).isoformat(timespec="seconds")
    merged = [t for t in merged if (t.get("time") or "") >= cutoff][:30]

    out = {"meta": {"handle": "@" + HANDLE,
                    "source": "X via keyless RSS mirror, filtered to the Energy Trade universe",
                    "as_of": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                    "count": len(merged)},
           "items": merged}
    json.dump(out, open("tweets.json", "w"), indent=1)
    print(f"tweets.json — {len(fresh)} fresh energy match(es) this fetch, {len(merged)} kept")


if __name__ == "__main__":
    main()
