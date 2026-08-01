#!/usr/bin/env python3
"""gen_stock_pages.py — generate canonical /stocks/<sym> pages for tickers that
appear in Energy Trade content but had no static page (previously served only by the
noindexed /t?sym= twin).

Template = the existing stock-page template (mirrors stocks/corz.html exactly):
head (title/description/canonical/OG/breadcrumb) + tkp main (About = Yahoo
business summary, industry context = the site's published INDUSTRY_ABOUT
editorial text, Key data, Valuation read via the SAME reverse-DCF the
fair-value calculator uses (accounts/api.js: r=9%, 10y, terminal 2.5%),
TradingView chart, related names) + live-patch script. Emits pageheader/footer
stubs — run gen_nav.py + gen_footer.py after to inject the ds-v2 shell, then
gen_sitemap.py (stocks/*.html is globbed automatically) and _gen_about.py.

Valuation read is OMITTED when forward EPS is not positive (story-stock
precedent — same rule as accounts/api.js _eps). No data is invented: quotes,
caps, summaries and analyst rows come from Yahoo (the site's data source);
if a field is missing the row is dropped.

Run:  .venv/bin/python gen_stock_pages.py
"""
import datetime, html, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

# ── which pages to build ─────────────────────────────────────────────────────
# group  -> which published INDUSTRY_ABOUT editorial text frames the industry
# rel    -> related-names row (all must be existing /stocks pages)
# ctx    -> ONE honest per-company sentence tying it to the AI trade (facts
#           already covered by Santro's published articles/pages)
NEW_TICKERS = {
    # ── Oil & Gas Majors ──
    "XOM": {"group": "oil_gas_majors", "h2": "The oil &amp; gas majors",
             "rel": ["cvx", "shel", "tte", "bp"],
             "ctx": "ExxonMobil is the largest US oil company, with Permian shale scale, offshore growth in Guyana, and a global refining and chemicals arm."},
    "CVX": {"group": "oil_gas_majors", "h2": "The oil &amp; gas majors",
             "rel": ["xom", "shel", "tte", "bp"],
             "ctx": "Chevron pairs Permian and Gulf of Mexico production with global LNG and refining, and closed its long-fought acquisition of Hess in 2025 for a stake in Guyana's oilfields."},
    "SHEL": {"group": "oil_gas_majors", "h2": "The oil &amp; gas majors",
             "rel": ["xom", "cvx", "tte", "bp"],
             "ctx": "Shell is Europe's largest energy company and the world's biggest LNG trader, London-listed with a heavily traded US ADR."},
    "TTE": {"group": "oil_gas_majors", "h2": "The oil &amp; gas majors",
             "rel": ["xom", "cvx", "shel", "bp"],
             "ctx": "TotalEnergies is the French supermajor, distinctive for keeping a large power and renewables arm alongside oil and gas."},
    "BP": {"group": "oil_gas_majors", "h2": "The oil &amp; gas majors",
             "rel": ["xom", "cvx", "shel", "tte"],
             "ctx": "BP is the London major that swung hardest toward renewables and then back to oil and gas after returns disappointed."},
    "COP": {"group": "oil_gas_majors", "h2": "The oil &amp; gas majors",
             "rel": ["xom", "cvx", "shel", "tte"],
             "ctx": "ConocoPhillips is exploration-and-production run at supermajor scale \u2014 no refining arm \u2014 bulked up by the Marathon Oil acquisition."},
    "EQNR": {"group": "oil_gas_majors", "h2": "The oil &amp; gas majors",
             "rel": ["xom", "cvx", "shel", "tte"],
             "ctx": "Equinor is Norway's state-controlled producer, a critical gas supplier to Europe with a growing offshore-wind business."},
    "SU": {"group": "oil_gas_majors", "h2": "The oil &amp; gas majors",
             "rel": ["xom", "cvx", "shel", "tte"],
             "ctx": "Suncor mines and upgrades Canada's oil sands and sells through its Petro-Canada retail chain \u2014 long-life barrels with high extraction costs."},
    # ── Shale & E&P ──
    "EOG": {"group": "shale_ep", "h2": "The shale &amp; E&amp;P industry",
             "rel": ["fang", "dvn", "oxy", "apa"],
             "ctx": "EOG is the benchmark large-cap shale producer, known for low-cost drilling standards and a conservative balance sheet."},
    "FANG": {"group": "shale_ep", "h2": "The shale &amp; E&amp;P industry",
             "rel": ["eog", "dvn", "oxy", "apa"],
             "ctx": "Diamondback is a Permian pure-play that scaled into one of the basin's largest producers through the Endeavor merger."},
    "DVN": {"group": "shale_ep", "h2": "The shale &amp; E&amp;P industry",
             "rel": ["eog", "fang", "oxy", "apa"],
             "ctx": "Devon is a multi-basin US oil producer that pioneered the fixed-plus-variable dividend the sector later copied."},
    "OXY": {"group": "shale_ep", "h2": "The shale &amp; E&amp;P industry",
             "rel": ["eog", "fang", "dvn", "apa"],
             "ctx": "Occidental brings Permian scale, Berkshire Hathaway as its anchor shareholder, and the debt load from its Anadarko and CrownRock acquisitions."},
    "APA": {"group": "shale_ep", "h2": "The shale &amp; E&amp;P industry",
             "rel": ["eog", "fang", "dvn", "oxy"],
             "ctx": "APA pairs US shale with production in Egypt and the North Sea, plus high-stakes exploration offshore Suriname."},
    "EQT": {"group": "shale_ep", "h2": "The shale &amp; E&amp;P industry",
             "rel": ["eog", "fang", "dvn", "oxy"],
             "ctx": "EQT is America's largest natural-gas producer, concentrated in Appalachia, and re-integrated its pipelines by buying back Equitrans."},
    "AR": {"group": "shale_ep", "h2": "The shale &amp; E&amp;P industry",
             "rel": ["eog", "fang", "dvn", "oxy"],
             "ctx": "Antero produces Appalachian gas and liquids with unhedged exposure that makes it one of the highest-torque gas names."},
    "PR": {"group": "shale_ep", "h2": "The shale &amp; E&amp;P industry",
             "rel": ["eog", "fang", "dvn", "oxy"],
             "ctx": "Permian Resources is a Delaware-basin consolidator assembled by rolling up smaller private operators."},
    "OVV": {"group": "shale_ep", "h2": "The shale &amp; E&amp;P industry",
             "rel": ["eog", "fang", "dvn", "oxy"],
             "ctx": "Ovintiv \u2014 the former Encana \u2014 balances oil and gas across the US Permian and Canada's Montney."},
    # ── Oilfield Services ──
    "SLB": {"group": "oilfield_services", "h2": "The oilfield-services industry",
             "rel": ["hal", "bkr", "nov", "fti"],
             "ctx": "SLB is the world's largest oilfield-services company, weighted to international and offshore work and layering digital on top."},
    "HAL": {"group": "oilfield_services", "h2": "The oilfield-services industry",
             "rel": ["slb", "bkr", "nov", "fti"],
             "ctx": "Halliburton dominates North American pressure pumping \u2014 the frack fleets behind US shale output."},
    "BKR": {"group": "oilfield_services", "h2": "The oilfield-services industry",
             "rel": ["slb", "hal", "nov", "fti"],
             "ctx": "Baker Hughes splits between oilfield services and an energy-technology arm that sells LNG turbomachinery."},
    "NOV": {"group": "oilfield_services", "h2": "The oilfield-services industry",
             "rel": ["slb", "hal", "bkr", "fti"],
             "ctx": "NOV builds rigs and drilling equipment \u2014 a capital-equipment cycle that turns even later than services work."},
    "FTI": {"group": "oilfield_services", "h2": "The oilfield-services industry",
             "rel": ["slb", "hal", "bkr", "nov"],
             "ctx": "TechnipFMC leads subsea equipment and integrated offshore projects, a prime beneficiary of the offshore revival."},
    "WFRD": {"group": "oilfield_services", "h2": "The oilfield-services industry",
             "rel": ["slb", "hal", "bkr", "nov"],
             "ctx": "Weatherford is the group's turnaround story \u2014 restructured through bankruptcy into consistent margins."},
    # ── Midstream & LNG ──
    "LNG": {"group": "midstream_lng", "h2": "The midstream &amp; LNG industry",
             "rel": ["kmi", "wmb", "et", "epd"],
             "ctx": "Cheniere is the largest US LNG exporter, selling liquefaction capacity from Sabine Pass and Corpus Christi under contracts that run 15\u201320 years."},
    "KMI": {"group": "midstream_lng", "h2": "The midstream &amp; LNG industry",
             "rel": ["lng", "wmb", "et", "epd"],
             "ctx": "Kinder Morgan owns one of the biggest US natural-gas pipeline networks, increasingly pitched as a data-center power-demand story."},
    "WMB": {"group": "midstream_lng", "h2": "The midstream &amp; LNG industry",
             "rel": ["lng", "kmi", "et", "epd"],
             "ctx": "Williams runs Transco, the workhorse pipeline moving gas up the US East Coast."},
    "ET": {"group": "midstream_lng", "h2": "The midstream &amp; LNG industry",
             "rel": ["lng", "kmi", "wmb", "epd"],
             "ctx": "Energy Transfer is a sprawling pipeline partnership with a high distribution yield and ambitions in LNG and data-center supply."},
    "EPD": {"group": "midstream_lng", "h2": "The midstream &amp; LNG industry",
             "rel": ["lng", "kmi", "wmb", "et"],
             "ctx": "Enterprise Products is the blue-chip MLP \u2014 NGL pipelines, fractionation and exports behind a quarter-century of distributions."},
    "TRGP": {"group": "midstream_lng", "h2": "The midstream &amp; LNG industry",
             "rel": ["lng", "kmi", "wmb", "et"],
             "ctx": "Targa gathers and processes Permian gas and exports NGLs \u2014 the growth name of the midstream group."},
    "OKE": {"group": "midstream_lng", "h2": "The midstream &amp; LNG industry",
             "rel": ["lng", "kmi", "wmb", "et"],
             "ctx": "ONEOK consolidated NGL and refined-products infrastructure through the Magellan and EnLink acquisitions."},
    "MPLX": {"group": "midstream_lng", "h2": "The midstream &amp; LNG industry",
             "rel": ["lng", "kmi", "wmb", "et"],
             "ctx": "MPLX is Marathon Petroleum's midstream partnership, generating the distributions that help fund MPC's buybacks."},
    # ── Refining & Downstream ──
    "MPC": {"group": "refining_downstream", "h2": "The refining &amp; downstream industry",
             "rel": ["psx", "vlo", "dino"],
             "ctx": "Marathon Petroleum is the largest US refiner by capacity, paired with cash flow from its MPLX midstream arm."},
    "PSX": {"group": "refining_downstream", "h2": "The refining &amp; downstream industry",
             "rel": ["mpc", "vlo", "dino"],
             "ctx": "Phillips 66 mixes refining with chemicals and midstream, under recurring activist pressure to simplify the mix."},
    "VLO": {"group": "refining_downstream", "h2": "The refining &amp; downstream industry",
             "rel": ["mpc", "psx", "dino"],
             "ctx": "Valero is the purest large-cap refining bet, with Gulf Coast scale plus a renewable-diesel business."},
    "DINO": {"group": "refining_downstream", "h2": "The refining &amp; downstream industry",
             "rel": ["mpc", "psx", "vlo"],
             "ctx": "HF Sinclair refines in the US mid-continent and Rockies \u2014 smaller and more volatile than the coastal giants."},
    # ── Nuclear & Uranium ──
    "CCJ": {"group": "nuclear_uranium", "h2": "The nuclear &amp; uranium complex",
             "rel": ["ceg", "oklo", "smr", "leu"],
             "ctx": "Cameco is the Western world's largest uranium miner and owns half of reactor-builder Westinghouse."},
    "CEG": {"group": "nuclear_uranium", "h2": "The nuclear &amp; uranium complex",
             "rel": ["ccj", "oklo", "smr", "leu"],
             "ctx": "Constellation operates America's largest nuclear fleet and struck the landmark deal to restart Three Mile Island for Microsoft's data centers."},
    "OKLO": {"group": "nuclear_uranium", "h2": "The nuclear &amp; uranium complex",
             "rel": ["ccj", "ceg", "smr", "leu"],
             "ctx": "Oklo is a pre-revenue developer of small fast reactors aimed squarely at data-center power deals \u2014 a story stock by construction."},
    "SMR": {"group": "nuclear_uranium", "h2": "The nuclear &amp; uranium complex",
             "rel": ["ccj", "ceg", "oklo", "leu"],
             "ctx": "NuScale holds the only small-modular-reactor design approved by US regulators, still chasing its first firm commercial order."},
    "LEU": {"group": "nuclear_uranium", "h2": "The nuclear &amp; uranium complex",
             "rel": ["ccj", "ceg", "oklo", "smr"],
             "ctx": "Centrus is the only listed Western uranium enricher, positioned for the HALEU fuel that advanced reactors will need."},
    "NXE": {"group": "nuclear_uranium", "h2": "The nuclear &amp; uranium complex",
             "rel": ["ccj", "ceg", "oklo", "smr"],
             "ctx": "NexGen owns the Arrow deposit in Saskatchewan \u2014 among the highest-grade undeveloped uranium resources \u2014 with production still years away."},
    "UEC": {"group": "nuclear_uranium", "h2": "The nuclear &amp; uranium complex",
             "rel": ["ccj", "ceg", "oklo", "smr"],
             "ctx": "Uranium Energy Corp restarts idled US mines and holds physical uranium \u2014 high torque to the spot price."},
    "UUUU": {"group": "nuclear_uranium", "h2": "The nuclear &amp; uranium complex",
             "rel": ["ccj", "ceg", "oklo", "smr"],
             "ctx": "Energy Fuels produces US uranium and is building a rare-earths processing line at its White Mesa mill."},
    "BWXT": {"group": "nuclear_uranium", "h2": "The nuclear &amp; uranium complex",
             "rel": ["ccj", "ceg", "oklo", "smr"],
             "ctx": "BWX Technologies builds reactors for the US Navy and government programs \u2014 nuclear exposure with defense-contractor economics."},
    # ── Renewables & Solar ──
    "FSLR": {"group": "renewables_solar", "h2": "The renewables &amp; solar complex",
             "rel": ["enph", "nee", "run", "sedg"],
             "ctx": "First Solar is the largest US-based panel manufacturer and the clearest beneficiary of domestic-content tax credits."},
    "ENPH": {"group": "renewables_solar", "h2": "The renewables &amp; solar complex",
             "rel": ["fslr", "nee", "run", "sedg"],
             "ctx": "Enphase sells microinverters and home batteries for rooftop solar, tightly bound to US residential demand and interest rates."},
    "NEE": {"group": "renewables_solar", "h2": "The renewables &amp; solar complex",
             "rel": ["fslr", "enph", "run", "sedg"],
             "ctx": "NextEra pairs Florida's biggest regulated utility with the world's largest developer of wind and solar."},
    "RUN": {"group": "renewables_solar", "h2": "The renewables &amp; solar complex",
             "rel": ["fslr", "enph", "nee", "sedg"],
             "ctx": "Sunrun leases rooftop solar-and-battery systems \u2014 a financing machine highly sensitive to rates and subsidy rules."},
    "SEDG": {"group": "renewables_solar", "h2": "The renewables &amp; solar complex",
             "rel": ["fslr", "enph", "nee", "run"],
             "ctx": "SolarEdge sells inverters into a European market that boomed and then buried it in excess inventory \u2014 a turnaround bet."},
    "NXT": {"group": "renewables_solar", "h2": "The renewables &amp; solar complex",
             "rel": ["fslr", "enph", "nee", "run"],
             "ctx": "Nextracker is the leader in trackers for utility-scale solar farms and has held margins the sector rarely delivers."},
    "ARRY": {"group": "renewables_solar", "h2": "The renewables &amp; solar complex",
             "rel": ["fslr", "enph", "nee", "run"],
             "ctx": "Array Technologies is the number-two solar-tracker maker \u2014 cheaper and choppier than its bigger rival."},
    "BEP": {"group": "renewables_solar", "h2": "The renewables &amp; solar complex",
             "rel": ["fslr", "enph", "nee", "run"],
             "ctx": "Brookfield Renewable owns hydro, wind and solar assets worldwide \u2014 a distribution-paying vehicle with development ambitions."},
    # ── Grid, Storage & Electrification ──
    "GEV": {"group": "grid_storage", "h2": "Grid, storage &amp; electrification",
             "rel": ["etn", "vrt", "pwr", "flnc"],
             "ctx": "GE Vernova makes the gas turbines and grid equipment the power buildout runs on, with an order book stretching into the 2030s."},
    "ETN": {"group": "grid_storage", "h2": "Grid, storage &amp; electrification",
             "rel": ["gev", "vrt", "pwr", "flnc"],
             "ctx": "Eaton sells the electrical guts of data centers, factories and grids \u2014 a broad toll booth on electrification."},
    "VRT": {"group": "grid_storage", "h2": "Grid, storage &amp; electrification",
             "rel": ["gev", "etn", "pwr", "flnc"],
             "ctx": "Vertiv supplies power and cooling infrastructure for data centers \u2014 the purest AI-buildout exposure in the bucket."},
    "PWR": {"group": "grid_storage", "h2": "Grid, storage &amp; electrification",
             "rel": ["gev", "etn", "vrt", "flnc"],
             "ctx": "Quanta is the contractor that actually builds transmission lines and substations; skilled-labor capacity is its moat."},
    "FLNC": {"group": "grid_storage", "h2": "Grid, storage &amp; electrification",
             "rel": ["gev", "etn", "vrt", "pwr"],
             "ctx": "Fluence delivers grid-scale battery storage systems while fighting Chinese competitors on price."},
    "BE": {"group": "grid_storage", "h2": "Grid, storage &amp; electrification",
             "rel": ["gev", "etn", "vrt", "pwr"],
             "ctx": "Bloom Energy sells fuel cells for on-site power \u2014 a way for data centers to skip the grid-connection queue."},
    "EOSE": {"group": "grid_storage", "h2": "Grid, storage &amp; electrification",
             "rel": ["gev", "etn", "vrt", "pwr"],
             "ctx": "Eos makes zinc-based long-duration batteries \u2014 an early-stage alternative to lithium chemistry."},
    "HUBB": {"group": "grid_storage", "h2": "Grid, storage &amp; electrification",
             "rel": ["gev", "etn", "vrt", "pwr"],
             "ctx": "Hubbell sells grid components and utility hardware \u2014 the quiet compounder of the electrification trade."},
    # ── Power & IPPs ──
    "VST": {"group": "power_utilities_ipp", "h2": "Power producers &amp; utilities",
             "rel": ["nrg", "tln", "duk", "so"],
             "ctx": "Vistra owns gas, nuclear and coal plants selling into competitive power markets \u2014 the defining data-center-power stock of this cycle."},
    "NRG": {"group": "power_utilities_ipp", "h2": "Power producers &amp; utilities",
             "rel": ["vst", "tln", "duk", "so"],
             "ctx": "NRG combines retail electricity, Texas generation, and a partnership with GE Vernova to build plants for data centers."},
    "TLN": {"group": "power_utilities_ipp", "h2": "Power producers &amp; utilities",
             "rel": ["vst", "nrg", "duk", "so"],
             "ctx": "Talen sells output from its Susquehanna nuclear plant to Amazon's data centers \u2014 the deal that kicked off the nuclear-AI trade."},
    "DUK": {"group": "power_utilities_ipp", "h2": "Power producers &amp; utilities",
             "rel": ["vst", "nrg", "tln", "so"],
             "ctx": "Duke is a classic regulated utility across the US Southeast, spending heavily on grid upgrades and new generation."},
    "SO": {"group": "power_utilities_ipp", "h2": "Power producers &amp; utilities",
             "rel": ["vst", "nrg", "tln", "duk"],
             "ctx": "Southern completed the Vogtle expansion \u2014 the first newly built US reactors in decades \u2014 and earns regulated returns on them."},
    "D": {"group": "power_utilities_ipp", "h2": "Power producers &amp; utilities",
             "rel": ["vst", "nrg", "tln", "duk"],
             "ctx": "Dominion serves Virginia's data-center alley, the fastest-growing electricity load in the country."},
    "PEG": {"group": "power_utilities_ipp", "h2": "Power producers &amp; utilities",
             "rel": ["vst", "nrg", "tln", "duk"],
             "ctx": "PSEG pairs a New Jersey regulated utility with nuclear plants courting data-center contracts."},
    "ETR": {"group": "power_utilities_ipp", "h2": "Power producers &amp; utilities",
             "rel": ["vst", "nrg", "tln", "duk"],
             "ctx": "Entergy serves the Gulf South, where LNG terminals and industrial buildout are driving unusual load growth."},
}

