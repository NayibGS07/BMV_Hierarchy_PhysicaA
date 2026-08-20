# --- Notebook code cell 6 ---

@dataclass
class Config:
    # Fixed ex-post candidate universe U38: the 30-issue base panel used in
    # the study design plus eight additional March-2026 S&P/BMV IPC
    # constituents. Applying this 2026-informed panel to 2015-2025 creates
    # a look-ahead selection/survivorship limitation for historical-market
    # interpretation; historical composition notices are contextual evidence
    # only and do not define U38.
    tickers_candidate: List[str] = field(default_factory=lambda: [
        # --- 30-issue base panel ---
        "ASURB.MX","GAPB.MX","OMAB.MX",
        "BIMBOA.MX","GRUMAB.MX","KIMBERA.MX","WALMEX.MX",
        "ALSEA.MX","AC.MX","FEMSAUBD.MX","CHDRAUIB.MX","HERDEZ.MX",
        "AMXB.MX","TLEVISACPO.MX","MEGACPO.MX",
        "LIVEPOLC-1.MX","ELEKTRA.MX",
        "CEMEXCPO.MX","ORBIA.MX","ALPEKA.MX",
        "GMEXICOB.MX","PE&OLES.MX","GCC.MX","GCARSOA1.MX",
        "GFNORTEO.MX","GFINBURO.MX","GENTERA.MX","BOLSAA.MX",
        "VOLARA.MX","PINFRA.MX",
        # --- eight additional March-2026 IPC constituents ---
        "BBAJIOO.MX","KOFUBL.MX","VESTA.MX","LABB.MX",
        "LACOMERUBC.MX","Q.MX","RA.MX","SIGMAFA.MX",
    ])

    sector_map: Dict[str,str] = field(default_factory=lambda: {
        "ASURB.MX":"Airports","GAPB.MX":"Airports","OMAB.MX":"Airports",
        "BIMBOA.MX":"Consumer","GRUMAB.MX":"Consumer","KIMBERA.MX":"Consumer",
        "WALMEX.MX":"Consumer","ALSEA.MX":"Consumer","AC.MX":"Consumer",
        "FEMSAUBD.MX":"Consumer","CHDRAUIB.MX":"Consumer","HERDEZ.MX":"Consumer",
        "AMXB.MX":"Telecom","TLEVISACPO.MX":"Telecom","MEGACPO.MX":"Telecom",
        "LIVEPOLC-1.MX":"Retail","ELEKTRA.MX":"Retail",
        "CEMEXCPO.MX":"Materials","ORBIA.MX":"Materials","ALPEKA.MX":"Materials",
        "GMEXICOB.MX":"Materials","PE&OLES.MX":"Materials","GCC.MX":"Materials",
        "GCARSOA1.MX":"Conglomerate",
        "GFNORTEO.MX":"Financial","GFINBURO.MX":"Financial",
        "GENTERA.MX":"Financial","BOLSAA.MX":"Financial",
        "VOLARA.MX":"Transport","PINFRA.MX":"Infrastructure",
        # --- eight additional issuers (economic grouping informed by GICS) ---
        "BBAJIOO.MX":"Financial",     # GICS: Banks (regional bank, Banco del Bajio)
        "KOFUBL.MX":"Consumer",       # GICS: Consumer Staples > Beverages (Coca-Cola FEMSA)
        "VESTA.MX":"Real Estate",     # GICS: Real Estate Mgmt. & Development
        "LABB.MX":"Health Care",      # GICS: Pharmaceuticals (Genomma Lab)
        "LACOMERUBC.MX":"Consumer",   # GICS: Consumer Staples > Food & Staples Retailing (La Comer, supermarkets)
        "Q.MX":"Financial",           # GICS: Insurance (Qualitas, auto P&C insurer)
        "RA.MX":"Financial",          # GICS: Banks (Regional / Banregio)
        "SIGMAFA.MX":"Consumer",      # GICS: Consumer Staples > Food Products (Sigma Foods)
    })
    sector_colors: Dict[str,str] = field(default_factory=lambda: {
        "Airports":"#1565C0","Consumer":"#2E7D32","Telecom":"#6A1B9A",
        "Retail":"#E65100","Materials":"#4E342E","Conglomerate":"#37474F",
        "Financial":"#B71C1C","Transport":"#00838F","Infrastructure":"#F57F17",
        "Health Care":"#AD1457","Real Estate":"#827717",
        "Other":"#9E9E9E",
    })
    historical_events: Dict[str,str] = field(default_factory=lambda: {
        "COVID-19\n(Mar-2020)":"2020-03-16",
        "Fed rates\n(Mar-2022)":"2022-03-16",
        "MX elections\n(Jun-2024)":"2024-06-02",
    })
    start: str = "2015-01-01"
    # NOTE: yfinance treats `end` as EXCLUSIVE (like a Python slice) -- with
    # end="2025-12-31" the last trading day actually returned would be
    # 2025-12-30, silently dropping the final day(s) of the study window.
    # Using the first day of the following year guarantees all of 2025 is
    # included.
    end:   str = "2026-01-01"
    # Display-only label for figure titles: the actual study period is
    # 2015-2025; `end` above is a technical (exclusive) API boundary, not
    # the period to report.
    end_display_year: str = "2025"
    min_coverage: float = 0.80
    min_common_dates_pair: int = 120
    min_common_frac_in_window: float = 0.90
    min_valid_peers: int = 3
    q_low: float = 1/3
    q_high: float = 2/3
    min_obs_symbol: int = 30
    symbolic_dist_type: str = "nominal"
    windows: Tuple[int,...] = (120, 240, 360, 480)
    gd_normalize: bool = True
    rolling_symbol_mode: Tuple[str,...] = ("strict", "inwindow")

    n_link_mc: int = 1000
    n_gd_mc: int = 2000
    ci_links: Tuple[float,float] = (0.025, 0.975)
    ci_gd: Tuple[float,float] = (0.05, 0.95)
    mc_max_attempts_factor: int = 5
    mc_null_model: str = "permutation"
    seed: int = 42
    block_size_bootstrap: Optional[int] = None
    hub_stability_windows: Tuple[int,...] = (120, 240, 480)
    # Edge perturbation robustness
    edge_perturbation_ks: Tuple[int,...] = (1, 5, 10, 20, 50)
    edge_perturbation_replicas: int = 100
    # Portable output directory: always relative to THIS notebook's working
    # directory (no machine-specific absolute path). Running the notebook
    # anywhere creates ./bmv_outputs/{figures,tables,data,manifest} automatically.
    out_dir: str = "bmv_outputs"
    dpi: int = 300  # publication-quality raster fallback; vector PDF is the primary format (see _save_fig)

CFG = Config()
os.makedirs(CFG.out_dir, exist_ok=True)

ALL_METHODS = ("symbolic", "mantegna", "spearman")
