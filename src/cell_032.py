def robustness_partition_analysis(df_ret, cfg, universe, partitions=None):
    """Symbolic partition robustness check."""
    if partitions is None:
        partitions = [(1 / 3, 2 / 3), (1 / 4, 3 / 4), (0.2, 0.8), (0.3, 0.7)]
    universe = canon_universe(universe)
    cfg_base = replace(cfg, q_low=1 / 3, q_high=2 / 3)
    df_s_base = symbolize_global(df_ret, cfg_base)
    df_s_base = df_s_base[df_s_base['Ticker'].isin(universe)][['Fecha', 'Ticker', 'symbol']].copy()
    D_base = symbolic_distance_matrix(df_s_base, cfg_base, _effective_min_common(cfg_base))
    D_base = drop_isolated_tickers(D_base.loc[universe, universe], cfg.min_valid_peers)
    D_base, keep = force_largest_connected_component(D_base)
    if set(keep) != set(universe):
        raise RuntimeError('robustness: base universe not connected.')
    mst_base = build_mst_from_D(D_base)
    gd_base = global_distance_norm(mst_base) if cfg.gd_normalize else global_distance(mst_base)
    edges_base = frozenset((frozenset([u, v]) for u, v in mst_base.edges()))
    bf = D_base.values[np.triu_indices_from(D_base.values, k=1)]
    rows = []
    for ql, qh in partitions:
        cfg_a = replace(cfg, q_low=ql, q_high=qh)
        gd_a = jacc = corr = np.nan
        reason = 'ok'
        try:
            df_s_a = symbolize_global(df_ret, cfg_a)
            df_s_a = df_s_a[df_s_a['Ticker'].isin(universe)][['Fecha', 'Ticker', 'symbol']].copy()
            D_a = symbolic_distance_matrix(df_s_a, cfg_a, _effective_min_common(cfg_a))
            D_a = drop_isolated_tickers(D_a.loc[universe, universe], cfg.min_valid_peers)
            D_a, k2 = force_largest_connected_component(D_a)
            if set(k2) != set(universe):
                reason = 'non_connected'
            else:
                mst_a = build_mst_from_D(D_a)
                gd_a = global_distance_norm(mst_a) if cfg.gd_normalize else global_distance(mst_a)
                edges_a = frozenset((frozenset([u, v]) for u, v in mst_a.edges()))
                jacc = len(edges_base & edges_a) / len(edges_base | edges_a)
                af = D_a.values[np.triu_indices_from(D_a.values, k=1)]
                valid = np.isfinite(bf) & np.isfinite(af)
                if valid.sum() > 2:
                    corr, _ = pearsonr(bf[valid], af[valid])
        except Exception as exc:
            reason = f'exception: {type(exc).__name__}'
        rows.append({'Partition': f'({ql:.2f},{qh:.2f})', 'Is_base': abs(ql - 1 / 3) < 1e-09 and abs(qh - 2 / 3) < 1e-09, 'NTL': round(float(gd_a), 6) if np.isfinite(gd_a) else np.nan, 'Delta_NTL_pct': round(100 * (gd_a - gd_base) / gd_base, 3) if np.isfinite(gd_a) else np.nan, 'Corr_dist': round(float(corr), 5) if np.isfinite(corr) else np.nan, 'Jaccard': round(float(jacc), 5) if np.isfinite(jacc) else np.nan, 'Status': reason})
    return pd.DataFrame(rows)

def mst_leave_one_out(df_ret, df_sym_global, cfg, method, exclude_ticker, base_universe=None):
    """Compute the publication analysis for this step."""
    base = base_universe if base_universe is not None else cfg.tickers_candidate
    universe_loo = [t for t in base if t != exclude_ticker]
    min_common = _effective_min_common(cfg)
    if method == 'symbolic':
        df_filt = df_sym_global[df_sym_global['Ticker'].isin(universe_loo)]
        D = symbolic_distance_matrix(df_filt[['Fecha', 'Ticker', 'symbol']], cfg, min_common)
    elif method == 'mantegna':
        D = mantegna_distance_matrix(df_ret[df_ret['Ticker'].isin(universe_loo)], cfg, min_common)
    elif method == 'spearman':
        D = spearman_distance_matrix(df_ret[df_ret['Ticker'].isin(universe_loo)], cfg, min_common)
    else:
        raise ValueError(f'Unknown method: {method}')
    D = drop_isolated_tickers(D, cfg.min_valid_peers)
    D, universe = force_largest_connected_component(D)
    mst = build_mst_from_D(D)
    hub_ticker, hub_degree, was_tied, _ = select_hub(mst)
    gd = global_distance_norm(mst) if cfg.gd_normalize else global_distance(mst)
    return ({'Excluded_ticker': exclude_ticker, 'Method': method, 'N_nodes': mst.number_of_nodes(), 'Hub': hub_ticker, 'Hub_degree': hub_degree, 'Hub_tied': was_tied, 'NTL': round(gd, 6)}, mst, D, universe)

def mst_without_elektra(df_ret, df_sym_global, cfg, method, base_universe=None):
    """Rebuild the MST after excluding ELEKTRA.MX as a targeted robustness check."""
    row, mst, D, universe = mst_leave_one_out(df_ret, df_sym_global, cfg, method, 'ELEKTRA.MX', base_universe=base_universe)
    row = {'Method': row['Method'], 'N_nodes': row['N_nodes'], 'Hub': row['Hub'], 'Hub_degree': row['Hub_degree'], 'NTL': row['NTL']}
    return (row, mst, D, universe)

