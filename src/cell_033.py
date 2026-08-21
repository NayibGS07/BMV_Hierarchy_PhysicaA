# --- Publication support: IPC turnover from curated composition history ---

IPC_HISTORY_PATH = Path("provenance/ipc_composition_history.csv")
IPC_ALIAS_PATH = Path("provenance/ipc_issuer_aliases.csv")


def _load_curated_ipc_history(path: Path = IPC_HISTORY_PATH):
    """Load the compact IPC composition history shipped with the repository.

    Each row represents one official composition snapshot and stores its
    constituent tickers as a semicolon-delimited list. The table is derived
    from official BMV/MexDer notices; copies of those third-party PDFs are
    intentionally not redistributed.
    """
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Curated IPC composition history not found: {path}. "
            "See provenance/README.md and ARTICLE_CROSSWALK.md."
        )
    df = pd.read_csv(path)
    required = {"effective_date", "source", "source_file", "n_tickers", "tickers"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"IPC composition history missing columns: {sorted(missing)}")
    out = []
    for _, row in df.iterrows():
        tickers = [t for t in str(row["tickers"]).split(";") if t]
        if len(tickers) != int(row["n_tickers"]):
            raise ValueError(
                f"IPC snapshot {row['effective_date']} declares {row['n_tickers']} "
                f"tickers but contains {len(tickers)}."
            )
        out.append({
            "effective_date": str(row["effective_date"]),
            "source": str(row["source"]),
            "source_file": str(row["source_file"]),
            "n_tickers": int(row["n_tickers"]),
            "tickers": tickers,
        })
    return sorted(out, key=lambda x: x["effective_date"])


def _load_issuer_aliases(path: Path = IPC_ALIAS_PATH) -> Dict[str, str]:
    if not Path(path).exists():
        return {}
    df = pd.read_csv(path)
    return dict(zip(df["ticker"].astype(str), df["issuer_id"].astype(str)))


def _months_between(d1: str, d2: str) -> int:
    y1, m1, _ = (int(x) for x in d1.split("-"))
    y2, m2, _ = (int(x) for x in d2.split("-"))
    return (y2 - y1) * 12 + (m2 - m1)


def compute_ipc_turnover_from_curated(history=None) -> pd.DataFrame:
    """Ticker/security-level turnover between consecutive available official
    composition snapshots. `spans_gap=True` flags intervals longer than the
    regular semiannual cadence."""
    if history is None:
        history = _load_curated_ipc_history()
    history = [x for x in history if x["effective_date"] >= "2015-01-01"]
    rows, prev = [], None
    for entry in history:
        cur = set(entry["tickers"])
        if prev is not None:
            added = cur - prev["set"]
            dropped = prev["set"] - cur
            rows.append({
                "period_start": prev["effective_date"],
                "period_end": entry["effective_date"],
                "n_add": len(added),
                "n_drop": len(dropped),
                "tickers_added": ", ".join(sorted(added)),
                "tickers_dropped": ", ".join(sorted(dropped)),
                "n_tickers": len(cur),
                "spans_gap": _months_between(prev["effective_date"], entry["effective_date"]) > 7,
            })
        prev = {"effective_date": entry["effective_date"], "set": cur}
    return pd.DataFrame(rows)


def compute_issuer_turnover_from_curated(history=None, aliases=None) -> pd.DataFrame:
    """Issuer-level turnover after collapsing documented same-issuer ticker
    and share-series transitions."""
    if history is None:
        history = _load_curated_ipc_history()
    if aliases is None:
        aliases = _load_issuer_aliases()
    history = [x for x in history if x["effective_date"] >= "2015-01-01"]
    rows, prev = [], None
    for entry in history:
        cur = {aliases.get(t, t) for t in entry["tickers"]}
        if prev is not None:
            added = cur - prev["set"]
            dropped = prev["set"] - cur
            rows.append({
                "period_start": prev["effective_date"],
                "period_end": entry["effective_date"],
                "n_add_issuers": len(added),
                "n_drop_issuers": len(dropped),
                "issuers_added": ", ".join(sorted(added)),
                "issuers_dropped": ", ".join(sorted(dropped)),
                "n_issuers": len(cur),
                "spans_gap": _months_between(prev["effective_date"], entry["effective_date"]) > 7,
            })
        prev = {"effective_date": entry["effective_date"], "set": cur}
    return pd.DataFrame(rows)


def plot_ipc_turnover(df_turnover: pd.DataFrame, cfg: Config, path: str) -> None:
    """Plot ticker-level IPC additions/removals from the curated history."""
    fig, ax = plt.subplots(figsize=(13, 5))
    x = np.arange(len(df_turnover))
    labels = df_turnover["period_end"].tolist()
    add_colors = ["#2E7D32" if not g else "#A5D6A7" for g in df_turnover["spans_gap"]]
    drop_colors = ["#B71C1C" if not g else "#EF9A9A" for g in df_turnover["spans_gap"]]
    ax.bar(x - 0.2, df_turnover["n_add"], width=0.4, color=add_colors, label="Additions")
    ax.bar(x + 0.2, -df_turnover["n_drop"], width=0.4, color=drop_colors, label="Removals")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_ylabel("Number of tickers")
    ax.set_title("S&P/BMV IPC reconstitution turnover (2015–2026)",
                 fontsize=12, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    ax.text(
        0.01, 0.02,
        "Lighter bars: interval spans a known history gap; turnover is aggregated across the longer interval.",
        transform=ax.transAxes, fontsize=7, style="italic"
    )
    plt.tight_layout()
    _save_fig(fig, path, cfg)
