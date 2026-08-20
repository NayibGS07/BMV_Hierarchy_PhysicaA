def _phase_surrogate_on_rlog(s, rng):
    n = len(s)
    s_c = s - np.mean(s)
    ft = np.fft.rfft(s_c)
    phases = rng.uniform(0.0, 2.0 * np.pi, len(ft))
    ft_surr = np.abs(ft) * np.exp(1j * phases)
    ft_surr[0] = np.real(ft_surr[0])
    if n % 2 == 0:
        ft_surr[-1] = np.real(ft_surr[-1])
    return np.fft.irfft(ft_surr, n=n) + np.mean(s)

def _apply_null_rlog(df_ret, null_model, rng):
    """Null-model generator for the independence-permutation MC framework.

    - "permutation" (default/primary): independently shuffles each
      ticker's own return sequence -- destroys BOTH cross-sectional
      alignment AND each ticker's own temporal structure (autocorrelation,
      volatility clustering).
    - "phase": phase-randomized surrogate.
    - "circular_shift" (secondary null, added alongside the primary): each
      ticker's return sequence is shifted by an independently-drawn random
      offset with wraparound (r_i(t) -> r_i((t+k_i) mod T), k_i drawn
      uniformly from 0..T-1 -- the identity shift k_i=0 is a valid member
      of this group and is not excluded, consistent with the (b+1)/(B+1)
      convention used elsewhere in this pipeline). This preserves each
      ticker's own marginal distribution and CIRCULAR autocorrelation
      structure exactly in the circular sense because the same sequence is
      rotated. Ordinary non-circular sample autocorrelation is preserved only
      approximately because the wraparound changes the boundary adjacency.
      "circular_shift" still destroys contemporaneous cross-sectional
      alignment between tickers -- a strictly weaker null than
      "permutation" in what it destroys. If the same substantive
      conclusions (which links are significant, hub concentration, etc.)
      hold under both "permutation" and "circular_shift", that is stronger
      evidence the results are not an artifact of the specific null
      construction (e.g. of also destroying each series' own
      autocorrelation, which "permutation" does but "circular_shift" does
      not).
    """
    groups = []
    for _, g in df_ret.groupby('Ticker'):
        g2 = g.copy()
        vals = g2['r_log'].to_numpy(dtype=float).copy()
        if null_model == 'phase' and len(vals) > 10:
            g2['r_log'] = _phase_surrogate_on_rlog(vals, rng)
        elif null_model == 'circular_shift' and len(vals) > 2:
            k = int(rng.integers(0, len(vals)))
            g2['r_log'] = np.roll(vals, k)
        else:
            rng.shuffle(vals)
            g2['r_log'] = vals
        groups.append(g2)
    return pd.concat(groups, ignore_index=True)

def _mc_pval_ge(sims_col, obs):
    """Compute the publication analysis for this step."""
    B = len(sims_col)
    b = int(np.sum(sims_col <= obs))
    return (b + 1) / (B + 1)

def _compute_mc_pvalues_twosided(obs_weights, sims_arr):
    out = []
    B = sims_arr.shape[0]
    for k, obs in enumerate(obs_weights):
        p_le = _mc_pval_ge(sims_arr[:, k], obs)
        p_ge = (int(np.sum(sims_arr[:, k] >= obs)) + 1) / (B + 1)
        out.append(min(2.0 * min(p_le, p_ge), 1.0))
    return out

def _compute_mc_pvalues_onesided(obs_weights, sims_arr):
    """Compute the publication analysis for this step."""
    return [_mc_pval_ge(sims_arr[:, k], obs) for k, obs in enumerate(obs_weights)]