def leave_one_out_sensitivity(df_ret, df_sym_global, cfg, method, mst_obs, top_k=5):
    """Compute the publication analysis for this step."""
    base_universe = list(mst_obs.nodes())
    obs_edges = {frozenset([u, v]) for u, v in mst_obs.edges()}
    top_nodes = [t for t, _ in sorted(mst_obs.degree(), key=lambda x: -x[1])[:top_k]]
    rows = []
    for t in top_nodes:
        try:
            row, mst_loo, _, _ = mst_leave_one_out(df_ret, df_sym_global, cfg, method, t, base_universe=base_universe)
        except Exception as e:
            rows.append({'Excluded_ticker': t, 'Method': method, 'Error': str(e)})
            continue
        loo_edges = {frozenset([u, v]) for u, v in mst_loo.edges()}
        shared = obs_edges & loo_edges
        comparable = {e for e in obs_edges if t not in e}
        jacc = len(shared) / len(comparable | loo_edges) if comparable | loo_edges else np.nan
        rows.append({'Excluded_ticker': t, 'Method': method, 'Original_degree': dict(mst_obs.degree())[t], 'New_hub': row['Hub'], 'New_hub_degree': row['Hub_degree'], 'New_NTL': row['NTL'], 'Jaccard_vs_original_backbone': round(float(jacc), 4) if np.isfinite(jacc) else np.nan})
    return pd.DataFrame(rows)

def edge_perturbation_robustness(D_full, mst_obs, cfg, rng):
    """ Backbone stability under random edge weight perturbation.
    For each k in cfg.edge_perturbation_ks, randomly perturb k edge weights
    in the complete graph, rebuild MST, and measure Jaccard vs original."""
    edges_obs = frozenset((frozenset([u, v]) for u, v in mst_obs.edges()))
    tickers = D_full.index.tolist()
    n = len(tickers)
    pairs = [(tickers[i], tickers[j]) for i in range(n) for j in range(i + 1, n) if np.isfinite(D_full.loc[tickers[i], tickers[j]])]
    rows = []
    for k in cfg.edge_perturbation_ks:
        if k > len(pairs):
            continue
        jaccards = []
        for _ in range(cfg.edge_perturbation_replicas):
            D_pert = D_full.copy()
            chosen = rng.choice(len(pairs), size=min(k, len(pairs)), replace=False)
            for idx_p in chosen:
                ti, tj = pairs[idx_p]
                orig = D_pert.loc[ti, tj]
                noise = rng.normal(0, 0.1 * abs(orig) if abs(orig) > 1e-09 else 0.01)
                new_val = max(0.001, orig + noise)
                D_pert.loc[ti, tj] = D_pert.loc[tj, ti] = new_val
            try:
                mst_p = build_mst_from_D(D_pert)
                edges_p = frozenset((frozenset([u, v]) for u, v in mst_p.edges()))
                un = len(edges_obs | edges_p)
                jacc = len(edges_obs & edges_p) / un if un > 0 else np.nan
                jaccards.append(jacc)
            except Exception:
                continue
        if jaccards:
            rows.append({'k_perturbed': k, 'N_replicas': len(jaccards), 'Jaccard_mean': round(float(np.mean(jaccards)), 4), 'Jaccard_std': round(float(np.std(jaccards)), 4), 'Jaccard_min': round(float(np.min(jaccards)), 4), 'Jaccard_q25': round(float(np.quantile(jaccards, 0.25)), 4), 'Jaccard_median': round(float(np.median(jaccards)), 4), 'Jaccard_q75': round(float(np.quantile(jaccards, 0.75)), 4)})
    return pd.DataFrame(rows)

def correlation_intra_inter_module(df_ret, mst, cfg, universe):
    """Intra-sector vs inter-sector mean Pearson correlation."""
    universe = canon_universe(universe)
    pivot = pivot_panel(df_ret[df_ret['Ticker'].isin(universe)][['Fecha', 'Ticker', 'r_log']], 'r_log')
    corr_mat = pivot.corr()
    intra, inter = ([], [])
    for i, ti in enumerate(universe):
        for j in range(i + 1, len(universe)):
            tj = universe[j]
            rho = corr_mat.loc[ti, tj] if ti in corr_mat.index and tj in corr_mat.columns else np.nan
            if not np.isfinite(rho):
                continue
            si = cfg.sector_map.get(ti, 'Other')
            sj = cfg.sector_map.get(tj, 'Other')
            if si == sj:
                intra.append(rho)
            else:
                inter.append(rho)
    result = {'Corr_intra': round(float(np.mean(intra)), 4) if intra else np.nan, 'Corr_inter': round(float(np.mean(inter)), 4) if inter else np.nan, 'N_intra': len(intra), 'N_inter': len(inter), 'Difference': round(float(np.mean(intra)) - float(np.mean(inter)), 4) if intra and inter else np.nan}
    log.info('Corr intra=%.4f | inter=%.4f | diff=%.4f', result['Corr_intra'], result['Corr_inter'], result['Difference'])
    return pd.DataFrame([result])