# ── published editorial industry texts (single source: ticker-about.js) ──────
src = open("ticker-about.js", encoding="utf-8").read()
m = re.search(r"window\.INDUSTRY_ABOUT=(\{.*?\});", src, re.S)
INDUSTRY_ABOUT = json.loads(m.group(1))

def industry_text(key):
    return INDUSTRY_ABOUT[key]["text"]

# ── the SAME reverse-DCF as accounts/api.js (dcf + impliedGrowth, bisection) ─
def dcf(eps, g, r, years, tg):
    if r <= tg: r = tg + 0.01
    pv, e = 0.0, eps
    for t in range(1, years + 1):
        e *= 1 + g
        pv += e / ((1 + r) ** t)
    pv += (e * (1 + tg)) / (r - tg) / ((1 + r) ** years)
    return pv

def implied_growth(eps, price, r=0.09, years=10, tg=0.025):
    lo, hi = -0.30, 0.6
    for _ in range(60):
        mid = (lo + hi) / 2
        if dcf(eps, mid, r, years, tg) > price: hi = mid
        else: lo = mid
    return (lo + hi) / 2

def glabel(pct):
    if pct < 0:  return "discounted"
    if pct <= 5: return "modest"
    if pct < 18: return "moderate"
    return "punchy"

def fcap(b):
    return f"${b/1000:.2f}T" if b >= 1000 else f"${b:.1f}B"