def mst_edge_length_order_statistic_test(df_ret_snapshot, thresholds, method, cfg, rng_mc, universe, mst_obs):
    """Compute the publication analysis for this step."""
    assert method in ALL_METHODS
    if method == 'symbolic' and thresholds is None:
        log.warning('thresholds=None -> symbolize_global() on null.')
    min_common = _effective_min_common(cfg)
    universe = canon_universe(universe)
    obs_weights = sorted([a['weight'] for _, _, a in mst_obs.edges(data=True)])
    m = len(obs_weights)
    df_base = df_ret_snapshot[df_ret_snapshot['Ticker'].isin(universe)][['Fecha', 'Ticker', 'r_log']].dropna(subset=['r_log']).copy()
    sims, null_msts, attempts = ([], [], 0)
    target = cfg.n_link_mc
    max_att = target * cfg.mc_max_attempts_factor
    log.info('MC %s (null=%s): target=%d replicas', method, cfg.mc_null_model, target)
    while len(sims) < target and attempts < max_att:
        attempts += 1
        try:
            df_ret_null = _apply_null_rlog(df_base, cfg.mc_null_model, rng_mc)
            if method in ('mantegna', 'spearman'):
                Dn = mantegna_distance_matrix(df_ret_null, cfg, min_common) if method == 'mantegna' else spearman_distance_matrix(df_ret_null, cfg, min_common)
            else:
                df_sym_null = symbolize_with_thresholds(df_ret_null, thresholds) if thresholds else symbolize_global(df_ret_null, cfg)
                Dn = symbolic_distance_matrix(df_sym_null, cfg, min_common)
            Dn = Dn.loc[universe, universe]
            Dn = drop_isolated_tickers(Dn, cfg.min_valid_peers)
            Dn, keep = force_largest_connected_component(Dn)
            if set(keep) != set(universe):
                continue
            mst_n = build_mst_from_D(Dn)
            null_w = sorted([a['weight'] for _, _, a in mst_n.edges(data=True)])
            if len(null_w) != m:
                continue
            sims.append(null_w)
            null_msts.append(mst_n)
        except Exception:
            continue
    min_valid = max(30, int(0.6 * target))
    if len(sims) < min_valid:
        raise RuntimeError(f'MC {method}: only {len(sims)} valid sims (min {min_valid}).')
    sims_arr = np.array(sims, dtype=float)
    lo = np.quantile(sims_arr, cfg.ci_links[0], axis=0)
    hi = np.quantile(sims_arr, cfg.ci_links[1], axis=0)
    pvals_two = _compute_mc_pvalues_twosided(obs_weights, sims_arr)
    pvals_one = _compute_mc_pvalues_onesided(obs_weights, sims_arr)
    if HAS_STATSMODELS:
        _, pvals_adj_two, _, _ = multipletests(pvals_two, method='fdr_bh')
        _, pvals_adj_one, _, _ = multipletests(pvals_one, method='fdr_bh')
        sig_bh_two = [bool(p <= 0.05) for p in pvals_adj_two]
        sig_bh_one = [bool(p <= 0.05) for p in pvals_adj_one]
    else:
        pvals_adj_two = pvals_two
        pvals_adj_one = pvals_one
        sig_bh_two = [bool(p <= 0.05) for p in pvals_two]
        sig_bh_one = [bool(p <= 0.05) for p in pvals_one]
    null_mean = np.mean(sims_arr, axis=0)
    null_std = np.std(sims_arr, axis=0, ddof=1)
    rows = []
    for k, obs_w in enumerate(obs_weights):
        z = (obs_w - null_mean[k]) / null_std[k] if null_std[k] > 1e-12 else np.nan
        rows.append({'Rank': k + 1, 'Observed': round(float(obs_w), 6), f'CI_{cfg.ci_links[0] * 100:.1f}%': round(float(lo[k]), 6), f'CI_{cfg.ci_links[1] * 100:.1f}%': round(float(hi[k]), 6), 'Null_mean': round(float(null_mean[k]), 6), 'Null_std': round(float(null_std[k]), 6), 'Z_score': round(float(z), 4) if np.isfinite(z) else np.nan, 'pval_twosided': round(float(pvals_two[k]), 5), 'pval_onesided': round(float(pvals_one[k]), 5), 'pval_BH_adj': round(float(pvals_adj_two[k]), 5), 'pval_BH_adj_onesided': round(float(pvals_adj_one[k]), 5), 'Sig_raw': bool(obs_w < lo[k] or obs_w > hi[k]), 'Sig_BH': sig_bh_two[k], 'Sig_BH_onesided': sig_bh_one[k]})
    df_r = pd.DataFrame(rows)
    log.info('MC %s: %d/%d sig BH (two-sided) | %d/%d sig BH (one-sided, H1: observed < null) | %d replicas used', method, int(df_r['Sig_BH'].sum()), m, int(df_r['Sig_BH_onesided'].sum()), m, len(sims))
    jaccard_null = []
    for i in range(min(len(null_msts) - 1, 100)):
        e1 = frozenset((frozenset([u, v]) for u, v in null_msts[i].edges()))
        e2 = frozenset((frozenset([u, v]) for u, v in null_msts[i + 1].edges()))
        un = len(e1 | e2)
        if un > 0:
            jaccard_null.append(len(e1 & e2) / un)
    jaccard_expected = float(np.mean(jaccard_null)) if jaccard_null else np.nan
    log.info('Jaccard expected under H0 (%s): %.4f', method, jaccard_expected)
    return (df_r, jaccard_expected, null_msts)

