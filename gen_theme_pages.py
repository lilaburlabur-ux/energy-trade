#!/usr/bin/env python3
"""gen_theme_pages.py — build /stocks/themes/<slug>.html shells for every
bubble in universe.json. Idempotent: overwrites the shells; the live map +
members table between the sector-map/sector-table markers are then filled by
scripts/inject_sector_maps.py (run it right after), and the ds-v2 shell is
injected by gen_nav.py + gen_footer.py.

Intro paragraph = the published INDUSTRY_ABOUT editorial for the bucket
(single source: ticker-about.js) — same text that frames the ticker pages.

Run:  python3 gen_theme_pages.py && python3 scripts/inject_sector_maps.py
"""
import html, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

SITE = "https://energytrade.online"

u = json.load(open("universe.json"))
TOTAL = sum(len(b["tickers"]) for b in u["bubbles"])

src = open("ticker-about.js", encoding="utf-8").read()
m = re.search(r"window\.INDUSTRY_ABOUT=(\{.*?\});", src, re.S)
ABOUT = json.loads(m.group(1))

HEADER = """  <header class="pageheader">
    <a class="logo" href="/" title="Energy Trade — dashboard"><span class="logo-s">E</span></a>
    <nav class="pagenav">
      <a class="nav-link" href="/">Terminal</a><a class="nav-link" href="/stocks">Stocks</a>
      <a class="nav-link" href="/etfs">ETFs</a><a class="nav-link" href="/news">News</a>
      <a class="nav-link" href="/about">About</a>
    </nav>
  </header>"""

FOOTER = """  <footer>
    <nav class="foot-nav" style="margin-bottom:6px"><a href="/">Terminal</a> · <a href="/stocks">Stocks</a> · <a href="/etfs">ETFs</a> · <a href="/news">News</a> · <a href="/about">About</a> · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></nav>
    Energy Trade — the energy market terminal for oil &amp; gas, nuclear, renewables and grid stocks. Beta version.<br>
    Quotes delayed ~15 min. <span class="nfa">Not financial advice.</span>
  </footer>"""

def esc(s): return html.escape(str(s or ""), quote=False)

def fcap(bn):
    return f"${bn/1000:.2f}T" if bn >= 1000 else f"${bn:.0f}B"

def page(b, others):
    slug = b["id"].replace("_", "-")
    label = b["label"]
    n = len(b["tickers"])
    cap = fcap(b["total_market_cap_b"])
    about = ABOUT[b["id"]]["text"]
    rel = " · ".join(
        f'<a href="/stocks/themes/{o["id"].replace("_", "-")}">{esc(o["label"])}</a>'
        for o in others)
    url = f"{SITE}/stocks/themes/{slug}"
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0a0e13" />
<meta name="apple-mobile-web-app-title" content="Energy Trade" />
<title>{esc(label)} Stocks — Live Heat Map ({n} names) | Energy Trade</title>
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"/>
<link rel="manifest" href="/manifest.json" />
<meta name="description" content="Track {n} {esc(label).lower()} stocks on a live heat map, with each ticker's profile, key data and valuation context. Quotes delayed ~15 min. Not financial advice."/>
<link rel="canonical" href="{url}"/>
<meta property="og:type" content="website"/><meta property="og:site_name" content="Energy Trade"/>
<meta property="og:title" content="{esc(label)} — live energy heat map | Energy Trade"/>
<meta property="og:description" content="{n} names · {cap} combined · live heat map · Energy Trade universe"/>
<meta property="og:url" content="{url}"/>
<meta property="og:image" content="{SITE}/assets/og-map.png"/>
<meta name="twitter:card" content="summary_large_image"/>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
 {{"@type":"ListItem","position":1,"name":"Home","item":"{SITE}/"}},
 {{"@type":"ListItem","position":2,"name":"Energy Stocks","item":"{SITE}/stocks"}},
 {{"@type":"ListItem","position":3,"name":"{esc(label)}","item":"{url}"}}]}}
</script>
<link rel="stylesheet" href="/site.css?v=14"/>
<style>
  .tkp{{max-width:1240px;margin:0 auto;padding:6px 20px 50px;}}
  .tkp h1{{font-size:26px;margin:14px 0 4px;}} .tkp .sub{{color:var(--muted);font-size:14.5px;margin:0 0 14px;}}
  .tkp p{{color:var(--muted);font-size:15px;line-height:1.65;}}
  .tt{{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px;}}
  .tt th{{text-align:left;color:var(--faint);font-size:11px;text-transform:uppercase;letter-spacing:.5px;padding:7px 9px;border-bottom:1px solid var(--border);}}
  .tt td{{padding:8px 9px;border-bottom:1px solid var(--border-soft);color:var(--muted);}}
  .tt td.tk a{{color:var(--accent-2);text-decoration:none;font-weight:700;}}
  .tt td.num{{text-align:right;font-variant-numeric:tabular-nums;}}
  .rel{{font-size:13px;color:var(--muted);line-height:1.9;}}
  .rel a{{color:var(--accent-2);text-decoration:none;font-weight:600;}}
  .nfax{{color:var(--faint);font-size:12.5px;margin-top:16px;}}
  @media(max-width:640px){{.tt td:nth-child(3),.tt th:nth-child(3){{display:none;}}}}
  #sector-map{{min-height:200px;}}
  .tt tr.grp td{{padding:14px 9px 5px;color:var(--text);font-weight:800;font-size:11px;letter-spacing:.6px;text-transform:uppercase;border-bottom:1px solid var(--border);}}
</style>
</head><body>
{HEADER}
  <main class="tkp">
    <nav style="font-size:13px;color:var(--faint);margin:14px 0 4px"><a href="/" style="color:var(--muted);text-decoration:none">Home</a> › <a href="/stocks" style="color:var(--muted);text-decoration:none">Energy Stocks</a> › {esc(label)}</nav>
    <h1>{esc(label)} — live heat map &amp; members</h1>
    <p class="sub">{n} names · combined market cap {cap} · part of the Energy Trade {TOTAL}-name universe</p>
    <!-- sector-map:start -->
    <!-- sector-map:end -->
    <p>{esc(about)}</p>
    <!-- sector-table:start -->
    <!-- sector-table:end -->
    <p class="rel"><b style="color:var(--text)">Other themes:</b> {rel}</p>
    <p class="rel">See all names on the <a href="/stocks">energy stocks bubble map</a>, or watch the whole sector live on the <a href="/terminal">terminal</a>.</p>
    <p class="nfax">Seed market caps are approximate and public; live values refresh on the map above and on each ticker page (delayed ~15 min). Membership follows the Energy Trade universe. "Hot" means attention, not direction. Education, not financial advice.</p>
    </main>
{FOOTER}
</body></html>"""

def main():
    os.makedirs("stocks/themes", exist_ok=True)
    for b in u["bubbles"]:
        others = [o for o in u["bubbles"] if o["id"] != b["id"]]
        slug = b["id"].replace("_", "-")
        with open(f"stocks/themes/{slug}.html", "w", encoding="utf-8") as f:
            f.write(page(b, others))
        print(f"  wrote stocks/themes/{slug}.html")
    print(f"done: {len(u['bubbles'])} theme shells — now run scripts/inject_sector_maps.py")

if __name__ == "__main__":
    main()