esc = lambda s: html.escape(str(s or ""), quote=False)

TKP_CSS = """<style>
  .tkp{max-width:1240px;margin:0 auto;padding:6px 20px 50px;}
  .tkp .crumb{font-size:13px;color:var(--faint,#6b7684);margin:14px 0 4px;} .tkp .crumb a{color:var(--muted,#9aa6b2);text-decoration:none;}
  .tkp h1{font-size:28px;margin:10px 0 4px;} .tkp .sub{color:var(--muted,#9aa6b2);font-size:15px;margin:0 0 18px;}
  .tkp h2{font-size:19px;margin:28px 0 8px;} .tkp p,.tkp li{color:var(--muted,#9aa6b2);font-size:15.5px;line-height:1.65;}
  .tkp b{color:var(--text,#e6edf3);} .tkp a{color:var(--accent,#f59e0b);}
  .kv{width:100%;border-collapse:collapse;margin:8px 0 4px;} .kv td{padding:8px 10px;border-bottom:1px solid var(--border-soft,#1c2230);font-size:14.5px;color:var(--muted);} .kv td:first-child{color:var(--faint,#6b7684);width:38%;}
  .rbx{display:inline-block;font-size:11px;font-weight:700;padding:2px 7px;border-radius:5px;background:rgba(240,90,110,.14);color:#f0596e;margin-left:6px;}
  .relx a{display:inline-block;margin:0 8px 6px 0;padding:5px 11px;border:1px solid var(--border-soft,#1c2230);border-radius:7px;font-size:13.5px;text-decoration:none;}
  .ctaE{margin-top:22px;padding:18px 20px;border:1px solid rgba(34,197,94,.28);border-radius:12px;background:rgba(34,197,94,.06);}
  .ctaE a{display:inline-block;background:var(--accent,#f59e0b);color:#fff;padding:9px 16px;border-radius:8px;font-weight:600;text-decoration:none;font-size:14px;margin-top:8px;}
  .nfax{color:var(--faint,#6b7684);font-size:13px;margin-top:18px;}
</style>"""

