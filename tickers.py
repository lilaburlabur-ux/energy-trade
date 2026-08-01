# =====================================================================
#  YOUR TICKERS  —  this is the ONE file you edit.
# =====================================================================
#  The heatmap resizes itself automatically to whatever is here.
#  Keep in sync with seed_energy_universe.py bucket membership.
# ---------------------------------------------------------------------

TICKERS = [
    # Oil & Gas Majors
    "XOM", "CVX", "SHEL", "TTE", "BP", "COP", "EQNR", "SU",
    # Shale & E&P
    "EOG", "FANG", "DVN", "OXY", "APA", "EQT", "AR", "PR", "OVV",
    # Oilfield Services
    "SLB", "HAL", "BKR", "NOV", "FTI", "WFRD",
    # Midstream & LNG
    "LNG", "KMI", "WMB", "ET", "EPD", "TRGP", "OKE", "MPLX",
    # Refining & Downstream
    "MPC", "PSX", "VLO", "DINO",
    # Nuclear & Uranium
    "CCJ", "CEG", "OKLO", "SMR", "LEU", "NXE", "UEC", "UUUU", "BWXT",
    # Renewables & Solar
    "FSLR", "ENPH", "NEE", "RUN", "SEDG", "NXT", "ARRY", "BEP",
    # Grid, Storage & Electrification
    "GEV", "ETN", "VRT", "PWR", "FLNC", "BE", "EOSE", "HUBB",
    # Power & IPPs
    "VST", "NRG", "TLN", "DUK", "SO", "D", "PEG", "ETR",
]

# Optional: nicer company names shown in the tooltip / details panel.
NAMES = {
    "XOM":  "ExxonMobil",
    "CVX":  "Chevron",
    "SHEL": "Shell",
    "TTE":  "TotalEnergies",
    "BP":   "BP",
    "COP":  "ConocoPhillips",
    "EQNR": "Equinor",
    "SU":   "Suncor Energy",
    "EOG":  "EOG Resources",
    "FANG": "Diamondback Energy",
    "DVN":  "Devon Energy",
    "OXY":  "Occidental Petroleum",
    "APA":  "APA Corp",
    "EQT":  "EQT Corp",
    "AR":   "Antero Resources",
    "PR":   "Permian Resources",
    "OVV":  "Ovintiv",
    "SLB":  "SLB (Schlumberger)",
    "HAL":  "Halliburton",
    "BKR":  "Baker Hughes",
    "NOV":  "NOV Inc",
    "FTI":  "TechnipFMC",
    "WFRD": "Weatherford",
    "LNG":  "Cheniere Energy",
    "KMI":  "Kinder Morgan",
    "WMB":  "Williams Companies",
    "ET":   "Energy Transfer",
    "EPD":  "Enterprise Products",
    "TRGP": "Targa Resources",
    "OKE":  "ONEOK",
    "MPLX": "MPLX",
    "MPC":  "Marathon Petroleum",
    "PSX":  "Phillips 66",
    "VLO":  "Valero Energy",
    "DINO": "HF Sinclair",
    "CCJ":  "Cameco",
    "CEG":  "Constellation Energy",
    "OKLO": "Oklo",
    "SMR":  "NuScale Power",
    "LEU":  "Centrus Energy",
    "NXE":  "NexGen Energy",
    "UEC":  "Uranium Energy Corp",
    "UUUU": "Energy Fuels",
    "BWXT": "BWX Technologies",
    "FSLR": "First Solar",
    "ENPH": "Enphase Energy",
    "NEE":  "NextEra Energy",
    "RUN":  "Sunrun",
    "SEDG": "SolarEdge",
    "NXT":  "Nextracker",
    "ARRY": "Array Technologies",
    "BEP":  "Brookfield Renewable",
    "GEV":  "GE Vernova",
    "ETN":  "Eaton",
    "VRT":  "Vertiv",
    "PWR":  "Quanta Services",
    "FLNC": "Fluence Energy",
    "BE":   "Bloom Energy",
    "EOSE": "Eos Energy",
    "HUBB": "Hubbell",
    "VST":  "Vistra",
    "NRG":  "NRG Energy",
    "TLN":  "Talen Energy",
    "DUK":  "Duke Energy",
    "SO":   "Southern Company",
    "D":    "Dominion Energy",
    "PEG":  "Public Service Enterprise",
    "ETR":  "Entergy",
}

# =====================================================================
#  ETF holdings sheets (authoritative weights from the fund's website).
# =====================================================================
#  When an ETF symbol has a sheet here, fetch.py uses THESE weights
#  instead of Yahoo's auto-pulled top holdings. Tile size = weight.
#  None curated yet for the energy universe.

ETF_HOLDINGS = {}
