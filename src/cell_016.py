def _download_individual(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """Download adjusted price history for one ticker with the per-ticker yfinance API."""
    try:
        h = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
        col = None
        if h is not None and (not h.empty) and ('Adj Close' in h.columns):
            col = 'Adj Close'
        else:
            h = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
            if h is not None and (not h.empty) and ('Close' in h.columns):
                col = 'Close'
                log.info("%s: 'Adj Close' unavailable under auto_adjust=False; used auto_adjust=True adjusted 'Close' instead (never a raw/unadjusted price).", ticker)
        if col is None:
            return None
        s = h[[col]].rename(columns={col: 'AdjClose'}).reset_index()
        s.columns = ['Fecha', 'AdjClose']
        s['Fecha'] = pd.to_datetime(s['Fecha']).dt.tz_localize(None)
        return s
    except Exception as e:
        log.warning('Individual-ticker fallback failed for %s: %s', ticker, e)
        return None

def _download_spliced(canonical_ticker: str, segments, cfg: Config) -> Optional[pd.DataFrame]:
    """Build a chain-linked adjusted price series across a documented ticker transition."""
    parts = []
    for seg_start, seg_end, src in segments:
        seg_end_actual = seg_end or cfg.end
        try:
            raw = yf.download(tickers=src, start=seg_start, end=seg_end_actual, auto_adjust=False, progress=False)
            if raw is None or raw.empty:
                log.warning('Splice segment %s (%s to %s) for %s returned no data.', src, seg_start, seg_end_actual, canonical_ticker)
                return None
            col = 'Adj Close' if 'Adj Close' in raw.columns else 'AdjClose'
            s = raw[[col]].rename(columns={col: 'AdjClose'}).reset_index()
            s.columns = ['Fecha', 'AdjClose']
            s['Fecha'] = pd.to_datetime(s['Fecha']).dt.tz_localize(None)
            s = s.dropna(subset=['AdjClose'])
            s = s[s['AdjClose'] > 0].sort_values('Fecha').reset_index(drop=True)
            if len(s) == 0:
                log.warning('Splice segment %s for %s had no valid prices.', src, canonical_ticker)
                return None
            parts.append(s)
        except Exception as e:
            log.warning('Splice segment %s for %s failed: %s', src, canonical_ticker, e)
            return None
    for i in range(len(parts) - 2, -1, -1):
        this_last = parts[i]['AdjClose'].iloc[-1]
        next_first = parts[i + 1]['AdjClose'].iloc[0]
        if not np.isfinite(this_last) or this_last == 0:
            log.warning('Splice rebase failed for %s at segment %d: invalid last price.', canonical_ticker, i)
            return None
        factor = next_first / this_last
        parts[i] = parts[i].copy()
        parts[i]['AdjClose'] = parts[i]['AdjClose'] * factor
    combined = pd.concat(parts, ignore_index=True).drop_duplicates(subset='Fecha', keep='first').sort_values('Fecha').reset_index(drop=True)
    combined['Ticker'] = canonical_ticker
    log.info('Spliced %s from %d segment(s): %d obs, %s to %s.', canonical_ticker, len(segments), len(combined), combined['Fecha'].min().date(), combined['Fecha'].max().date())
    return combined[['Fecha', 'AdjClose', 'Ticker']]

def download_prices(cfg: Config):
    """Returns (df_prices, provenance_rows). provenance_rows records, per
    ticker, exactly HOW its price series was acquired (bulk / individual
    fallback / chain-linked splice / splice-failed-fallback) -- see
    data_provenance.csv in run_pipeline. This matters for a specific,
    otherwise-invisible failure mode: if a TICKER_SPLICES entry's chain-
    link fails, the code falls back to a plain, TRUNCATED single-ticker
    download of just the current instrument -- which may then fail the
    80% coverage filter and show up in ipc_comparison.csv as ordinary
    "In IPC, excluded by coverage", indistinguishable from a genuine
    short-history case like BBAJIOO.MX, even though the real cause was a
    failed splice recovery attempt. Provenance tracking makes that
    distinction auditable.
    """
    provenance = []
    tickers_bulk = [t for t in cfg.tickers_candidate if t not in TICKER_SPLICES]
    log.info('Downloading %d tickers (%d via bulk, %d via splice)...', len(cfg.tickers_candidate), len(tickers_bulk), len(cfg.tickers_candidate) - len(tickers_bulk))
    raw = yf.download(tickers=tickers_bulk, start=cfg.start, end=cfg.end, group_by='ticker', auto_adjust=False, threads=True, progress=False)
    frames = []
    if isinstance(raw.columns, pd.MultiIndex):
        available = raw.columns.get_level_values(0).unique().tolist()
        for t in tickers_bulk:
            if t not in available:
                continue
            sub = raw[t].copy()
            col = 'Adj Close' if 'Adj Close' in sub.columns else 'AdjClose' if 'AdjClose' in sub.columns else None
            if col is None:
                continue
            s = sub[[col]].rename(columns={col: 'AdjClose'})
            s.index.name = 'Fecha'
            s['Ticker'] = t
            s = s.reset_index()
            if s['AdjClose'].notna().any():
                frames.append(s)
    else:
        col = 'Adj Close' if 'Adj Close' in raw.columns else 'AdjClose'
        s = raw[[col]].rename(columns={col: 'AdjClose'})
        s.index.name = 'Fecha'
        s['Ticker'] = tickers_bulk[0]
        frames.append(s.reset_index())
    got_bulk = {f['Ticker'].iloc[0] for f in frames if len(f) > 0}
    for t in got_bulk:
        provenance.append({'Ticker': t, 'Acquisition_method': 'Yahoo bulk', 'Source_tickers': t, 'Note': ''})
    missing = [t for t in tickers_bulk if t not in got_bulk]
    for t in missing:
        s = _download_individual(t, cfg.start, cfg.end)
        if s is not None and len(s) > 0:
            s = s.copy()
            s['Ticker'] = t
            frames.append(s[['Fecha', 'AdjClose', 'Ticker']])
            log.info('Recovered %s via individual-ticker fallback (%d obs) -- bulk download had failed for this symbol.', t, len(s))
            provenance.append({'Ticker': t, 'Acquisition_method': 'Yahoo individual fallback', 'Source_tickers': t, 'Note': 'Bulk download failed'})
        else:
            log.warning("%s: no data from bulk OR individual download -- excluded from this run. This is a download/data-availability failure, not a coverage shortfall (see compare_with_ipc()'s Note column for this distinction).", t)
            provenance.append({'Ticker': t, 'Acquisition_method': 'FAILED', 'Source_tickers': '', 'Note': 'No data from any source'})
    for canonical, segments in TICKER_SPLICES.items():
        if canonical not in cfg.tickers_candidate:
            continue
        spliced = _download_spliced(canonical, segments, cfg)
        if spliced is not None and len(spliced) > 0:
            frames.append(spliced)
            src_list = ', '.join((seg[2] for seg in segments))
            transition_dates = ', '.join((seg[0] for seg in segments[1:]))
            provenance.append({'Ticker': canonical, 'Acquisition_method': 'Chain-linked splice', 'Source_tickers': src_list, 'Note': f'Transition date(s) excluded from returns: {transition_dates}'})
        else:
            log.warning('Splice for %s failed -- falling back to a plain single-ticker download (may have truncated coverage).', canonical)
            s = _download_individual(canonical, cfg.start, cfg.end)
            if s is not None and len(s) > 0:
                s = s.copy()
                s['Ticker'] = canonical
                frames.append(s[['Fecha', 'AdjClose', 'Ticker']])
                log.info('%s: recovered via individual-ticker fallback after splice failure (%d obs, likely truncated -- see data_provenance.csv).', canonical, len(s))
                provenance.append({'Ticker': canonical, 'Acquisition_method': 'Yahoo individual fallback (splice failed)', 'Source_tickers': canonical, 'Note': "Chain-link splice failed; using TRUNCATED single-ticker history -- may not meet the coverage threshold despite the issuer's longer true history. Check Coverage in ticker_coverage.csv before trusting an 'excluded by coverage' verdict for this ticker."})
            else:
                provenance.append({'Ticker': canonical, 'Acquisition_method': 'FAILED', 'Source_tickers': '', 'Note': 'Splice failed AND individual fallback failed'})
    if not frames:
        raise RuntimeError('No tickers downloaded.')
    df = pd.concat(frames, ignore_index=True)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df.loc[df['AdjClose'] <= 0, 'AdjClose'] = np.nan
    df = df.dropna(subset=['AdjClose']).sort_values(['Ticker', 'Fecha']).reset_index(drop=True)
    log.info('Downloaded: %d tickers | %s to %s', df['Ticker'].nunique(), df['Fecha'].min().date(), df['Fecha'].max().date())
    return (df, pd.DataFrame(provenance))

def filter_by_coverage(df_prices, cfg):
    all_dates = df_prices['Fecha'].nunique()
    cov = df_prices.groupby('Ticker')['Fecha'].nunique() / max(1, all_dates)
    cov_df = cov.reset_index()
    cov_df.columns = ['Ticker', 'Coverage']
    cov_df['Sector'] = cov_df['Ticker'].map(cfg.sector_map).fillna('Other')
    cov_df['Included'] = cov_df['Coverage'] >= cfg.min_coverage
    cov_df['N_valid_days'] = (cov_df['Coverage'] * all_dates).astype(int)
    cov_df = cov_df.sort_values('Coverage', ascending=False).reset_index(drop=True)
    keep = cov[cov >= cfg.min_coverage].index.tolist()
    out = df_prices[df_prices['Ticker'].isin(keep)].copy()
    log.info('Tickers after coverage filter: %d / %d', len(keep), len(cfg.tickers_candidate))
    return (out, cov_df)

def compute_log_returns(df_prices):
    """Compute the publication analysis for this step."""
    wide = df_prices.pivot(index='Fecha', columns='Ticker', values='AdjClose').sort_index()
    r_wide = np.log(wide).diff()
    d = r_wide.stack(dropna=False).rename('r_log').reset_index()
    d = d.dropna(subset=['r_log']).sort_values(['Ticker', 'Fecha']).reset_index(drop=True)
    log.info('Log returns: %d obs | %d tickers (common-calendar diff)', len(d), d['Ticker'].nunique())
    return d

def _splice_transition_dates(ticker_splices=None) -> Dict[str, List[str]]:
    """For each spliced ticker (see TICKER_SPLICES), the date(s) where one
    segment's price series meets the next -- these are known statically
    from the segment boundaries, not discovered at download time."""
    if ticker_splices is None:
        ticker_splices = TICKER_SPLICES
    return {t: [seg[0] for seg in segments[1:]] for t, segments in ticker_splices.items()}

def null_splice_transition_returns(df_ret: pd.DataFrame, ticker_splices=None) -> pd.DataFrame:
    """Compute the publication analysis for this step."""
    transitions = _splice_transition_dates(ticker_splices)
    if not transitions:
        return df_ret
    df_ret = df_ret.copy()
    n_nulled = 0
    for ticker, dates in transitions.items():
        for d in dates:
            mask = (df_ret['Ticker'] == ticker) & (df_ret['Fecha'] == pd.Timestamp(d))
            n_nulled += int(mask.sum())
            df_ret = df_ret[~mask]
    if n_nulled:
        log.info('Nulled %d splice-transition return(s) -- see null_splice_transition_returns docstring.', n_nulled)
    return df_ret.reset_index(drop=True)

def compute_descriptive_stats(df_ret, cfg):
    rows = []
    for ticker, grp in df_ret.groupby('Ticker'):
        r = grp['r_log'].dropna().values
        if len(r) < 30:
            continue
        jb_stat, jb_pval = jarque_bera(r)
        rows.append({'Ticker': ticker, 'Sector': cfg.sector_map.get(ticker, 'Other'), 'N': len(r), 'Mean_daily': round(float(np.mean(r)), 6), 'Std_daily': round(float(np.std(r, ddof=1)), 6), 'Skewness': round(float(pd.Series(r).skew()), 4), 'Excess_kurtosis': round(float(pd.Series(r).kurtosis()), 4), 'JB_stat': round(float(jb_stat), 2), 'JB_pval': round(float(jb_pval), 6), 'Normal_5pct': jb_pval >= 0.05})
    df_s = pd.DataFrame(rows)
    n_reject = int((~df_s['Normal_5pct']).sum()) if len(df_s) else 0
    log.info('%d/%d reject normality (JB 5%%)', n_reject, len(df_s))
    return df_s