# pageheader/footer stubs — gen_nav.py / gen_footer.py replace these with the
# ds-v2 meganav + mega footer (same stubs gen_etf_pages.js emits)
HEADER = """  <header class="pageheader">
    <a class="logo" href="/" title="Energy Trade — dashboard">
      <span class="logo-s">S<span class="logo-ai">AI</span></span>
      <span class="logo-rest"><span class="logo-antro">ANTRO</span>
        <span class="logo-tagline">AI&nbsp;RESEARCH&nbsp;·&nbsp;MARKETS</span></span>
    </a>
    <nav class="pagenav">
      <a class="nav-link" href="/">Terminal</a><a class="nav-link" href="/stocks">Stocks</a>
      <a class="nav-link" href="/crypto">Crypto</a><a class="nav-link" href="/bubble">Bubble risk</a>
      <a class="nav-link" href="/research">Research</a><a class="nav-link" href="/about">About</a>
    </nav>
  </header>"""
FOOTER = """  <footer>
    <nav class="foot-nav" style="margin-bottom:6px"><a href="/">Terminal</a> · <a href="/stocks">Stocks</a> · <a href="/ipos">IPOs</a> · <a href="/etfs">ETFs</a> · <a href="/crypto">Crypto</a> · <a href="/news">News</a> · <a href="/research">Research</a> · <a href="/blog">Blog</a> · <a href="/about">About</a> · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></nav>
    Energy Trade — the AI bubble terminal for AI stocks, ETFs, crypto, hot tickers, research and bubble-risk signals. Beta version.<br>
    Quotes delayed ~15 min. Real-time data planned for Pro. <span class="nfa">Not financial advice.</span><br>
    Contact us: <a href="mailto:hello@energytrade.online">hello@energytrade.online</a><br>
    © 2026 Energy Trade. All rights reserved. Uses custom models.
  </footer>"""

