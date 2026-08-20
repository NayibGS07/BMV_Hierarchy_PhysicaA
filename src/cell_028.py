def rolling_global_distance(df_ret, df_sym_global, method, window, cfg, universe, symbol_mode, diag):
    """Rolling NTL computation. Returns Series of NTL values."""
    assert method in ALL_METHODS
    if method == 'symbolic':
        assert symbol_mode in ('strict', 'inwindow')
    universe = canon_universe(universe)
    min_common = _effective_min_common(cfg, window=window)
    dates = np.array(sorted(df_ret['Fecha'].unique()))
    out = {}
    desc = f'Rolling NTL {method} w={window}' + (f' ({symbol_mode})' if symbol_mode else '')
    for end_idx in tqdm(range(window, len(dates) + 1), desc=desc, leave=True):
        diag.total_windows += 1
        win_dates = set(dates[end_idx - window:end_idx])
        t_end = pd.Timestamp(dates[end_idx - 1])
        try:
            if method in ('mantegna', 'spearman'):
                sub = df_ret[df_ret['Fecha'].isin(win_dates) & df_ret['Ticker'].isin(universe)][['Fecha', 'Ticker', 'r_log']].copy()
                D = mantegna_distance_matrix(sub, cfg, min_common) if method == 'mantegna' else spearman_distance_matrix(sub, cfg, min_common)
            else:
                if symbol_mode == 'strict':
                    sub = df_sym_global[df_sym_global['Fecha'].isin(win_dates) & df_sym_global['Ticker'].isin(universe)][['Fecha', 'Ticker', 'symbol']].copy()
                else:
                    sub_r = df_ret[df_ret['Fecha'].isin(win_dates) & df_ret['Ticker'].isin(universe)][['Fecha', 'Ticker', 'r_log']].copy()
                    sub = symbolize_in_window(sub_r, cfg, diag)[['Fecha', 'Ticker', 'symbol']].copy()
                D = symbolic_distance_matrix(sub, cfg, min_common)
            D = D.loc[universe, universe]
            D2 = drop_isolated_tickers(D, cfg.min_valid_peers)
            if D2.shape[0] < 2:
                diag.nan_windows += 1
                diag.nan_due_isolated += 1
                out[t_end] = np.nan
                continue
            D3, keep = force_largest_connected_component(D2)
            if set(keep) != set(universe):
                diag.nan_windows += 1
                diag.nan_due_lcc_mismatch += 1
                out[t_end] = np.nan
                continue
            mst = build_mst_from_D(D3)
            out[t_end] = global_distance_norm(mst) if cfg.gd_normalize else global_distance(mst)
            diag.ok_windows += 1
        except Exception:
            diag.nan_windows += 1
            diag.nan_due_exception += 1
            out[t_end] = np.nan
    return pd.Series(out).sort_index()

