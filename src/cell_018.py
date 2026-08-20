def compute_symbol_thresholds(df_ret, cfg):
    thresholds = {}
    for ticker, grp in df_ret.groupby('Ticker'):
        r = grp['r_log'].dropna().values
        if len(r) < cfg.min_obs_symbol:
            continue
        thresholds[ticker] = (float(np.quantile(r, cfg.q_low)), float(np.quantile(r, cfg.q_high)))
    return thresholds

def symbolize_with_thresholds(df_ret, thresholds):
    rows_list = []
    for ticker, grp in df_ret.groupby('Ticker'):
        if ticker not in thresholds:
            continue
        a, b = thresholds[ticker]
        g2 = grp.copy()
        r = g2['r_log'].values
        g2['symbol'] = np.where(r < a, 1, np.where(r <= b, 2, 3)).astype(np.int16)
        rows_list.append(g2)
    if not rows_list:
        return df_ret.assign(symbol=pd.NA).head(0)
    return pd.concat(rows_list, ignore_index=True).dropna(subset=['symbol']).copy()

def _symbolize_series(s, q_low, q_high, min_obs):
    valid = s.dropna()
    if len(valid) < min_obs:
        return pd.Series(pd.NA, index=s.index, dtype='Int64')
    a, b = (float(valid.quantile(q_low)), float(valid.quantile(q_high)))
    out = pd.Series(pd.NA, index=s.index, dtype='Int64')
    mask = s.notna()
    out[mask] = np.where(s[mask] < a, 1, np.where(s[mask] <= b, 2, 3))
    return out

def symbolize_global(df_ret, cfg):
    d = df_ret.copy()
    d['symbol'] = d.groupby('Ticker')['r_log'].transform(lambda s: _symbolize_series(s, cfg.q_low, cfg.q_high, cfg.min_obs_symbol))
    return d.dropna(subset=['symbol']).copy()

def symbolize_in_window(df_window, cfg, diag=None):
    if diag is not None:
        counts = df_window.dropna(subset=['r_log']).groupby('Ticker')['r_log'].size()
        diag.tickers_insufficient_symbol_obs_total += int((counts < cfg.min_obs_symbol).sum()) if len(counts) else 0
    return symbolize_global(df_window, cfg)