LIVE_PATCH = """<script>
/* live-patch the static Key data from universe.json at view time; crawlable
   static values remain the fallback if this fails */
(async()=>{try{
  const SYM=document.querySelector(".kv b").textContent.trim();
  const u=await (await fetch("/universe.json?t="+Date.now())).json();
  let x=null; for(const b of u.bubbles){ x=b.tickers.find(t=>t.ticker===SYM); if(x) break; }
  if(!x||x.price==null) return;
  const fmt=v=>v==null?"—":(v>=0?"+":"")+v.toFixed(1)+"%";
  const rows=[...document.querySelectorAll(".kv tr")];
  const cell=l=>{const r=rows.find(r=>r.cells[0].textContent.trim()===l); return r?r.cells[1]:null;};
  const pc=cell("Price");
  if(pc){const ch=x.change_pct; pc.innerHTML="$"+x.price.toFixed(2)+(ch!=null?' <span style="color:'+(ch>=0?"#22c55e":"#f05a6e")+';font-weight:700">'+fmt(ch)+" today</span>":"");}
  const mc=cell("Market cap"); if(mc&&x.market_cap_b) mc.textContent="$"+x.market_cap_b.toFixed(2)+"B";
  const pf=cell("Performance"); if(pf&&x.perf) pf.textContent="1W "+fmt(x.perf["1W"])+" · 1M "+fmt(x.perf["1M"])+" · 1Y "+fmt(x.perf["1Y"]);
  const sp=document.querySelector(".tkp h2 span");
  if(sp&&u.meta&&u.meta.as_of) sp.textContent="· delayed ~15 min · "+u.meta.as_of;
}catch(e){}})();
</script>"""