def rolling_topological_metrics(df_ret, df_sym_global, method, window, cfg, universe, symbol_mode):
    """ Rolling APL_weighted, diameter_topo, degree_entropy."""
    assert method in ALL_METHODS
    if method == 'symbolic':
        assert symbol_mode in ('strict', 'inwindow')
    universe = canon_universe(universe)
    min_common = _effective_min_common(cfg, window=window)
    dates = np.array(sorted(df_ret['Fecha'].unique()))
    out_apl, out_diam, out_ent = ({}, {}, {})
    desc = f'Rolling topo {method} w={window}' + (f' ({symbol_mode})' if symbol_mode else '')
    for end_idx in tqdm(range(window, len(dates) + 1), desc=desc, leave=True):
        win_dates = set(dates[end_idx - window:end_idx])
        t_end = pd.Timestamp(dates[end_idx - 1])
        try:
            if method in ('mantegna', 'spearman'):
                sub = df_ret[df_ret['Fecha'].isin(win_dates) & df_ret['Ticker'].isin(universe)][['Fecha', 'Ticker', 'r_log']].copy()
                D = mantegna_distance_matrix(sub, cfg, min_common) if method == 'mantegna' else spearman_distance_matrix(sub, cfg, min_common)
            else:
                if symbol_mode == 'strict':
                    sub = df_sym_global[df_sym_global['Fecha'].isin(win_dates) & df_sym_global['Ticker'].isin(universe)][['Fecha', 'Ticker', 'symbol']].copy()
                else:
                    sub_r = df_ret[df_ret['Fecha'].isin(win_dates) & df_ret['Ticker'].isin(universe)][['Fecha', 'Ticker', 'r_log']].copy()
                    sub = symbolize_global(sub_r, cfg)[['Fecha', 'Ticker', 'symbol']].copy()
                D = symbolic_distance_matrix(sub, cfg, min_common)
            D = D.loc[universe, universe]
            D2 = drop_isolated_tickers(D, cfg.min_valid_peers)
            if D2.shape[0] < 2:
                out_apl[t_end] = out_diam[t_end] = out_ent[t_end] = np.nan
                continue
            D3, keep = force_largest_connected_component(D2)
            if set(keep) != set(universe):
                out_apl[t_end] = out_diam[t_end] = out_ent[t_end] = np.nan
                continue
            mst = build_mst_from_D(D3)
            out_apl[t_end] = average_path_length_weighted(mst)
            out_diam[t_end] = tree_diameter_topo(mst)
            out_ent[t_end] = degree_entropy(mst)
        except Exception:
            out_apl[t_end] = out_diam[t_end] = out_ent[t_end] = np.nan
    return (pd.Series(out_apl).sort_index(), pd.Series(out_diam).sort_index(), pd.Series(out_ent).sort_index())

def export_rolling_csv(gd, lo, hi, path):
    gd_c = gd.dropna()
    pd.DataFrame({'Date': gd_c.index, 'NTL': gd_c.values, 'CI_low': lo.reindex(gd_c.index).values, 'CI_high': hi.reindex(gd_c.index).values}).to_csv(path, index=False, encoding='utf-8')

def characterize_breaks(gd, lo, hi, method, window):
    """Identify out-of-band episodes (integration / fragmentation)."""
    g = gd.dropna()
    lo_r = lo.reindex(g.index)
    hi_r = hi.reindex(g.index)
    above, below = (g > hi_r, g < lo_r)
    rows = []
    in_ep = False
    ep_start = ep_dir = prev_date = None
    ep_vals = ep_lo = ep_hi = []
    for date, val in g.items():
        is_out = bool(above.loc[date]) or bool(below.loc[date])
        if is_out and (not in_ep):
            in_ep = True
            ep_start = date
            ep_dir = 'fragmentation' if bool(above.loc[date]) else 'integration'
            ep_vals = [val]
            ep_lo = [float(lo_r.loc[date])]
            ep_hi = [float(hi_r.loc[date])]
        elif is_out and in_ep:
            ep_vals.append(val)
            ep_lo.append(float(lo_r.loc[date]))
            ep_hi.append(float(hi_r.loc[date]))
        elif not is_out and in_ep:
            mags = [v - h if v > h else l - v for v, l, h in zip(ep_vals, ep_lo, ep_hi)]
            rows.append({'Method': method, 'Window': window, 'Start': ep_start, 'End': prev_date, 'Duration_days': len(ep_vals), 'Direction': ep_dir, 'NTL_mean': round(float(np.mean(ep_vals)), 6), 'Magnitude_mean': round(float(np.mean(mags)), 6), 'Magnitude_max': round(float(np.max(mags)), 6)})
            in_ep = False
        prev_date = date
    if in_ep:
        mags = [v - h if v > h else l - v for v, l, h in zip(ep_vals, ep_lo, ep_hi)]
        rows.append({'Method': method, 'Window': window, 'Start': ep_start, 'End': g.index[-1], 'Duration_days': len(ep_vals), 'Direction': ep_dir, 'NTL_mean': round(float(np.mean(ep_vals)), 6), 'Magnitude_mean': round(float(np.mean(mags)), 6), 'Magnitude_max': round(float(np.max(mags)), 6)})
    return pd.DataFrame(rows)

