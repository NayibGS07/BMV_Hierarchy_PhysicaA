# --- Notebook code cell 14 ---
# External regulatory triangulation using Mexico's annual list of locally
# systemically important banks (Instituciones de Banca Múltiple de Importancia
# Sistémica Local, ISL). The classification is not used to construct the
# network; it is an independent regulatory benchmark for contextual comparison.
# Source: CNBV annual ISL evaluation approved 28-Apr-2026 (information as of
# Dec-2025), publicly communicated 22-May-2026.

CNBV_DSIB_2026: List[Dict[str, Any]] = [
    {"institution": "BBVA Mexico", "category": "IV", "listed_ticker": None},
    {"institution": "Santander Mexico", "category": "III", "listed_ticker": None},
    {"institution": "Banorte", "category": "II", "listed_ticker": "GFNORTEO.MX"},
    {"institution": "Inbursa", "category": "I", "listed_ticker": "GFINBURO.MX"},
    {"institution": "Banamex", "category": "I", "listed_ticker": None},
    {"institution": "Scotiabank Mexico", "category": "I", "listed_ticker": None},
    {"institution": "Citi Mexico", "category": "I", "listed_ticker": None},
    {"institution": "HSBC Mexico", "category": "I", "listed_ticker": None},
]


def triangulate_hubs_against_dsib(cfg: Config) -> pd.DataFrame:
    """Return the CNBV 2026 ISL classification and study-universe presence."""
    rows = []
    for d in CNBV_DSIB_2026:
        t = d["listed_ticker"]
        rows.append({
            "Institution": d["institution"],
            "CNBV_ISL_category": d["category"],
            "Listed_ticker": t if t else "(not separately listed)",
            "In_study_universe": bool(t and t in cfg.tickers_candidate),
        })
    return pd.DataFrame(rows)