def page(sym, cfg, d, asof):
    slug = sym.lower()
    co, sector, ind = d["company"], d.get("sector") or "—", d.get("industry") or "—"
    REL_LABELS = {"sk-hynix": "SK Hynix", "burry-short-watch": "Burry Short Watch"}
    rel = "".join(f'<a href="/stocks/{r}">{REL_LABELS.get(r, r.upper() if len(r)<=5 else r.replace("-", " ").title())}</a>' for r in cfg["rel"])
    # key data rows (only real fields)
    rows = [f'<tr><td>Ticker</td><td><b>{sym}</b></td></tr>',
            f'<tr><td>Company</td><td>{esc(co)}</td></tr>']
    if d.get("price") is not None: rows.append(f'<tr><td>Price</td><td>${d["price"]:.2f}</td></tr>')
    if d.get("market_cap_b"):      rows.append(f'<tr><td>Market cap</td><td>{fcap(d["market_cap_b"])}</td></tr>')
    rows.append(f'<tr><td>Sector / industry</td><td>{esc(sector)} / {esc(ind)}</td></tr>')
    if d.get("target") and d.get("n_analysts"):
        rec = f', {d["rec"]}' if d.get("rec") and d["rec"] != "none" else ""
        rows.append(f'<tr><td>Analyst mean target</td><td>${round(d["target"])} ({d["n_analysts"]} analysts{rec})</td></tr>')
    # valuation read — forward EPS only, same rule as accounts/api.js
    val = ""
    if d.get("fwd_eps") and d["fwd_eps"] > 0 and d.get("price"):
        g = implied_growth(d["fwd_eps"], d["price"]) * 100
        val = (f'\n    <h2>Valuation read</h2>\n'
               f'    <p><b>What the price implies:</b> the market is pricing in roughly <b>~{g:.0f}%/yr</b> '
               f'earnings growth ({glabel(g)}), on a reverse-DCF of forward earnings (${d["fwd_eps"]:.2f}). '
               f'Run your own assumptions in the <a href="/tools/fair-value-calculator">fair-value calculator</a>.</p>\n')
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0a0e13" />
<meta name="mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-title" content="Energy Trade" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<title>{sym} ({esc(co)}) — energy exposure, valuation &amp; data | Energy Trade</title>
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"/>
<link rel="icon" type="image/png" sizes="48x48" href="/assets/favicon-48.png"/>
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png"/>
<link rel="manifest" href="/manifest.json" />
<meta name="description" content="{sym} ({esc(co)}): {esc(ind)}. What it does, the industry it's in, the growth its price implies, key data and related names. Delayed data, not advice."/>
<link rel="canonical" href="https://energytrade.online/stocks/{slug}"/>
<meta property="og:type" content="website"/><meta property="og:site_name" content="Energy Trade"/>
<meta property="og:title" content="{sym} — {esc(co)}"/>
<meta property="og:description" content="{esc(ind)} · in the Energy Trade energy universe"/>
<meta property="og:url" content="https://energytrade.online/stocks/{slug}"/>
<meta property="og:image" content="https://energytrade.online/assets/og-map.png"/>
<meta name="twitter:card" content="summary_large_image"/><meta name="twitter:image" content="https://energytrade.online/assets/og-map.png"/>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
 {{"@type":"ListItem","position":1,"name":"Home","item":"https://energytrade.online/"}},
 {{"@type":"ListItem","position":2,"name":"Energy Stocks","item":"https://energytrade.online/stocks"}},
 {{"@type":"ListItem","position":3,"name":"{sym}","item":"https://energytrade.online/stocks/{slug}"}}]}}