def hub_stability_rolling(df_ret, df_sym_global, method, window, cfg, universe, symbol_mode):
    """Rolling hub identification for temporal stability analysis."""
    assert method in ALL_METHODS
    universe = canon_universe(universe)
    min_common = _effective_min_common(cfg, window=window)
    dates = np.array(sorted(df_ret['Fecha'].unique()))
    rows = []
    desc = f'HubStab {method} w={window}'
    for end_idx in tqdm(range(window, len(dates) + 1), desc=desc, leave=False):
        win_dates = set(dates[end_idx - window:end_idx])
        t_end = pd.Timestamp(dates[end_idx - 1])
        try:
            if method in ('mantegna', 'spearman'):
                sub = df_ret[df_ret['Fecha'].isin(win_dates) & df_ret['Ticker'].isin(universe)][['Fecha', 'Ticker', 'r_log']].copy()
                D = mantegna_distance_matrix(sub, cfg, min_common) if method == 'mantegna' else spearman_distance_matrix(sub, cfg, min_common)
            else:
                if symbol_mode == 'strict':
                    sub = df_sym_global[df_sym_global['Fecha'].isin(win_dates) & df_sym_global['Ticker'].isin(universe)][['Fecha', 'Ticker', 'symbol']].copy()
                else:
                    sub_ret = df_ret[df_ret['Fecha'].isin(win_dates) & df_ret['Ticker'].isin(universe)][['Fecha', 'Ticker', 'r_log']].copy()
                    sub = symbolize_in_window(sub_ret, cfg)[['Fecha', 'Ticker', 'symbol']].copy()
                D = symbolic_distance_matrix(sub, cfg, min_common)
            D = D.loc[universe, universe]
            D2 = drop_isolated_tickers(D, cfg.min_valid_peers)
            if D2.shape[0] < 2:
                continue
            D3, keep = force_largest_connected_component(D2)
            if set(keep) != set(universe):
                continue
            mst = build_mst_from_D(D3)
            hub_ticker, hub_degree, was_tied, _ = select_hub(mst)
            rows.append({'Date': t_end, 'Method': method, 'Window': window, 'Mode': symbol_mode if symbol_mode else '', 'Hub_ticker': hub_ticker, 'Hub_degree': int(hub_degree), 'Hub_tied': was_tied, 'Hub_sector': cfg.sector_map.get(hub_ticker, 'Other'), 'N_nodes': mst.number_of_nodes()})
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    df_hub = pd.DataFrame(rows)
    top_hub = df_hub['Hub_ticker'].value_counts().idxmax()
    top_freq = df_hub['Hub_ticker'].value_counts().max()
    df_hub['Is_dominant_hub'] = df_hub['Hub_ticker'] == top_hub
    log.info('Hub stability %s w=%d: %s | %.1f%%', method, window, top_hub, 100 * top_freq / len(df_hub))
    safe_write_csv(df_hub, os.path.join(cfg.out_dir, f'hub_stability_{method}_w{window}.csv'))
    return df_hub

def seasonality_cv_log(gd, method, window):
    """ Log monthly CV max — no figure generated."""
    g = gd.dropna().reset_index()
    g.columns = ['Date', 'NTL']
    g['Month'] = g['Date'].dt.month
    seasonal = g.groupby('Month')['NTL'].agg(Mean='mean', Std='std').reset_index()
    seasonal['CV'] = seasonal['Std'] / seasonal['Mean']
    max_cv = float(seasonal['CV'].max()) if len(seasonal) else 0.0
    log.info('Seasonality %s w=%d: CV_max=%.4f — %s', method, window, max_cv, 'NO seasonality detected' if max_cv < 0.2 else 'ALERT: possible seasonality')
    return max_cv
