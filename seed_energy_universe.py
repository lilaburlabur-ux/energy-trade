#!/usr/bin/env python3
"""
seed_energy_universe.py — ONE-TIME builder of the Energy Trade universe.json.

Creates the 9-bucket energy universe with real fetched values (prices, caps,
P/E, 30-day sparklines) so update_quotes.py / update_universe.py can maintain
it from day one. Bucket membership lives HERE; re-run only to change it.

Listing notes (verified 2026-08): PXD gone (ExxonMobil takeover), HES gone
(Chevron), MRO gone (ConocoPhillips) — none seeded. TSLA deliberately left
out of grid_storage: it's an auto maker first and would drown the map.

Run:  .venv/bin/python seed_energy_universe.py
"""

import json
import time
import datetime as dt

import yfinance as yf

BUCKETS = [
    ("oil_gas_majors", "Oil & Gas Majors", "#E8A33D",
     ["XOM", "CVX", "SHEL", "TTE", "BP", "COP", "EQNR", "SU"]),
    ("shale_ep", "Shale & E&P", "#D97742",
     ["EOG", "FANG", "DVN", "OXY", "APA", "EQT", "AR", "PR", "OVV"]),
    ("oilfield_services", "Oilfield Services", "#A67C52",
     ["SLB", "HAL", "BKR", "NOV", "FTI", "WFRD"]),
    ("midstream_lng", "Midstream & LNG", "#C9A227",
     ["LNG", "KMI", "WMB", "ET", "EPD", "TRGP", "OKE", "MPLX"]),
    ("refining_downstream", "Refining & Downstream", "#B65D32",
     ["MPC", "PSX", "VLO", "DINO"]),
    ("nuclear_uranium", "Nuclear & Uranium", "#F2D43D",
     ["CCJ", "CEG", "OKLO", "SMR", "LEU", "NXE", "UEC", "UUUU", "BWXT"]),
    ("renewables_solar", "Renewables & Solar", "#9CC65A",
     ["FSLR", "ENPH", "NEE", "RUN", "SEDG", "NXT", "ARRY", "BEP"]),
    ("grid_storage", "Grid, Storage & Electrification", "#F08C4A",
     ["GEV", "ETN", "VRT", "PWR", "FLNC", "BE", "EOSE", "HUBB"]),
    ("power_utilities_ipp", "Power & IPPs", "#CB9E6E",
     ["VST", "NRG", "TLN", "DUK", "SO", "D", "PEG", "ETR"]),
]

SEED_NOTE = "seeded {} by seed_energy_universe.py; live fields maintained by update_quotes.py"


def pct(closes, days):
    if len(closes) <= days:
        return None
    prev = closes[-1 - days]
    return round((closes[-1] / prev - 1) * 100, 1) if prev else None


def main():
    all_syms = [s for _, _, _, syms in BUCKETS for s in syms]
    assert len(all_syms) == len(set(all_syms)), "duplicate ticker across buckets"
    print(f"{len(all_syms)} tickers in {len(BUCKETS)} buckets — downloading 1y bars...")

    px = yf.download(all_syms, period="1y", interval="1d", auto_adjust=True,
                     progress=False, group_by="ticker", threads=True)

    today = dt.date.today().isoformat()
    bubbles, failures = [], []
    for bid, label, color, syms in BUCKETS:
        tickers, industries = [], set()
        for s in syms:
            try:
                c = px[s]["Close"].dropna()
                v = px[s]["Volume"].dropna()
                if len(c) < 2:
                    raise ValueError("no price history")
                closes = [round(float(x), 2) for x in c]
                info = {}
                try:
                    info = yf.Ticker(s).info or {}
                except Exception:
                    pass
                time.sleep(0.4)  # be polite to Yahoo on the one-time seed
                cap = info.get("marketCap")
                industry = info.get("industry") or ""
                if industry:
                    industries.add(industry)
                entry = {
                    "ticker": s,
                    "company": info.get("shortName") or info.get("longName") or s,
                    "sector": info.get("sector") or "Energy",
                    "industry": industry or "—",
                    "country": info.get("country") or "USA",
                    "market_cap_b": round(cap / 1e9, 2) if cap else None,
                    "pe": round(info["trailingPE"], 2) if isinstance(info.get("trailingPE"), (int, float)) else None,
                    "price": closes[-1],
                    "change_pct": round((closes[-1] / closes[-2] - 1) * 100, 2),
                    "volume": int(v.iloc[-1]) if len(v) else 0,
                    "perf": {"1W": pct(closes, 5), "1M": pct(closes, 21),
                             "1Y": pct(closes, min(252, len(closes) - 1))},
                    "spark": closes[-30:],
                    "_note": SEED_NOTE.format(today),
                }
                if isinstance(info.get("forwardEps"), (int, float)):
                    entry["fwd_eps"] = round(info["forwardEps"], 2)
                tickers.append(entry)
                print(f"  {s:6} {entry['company'][:32]:32} ${entry['price']:>9} cap={entry['market_cap_b']}B")
            except Exception as e:
                failures.append(f"{s}: {e}")
                print(f"  {s:6} FAILED — {e}")
        caps = [t["market_cap_b"] for t in tickers if t["market_cap_b"]]
        moves = [t["change_pct"] for t in tickers]
        bubbles.append({
            "id": bid, "label": label, "color": color, "count": len(tickers),
            "total_market_cap_b": round(sum(caps), 2),
            "avg_change_pct": round(sum(moves) / len(moves), 2) if moves else 0,
            "industries_included": sorted(industries),
            "tickers": tickers,
        })

    out = {
        "meta": {
            "source": "Energy Trade curated universe (seed_energy_universe.py)",
            "as_of": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "total_tickers": sum(b["count"] for b in bubbles),
            "min_bubble_size": 7,
            "render_spec": {
                "bubble_size": "sqrt(total_market_cap_b) — sqrt scale so megacaps don't drown the map",
                "bubble_color": "avg_change_pct (red<0<green) or fixed category color",
                "drilldown": "click bubble -> packed circles of member tickers, ticker circle size = sqrt(market_cap_b), color = change_pct",
                "tooltip": "company, industry, cap, P/E, price, day %",
            },
            "session": "closed",
        },
        "bubbles": bubbles,
    }
    with open("universe.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nuniverse.json written: {out['meta']['total_tickers']} tickers, {len(bubbles)} bubbles")
    if failures:
        print("FAILURES (fix or drop before shipping):")
        for f_ in failures:
            print("  " + f_)


if __name__ == "__main__":
    main()
