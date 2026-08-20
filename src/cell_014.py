# --- Notebook code cell 14 ---
# Cross-references the MST/HT hub findings (Section 9-11) against Mexico's
# official list of Locally Systemically Important Banks ("Instituciones de
# Banca Multiple de Importancia Sistemica Local", ISL), published annually
# by the Comision Nacional Bancaria y de Valores (CNBV).
#
# IMPORTANT SCOPE NOTE: this is EXTERNAL REGULATORY TRIANGULATION, not
# "validation" of the MST/HT results in a formal statistical sense. CNBV's
# ISL designation measures BANKING systemic importance (capital buffers,
# balance-sheet interconnectedness); the MST/HT measures CENTRALITY OF
# EQUITY-RETURN CO-MOVEMENT. These are related but conceptually distinct
# constructs, and agreement between them is suggestive corroboration, not
# proof that the network-centrality measure is "correct."
#
# Source: CNBV Junta de Gobierno, annual ISL evaluation approved 28-Apr-2026
# (data as of Dec-2025), published as Comunicado No. 11 on 22-May-2026. This
# "ratification" of the prior year's Comunicado No. 008 (15-Apr-2025, data
# as of Dec-2024) -- it is in fact a new annual evaluation; the set of 8
# designated institutions happens to be unchanged year-over-year, which is
# why some secondary press coverage described it colloquially as a
# "ratification."
# https://www.gob.mx/cnbv/prensa/junta-de-gobierno-de-la-cnbv-determino-las-instituciones-de-banca-multiple-de-importancia-sistemica-local

CNBV_DSIB_2026: List[Dict[str, Any]] = [
    {"institution": "BBVA Mexico", "category": "IV", "listed_ticker": None},
    {"institution": "Santander Mexico", "category": "III", "listed_ticker": None},
    {"institution": "Banorte", "category": "III", "listed_ticker": "GFNORTEO.MX"},
    {"institution": "Banamex (Citigroup)", "category": "I", "listed_ticker": None},
    {"institution": "Scotiabank Mexico", "category": "I", "listed_ticker": None},
    {"institution": "Citi Mexico", "category": "I", "listed_ticker": None},
    {"institution": "HSBC Mexico", "category": "I", "listed_ticker": None},
    {"institution": "Inbursa", "category": "I", "listed_ticker": "GFINBURO.MX"},
]
# Note: category IV = highest additional capital buffer requirement (single
# occupant: BBVA Mexico, the largest bank in the country by market share).
# Of the 8 designated D-SIBs, only Banorte and Inbursa trade as standalone
# public entities with their own BMV ticker among this study's universe --
# the rest are subsidiaries of foreign banking groups without a separately
# listed Mexican equity.

def triangulate_hubs_against_dsib(cfg: Config) -> pd.DataFrame:
    """Return a small table indicating which D-SIB-linked tickers are present
    in the study universe, for direct cross-reference (external regulatory
    triangulation -- see scope note above, this is NOT a formal statistical
    validation) against the hub / betweenness-centrality tables produced in
    Section 9-11."""
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
