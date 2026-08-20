# --- Notebook code cell 12 ---
# A chain-linked predecessor is attempted when the current instrument does not
# cover the complete study period. The splice preserves within-segment returns;
# the transition return itself is removed because it is not directly observed.
# Coca-Cola FEMSA changed its listed unit structure in April 2019, so the
# predecessor KOFL.MX is used only as a documented continuity attempt for
# KOFUBL.MX. The candidate still fails the manuscript's 80% coverage threshold.
TICKER_SPLICES: Dict[str, List[Tuple[str, Optional[str], str]]] = {
    "KOFUBL.MX": [
        ("2015-01-01", "2019-04-11", "KOFL.MX"),
        ("2019-04-11", None, "KOFUBL.MX"),
    ],
}