def edge_bootstrap_support(df_ret_snapshot, thresholds, method, cfg, rng_boot, universe, mst_obs, n_boot=None, block_size=None):
    """Compute the publication analysis for this step."""
    assert method in ALL_METHODS
    if n_boot is None:
        n_boot = cfg.n_link_mc
    min_common = _effective_min_common(cfg)
    universe = canon_universe(universe)
    obs_edges = [(u, v) for u, v, _ in mst_obs.edges(data=True)]
    obs_edge_keys = [frozenset([u, v]) for u, v in obs_edges]
    df_base = df_ret_snapshot[df_ret_snapshot['Ticker'].isin(universe)][['Fecha', 'Ticker', 'r_log']].dropna(subset=['r_log']).copy()
    wide = df_base.pivot(index='Fecha', columns='Ticker', values='r_log').sort_index()
    wide = wide[universe]
    T = len(wide)
    if block_size is None:
        block_size = max(5, round(T ** (1 / 3)))
    block_size = int(min(block_size, T // 2))
    n_blocks_needed = math.ceil(T / block_size)
    dates = wide.index
    support_count = np.zeros(len(obs_edge_keys), dtype=int)
    n_valid = 0
    attempts, max_att = (0, n_boot * cfg.mc_max_attempts_factor)
    while n_valid < n_boot and attempts < max_att:
        attempts += 1
        try:
            start_idx = rng_boot.integers(0, T - block_size + 1, size=n_blocks_needed)
            boot_rows = np.concatenate([np.arange(s, s + block_size) for s in start_idx])[:T]
            wide_boot = wide.iloc[boot_rows].copy()
            wide_boot.index = dates
            df_boot = wide_boot.reset_index().melt(id_vars='Fecha', var_name='Ticker', value_name='r_log').dropna(subset=['r_log'])
            if method in ('mantegna', 'spearman'):
                Db = mantegna_distance_matrix(df_boot, cfg, min_common) if method == 'mantegna' else spearman_distance_matrix(df_boot, cfg, min_common)
            else:
                df_sym_boot = symbolize_with_thresholds(df_boot, thresholds) if thresholds else symbolize_global(df_boot, cfg)
                Db = symbolic_distance_matrix(df_sym_boot, cfg, min_common)
            Db = Db.loc[universe, universe]
            Db = drop_isolated_tickers(Db, cfg.min_valid_peers)
            Db, keep = force_largest_connected_component(Db)
            if set(keep) != set(universe):
                continue
            mst_b = build_mst_from_D(Db)
            boot_edge_keys = {frozenset([u, v]) for u, v in mst_b.edges()}
            for k, ek in enumerate(obs_edge_keys):
                if ek in boot_edge_keys:
                    support_count[k] += 1
            n_valid += 1
        except Exception:
            continue
    if n_valid < max(30, int(0.6 * n_boot)):
        log.warning('edge_bootstrap_support %s: only %d/%d valid replicas.', method, n_valid, n_boot)
    rows = []
    for (u, v), obs_w, cnt in zip(obs_edges, [mst_obs[u][v]['weight'] for u, v in obs_edges], support_count):
        rows.append({'Ticker_i': u, 'Ticker_j': v, 'Sector_i': cfg.sector_map.get(u, 'Other'), 'Sector_j': cfg.sector_map.get(v, 'Other'), 'Observed_weight': round(float(obs_w), 6), 'Bootstrap_support': round(cnt / max(n_valid, 1), 4), 'N_valid_replicas': n_valid})
    df_support = pd.DataFrame(rows).sort_values('Bootstrap_support', ascending=True).reset_index(drop=True)
    log.info('Edge bootstrap support (%s): median=%.3f | min=%.3f (%s-%s) | %d replicas', method, df_support['Bootstrap_support'].median(), df_support['Bootstrap_support'].min(), df_support.iloc[0]['Ticker_i'], df_support.iloc[0]['Ticker_j'], n_valid)
    return df_support

def bootstrap_ci_block(gd, cfg, rng_boot, block_size=None):
    """Block bootstrap CI for rolling NTL series, ALWAYS treating the series
    as I(1) (differences, block-resample, re-integrate; Kuensch 1989).

    This branch is appropriate for an I(1) series and is selected by
    `bootstrap_ntl_by_stationarity` after the ADF/KPSS diagnosis.
    """
    g = gd.dropna()
    vals = g.values.astype(float)
    T = len(vals)
    if T < 20:
        raise RuntimeError(f'NTL too short for bootstrap (T={T}).')
    inc = np.diff(vals)
    n = len(inc)
    if block_size is None:
        block_size = max(5, round(n ** (1 / 3)))
    block_size = int(min(block_size, n // 2))
    blocks = [inc[i:i + block_size] for i in range(n - block_size + 1)]
    n_blocks_needed = math.ceil(n / block_size)
    sims = np.zeros((cfg.n_gd_mc, T), dtype=float)
    sims[:, 0] = vals[0]
    for sim_i in range(cfg.n_gd_mc):
        chosen = rng_boot.integers(0, len(blocks), size=n_blocks_needed)
        inc_boot = np.concatenate([blocks[j] for j in chosen])[:n]
        sims[sim_i, 1:] = vals[0] + np.cumsum(inc_boot)
    lo = np.quantile(sims, cfg.ci_gd[0], axis=0)
    hi = np.quantile(sims, cfg.ci_gd[1], axis=0)
    return (pd.Series(lo, index=g.index), pd.Series(hi, index=g.index))

def _block_bootstrap_levels(vals, n_reps, block_size, rng_boot, ci):
    """Moving block bootstrap directly on LEVELS (appropriate for a
    level-stationary series): resample blocks of the series itself, not of
    its differences."""
    T = len(vals)
    blocks = [vals[i:i + block_size] for i in range(T - block_size + 1)]
    n_blocks_needed = math.ceil(T / block_size)
    sims = np.zeros((n_reps, T), dtype=float)
    for sim_i in range(n_reps):
        chosen = rng_boot.integers(0, len(blocks), size=n_blocks_needed)
        sims[sim_i, :] = np.concatenate([blocks[j] for j in chosen])[:T]
    return (np.quantile(sims, ci[0], axis=0), np.quantile(sims, ci[1], axis=0))

def _block_bootstrap_trend_stationary(vals, n_reps, block_size, rng_boot, ci):
    """Detrend (OLS on a linear time index), block-bootstrap the residuals,
    add the trend back (appropriate for a trend-stationary series)."""
    T = len(vals)
    t_idx = np.arange(T)
    slope, intercept = np.polyfit(t_idx, vals, 1)
    trend = intercept + slope * t_idx
    resid = vals - trend
    lo_r, hi_r = _block_bootstrap_levels(resid, n_reps, block_size, rng_boot, ci)
    return (trend + lo_r, trend + hi_r)

def bootstrap_ntl_by_stationarity(gd, cfg, rng_boot, stationarity_conclusion, block_size=None):
    """Dispatch to the bootstrap scheme appropriate for the ADF/KPSS
    diagnosis (see test_gd_stationarity), instead of unconditionally
    assuming I(1):
      - level_stationary   -> block bootstrap directly on levels
      - trend_stationary   -> detrend, block-bootstrap residuals, re-trend
      - unit_root_I1       -> block bootstrap on first differences
      - anything else (inconclusive / test_incomplete / insufficient_obs)
                           -> falls back to the I(1) scheme, WITH the
                               resulting band explicitly flagged as
                               low-confidence via the returned `scheme` tag,
                               since no specification was confirmed appropriate.
    """
    g = gd.dropna()
    vals = g.values.astype(float)
    T = len(vals)
    if T < 20:
        raise RuntimeError(f'NTL too short for bootstrap (T={T}).')
    if block_size is None:
        block_size = max(5, round(T ** (1 / 3)))
    block_size = int(min(block_size, T // 2))
    concl = (stationarity_conclusion or '').split(' (')[0]
    if concl == 'level_stationary':
        lo, hi = _block_bootstrap_levels(vals, cfg.n_gd_mc, block_size, rng_boot, cfg.ci_gd)
        scheme = 'level_bootstrap'
    elif concl == 'trend_stationary':
        lo, hi = _block_bootstrap_trend_stationary(vals, cfg.n_gd_mc, block_size, rng_boot, cfg.ci_gd)
        scheme = 'detrended_residual_bootstrap'
    elif concl == 'unit_root_I1':
        lo_s, hi_s = bootstrap_ci_block(g, cfg, rng_boot, block_size=block_size)
        lo, hi = (lo_s.values, hi_s.values)
        scheme = 'difference_bootstrap_I1'
    else:
        lo_s, hi_s = bootstrap_ci_block(g, cfg, rng_boot, block_size=block_size)
        lo, hi = (lo_s.values, hi_s.values)
        scheme = 'difference_bootstrap_FALLBACK_inconclusive_diagnosis'
    return (pd.Series(lo, index=g.index), pd.Series(hi, index=g.index), scheme)

def test_gd_stationarity(gd, method, window, cfg):
    """ADF + KPSS stationarity diagnostics for rolling NTL, tested under
    BOTH a level-only specification (regression="c") and a trend
    specification (regression="ct"). Testing only "c" and then labeling an
    inconclusive combination as "trend_stationary" is a category error --
    trend-stationarity can only be assessed by actually including a trend
    term. Running both specifications lets the conclusion distinguish
    level-stationary, trend-stationary, unit-root (I(1)), and genuinely
    inconclusive cases without ambiguity."""
    g = gd.dropna()
    row = {'Method': method, 'Window': window, 'N_obs': len(g), 'ADF_c_stat': np.nan, 'ADF_c_pval': np.nan, 'KPSS_c_stat': np.nan, 'KPSS_c_pval': np.nan, 'ADF_ct_stat': np.nan, 'ADF_ct_pval': np.nan, 'KPSS_ct_stat': np.nan, 'KPSS_ct_pval': np.nan, 'Conclusion': 'statsmodels_not_available'}
    if not HAS_STATSMODELS:
        return pd.DataFrame([row])
    from statsmodels.tsa.stattools import adfuller, kpss
    vals = g.values.astype(float)
    if len(vals) < 20:
        row['Conclusion'] = 'insufficient_obs'
        return pd.DataFrame([row])

    def _run(regression):
        adf_p = kpss_p = adf_s = kpss_s = np.nan
        try:
            r = adfuller(vals, autolag='AIC', regression=regression)
            adf_s, adf_p = (float(r[0]), float(r[1]))
        except Exception:
            pass
        try:
            from statsmodels.tools.sm_exceptions import InterpolationWarning
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=InterpolationWarning)
                r = kpss(vals, regression=regression, nlags='auto')
            kpss_s, kpss_p = (float(r[0]), float(r[1]))
        except Exception:
            pass
        return (adf_s, adf_p, kpss_s, kpss_p)
    adf_c_s, adf_c_p, kpss_c_s, kpss_c_p = _run('c')
    adf_ct_s, adf_ct_p, kpss_ct_s, kpss_ct_p = _run('ct')
    row.update({'ADF_c_stat': round(adf_c_s, 5) if np.isfinite(adf_c_s) else np.nan, 'ADF_c_pval': round(adf_c_p, 6) if np.isfinite(adf_c_p) else np.nan, 'KPSS_c_stat': round(kpss_c_s, 5) if np.isfinite(kpss_c_s) else np.nan, 'KPSS_c_pval': round(kpss_c_p, 6) if np.isfinite(kpss_c_p) else np.nan, 'ADF_ct_stat': round(adf_ct_s, 5) if np.isfinite(adf_ct_s) else np.nan, 'ADF_ct_pval': round(adf_ct_p, 6) if np.isfinite(adf_ct_p) else np.nan, 'KPSS_ct_stat': round(kpss_ct_s, 5) if np.isfinite(kpss_ct_s) else np.nan, 'KPSS_ct_pval': round(kpss_ct_p, 6) if np.isfinite(kpss_ct_p) else np.nan})

    def _classify(adf_p, kpss_p):
        """H0(ADF)=unit root; H0(KPSS)=stationarity (level or trend,
        depending on `regression`). Returns 'stationary', 'unit_root', or
        'inconclusive' for the given specification."""
        if not (np.isfinite(adf_p) and np.isfinite(kpss_p)):
            return 'test_incomplete'
        ar, kr = (adf_p < 0.05, kpss_p < 0.05)
        if ar and (not kr):
            return 'stationary'
        if not ar and kr:
            return 'unit_root'
        return 'inconclusive'
    level_verdict = _classify(row['ADF_c_pval'], row['KPSS_c_pval'])
    trend_verdict = _classify(row['ADF_ct_pval'], row['KPSS_ct_pval'])
    if level_verdict == 'stationary':
        concl = 'level_stationary'
    elif level_verdict == 'unit_root' and trend_verdict == 'stationary':
        concl = 'trend_stationary (non-stationary in levels, stationary around a deterministic trend)'
    elif level_verdict == 'unit_root' and trend_verdict == 'unit_root':
        concl = 'unit_root_I1 (block bootstrap on differences appropriate)'
    else:
        concl = 'inconclusive (level spec: %s; trend spec: %s -- ADF and KPSS disagree; do not over-interpret compression/sync episodes from this series alone)' % (level_verdict, trend_verdict)
    row['Conclusion'] = concl
    return pd.DataFrame([row])