</script>
<link rel="stylesheet" href="/site.css?v=14"/>
{TKP_CSS}
</head><body>
{HEADER}
  <main class="tkp">
    <nav class="crumb" aria-label="Breadcrumb"><a href="/">Home</a> › <a href="/stocks">Energy Stocks</a> › {sym}</nav>
    <h1>{sym} — {esc(co)}</h1>
    <p class="sub">{esc(sector)} · {esc(ind)}</p>

    <h2>About {esc(co)}</h2>
    <p>{esc(d["summary"])}</p>

    <h2>{cfg["h2"]}</h2>
    <p>{industry_text(cfg["group"])} {esc(cfg["ctx"])}</p>

    <h2>Key data <span style="font-size:12px;color:var(--faint,#6b7684)">· delayed ~15 min, as of {asof}</span></h2>
    <table class="kv">
      {chr(10).join("      " + r for r in rows).strip()}
    </table>
{val}
    <h2>Chart</h2>
    <div class="tradingview-widget-container"><div id="tv_{sym}"></div></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
    {{"symbols":[["{sym}"]],"chartOnly":false,"width":"100%","height":300,"colorTheme":"dark","isTransparent":true,"autosize":false}}
    </script>

    <h2>Related energy names</h2>
    <p class="relx">{rel}</p>
    <p>See the full picture on the <a href="/stocks">energy stocks bubble map</a>, or watch the whole sector live on the <a href="/terminal">terminal</a>.</p>

    <div class="ctaE">
      <b>Run a fair-value read on {sym} — free.</b>
      <p>Test what today's price assumes with your own growth and discount inputs — no signup needed.</p>
      <a href="/tools/fair-value-calculator">Open the fair-value calculator →</a>
    </div>
    <p class="nfax">Market data is delayed ~15 minutes and provided for education, not as financial advice. "Hot" means attention, not direction.</p>
  </main>
{FOOTER}
{LIVE_PATCH}
</body></html>"""

def main():
    import yfinance as yf
    asof = datetime.date.today().strftime("%-d %B %Y")
    built, skipped = [], []
    for sym, cfg in NEW_TICKERS.items():
        # idempotent like the other generators: re-running refreshes the baked
        # quotes/analyst rows on the pages this script owns (NEW_TICKERS only)
        try:
            i = yf.Ticker(sym).info
            time.sleep(0.35)  # pace the one-time page build
        except Exception as e:
            print(f"SKIP {sym}: fetch failed ({e})"); skipped.append(sym); continue
        d = {"company": i.get("longName") or i.get("shortName"),
             "sector": i.get("sector"), "industry": i.get("industry"),
             "price": i.get("currentPrice") or i.get("regularMarketPrice"),
             "market_cap_b": round((i.get("marketCap") or 0)/1e9, 2) or None,
             "fwd_eps": i.get("forwardEps"), "target": i.get("targetMeanPrice"),
             "n_analysts": i.get("numberOfAnalystOpinions"), "rec": i.get("recommendationKey"),
             "summary": i.get("longBusinessSummary")}
        if not d["company"] or not d["summary"] or i.get("quoteType") != "EQUITY":
            print(f"SKIP {sym}: insufficient real data (company/summary/equity check failed)")
            skipped.append(sym); continue
        # honest tense: analyst rows/quotes are point-in-time; page carries as-of date
        open(f"stocks/{sym.lower()}.html", "w", encoding="utf-8").write(page(sym, cfg, d, asof))
        built.append(sym); print(f"  wrote stocks/{sym.lower()}.html")
    print(f"done: {len(built)} built ({', '.join(built)})" + (f" · {len(skipped)} skipped" if skipped else ""))
    print("now run: python3 gen_nav.py && python3 gen_footer.py && python3 gen_sitemap.py && python3 _gen_about.py")

if __name__ == "__main__":
    main()
