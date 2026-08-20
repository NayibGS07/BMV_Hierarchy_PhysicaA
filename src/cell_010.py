# --- Notebook code cell 10 ---

@dataclass
class RollingDiagnostics:
    total_windows: int = 0
    ok_windows: int = 0
    nan_windows: int = 0
    nan_due_lcc_mismatch: int = 0
    nan_due_isolated: int = 0
    nan_due_exception: int = 0
    tickers_insufficient_symbol_obs_total: int = 0
    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in
                ["total_windows","ok_windows","nan_windows",
                 "nan_due_lcc_mismatch","nan_due_isolated","nan_due_exception",
                 "tickers_insufficient_symbol_obs_total"]}

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def canon_universe(nodes: List[str]) -> List[str]:
    return sorted(set(nodes))

def pivot_panel(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    return df.pivot_table(index="Fecha", columns="Ticker",
                          values=value_col, aggfunc="first")

def _effective_min_common(cfg: Config, window: Optional[int] = None) -> int:
    if window is None:
        return int(cfg.min_common_dates_pair)

    return int(max(10, math.floor(cfg.min_common_frac_in_window * window)))

def safe_write_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False, encoding="utf-8")

def json_safe(obj: Any) -> Any:
    if isinstance(obj, dict): return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)): return [json_safe(v) for v in obj]
    if isinstance(obj, np.integer): return int(obj)
    if isinstance(obj, np.floating): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    if isinstance(obj, (bool, int, float, str, type(None))): return obj
    return str(obj)

def write_manifest(cfg: Config, rngs: RNGPack, path: str) -> None:
    import scipy
    import importlib.metadata as importlib_metadata
    payload = {
        "version": "1.0.0",
        "config": json_safe(cfg.__dict__),
        "seed": cfg.seed,
        "methods": list(ALL_METHODS),
        "packages": {"python": platform.python_version(),
                     "numpy": np.__version__, "pandas": pd.__version__,
                     "scipy": scipy.__version__,
                     "networkx": nx.__version__,
                     "matplotlib": matplotlib.__version__,
                     "yfinance": getattr(yf, "__version__", "unknown"),
                     "statsmodels": importlib_metadata.version("statsmodels"),
                     "tqdm": importlib_metadata.version("tqdm")},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info("Manifest written: %s", path)

def _save_fig(fig, path, cfg):
    """Save a figure in both formats needed for the paper.

    PDF (vector, primary): what actually gets \\includegraphics'd into the
    LaTeX manuscript. Infinitely scalable, sharp at any zoom, small file
    size for line/network plots. Fonts are embedded as TrueType (Type 42,
    see matplotlib.rcParams at the top of this notebook) rather than
    matplotlib's default bitmap Type 3, which is what makes text in the
    PDF stay crisp instead of pixelating when the reader zooms in.

    PNG (raster, secondary, dpi=cfg.dpi=300): for quick previews, slide
    decks, or anywhere a vector format isn't accepted.
    """
    path = str(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pdf_path = path if path.endswith(".pdf") else re.sub(r"\.png$", ".pdf", path)
    png_path = path if path.endswith(".png") else re.sub(r"\.pdf$", ".png", path)
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=cfg.dpi, bbox_inches="tight")
    plt.show()
    plt.close(fig)
    log.info("Saved: %s (+.png preview)", pdf_path)
