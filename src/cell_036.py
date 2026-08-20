def _vectorize_upper(M: np.ndarray) -> np.ndarray:
    n = M.shape[0]
    iu = np.triu_indices(n, k=1)
    return M[iu]

def _ols_coef(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    """OLS coefficients (intercept first) for y ~ X. X has no intercept column."""
    X1 = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    return beta

def _vif(X: np.ndarray) -> np.ndarray:
    """Variance Inflation Factor per column of X (predictors only, no intercept).
    Reported as a collinearity diagnostic alongside every MRQAP result --
    DSP-MRQAP corrects the SIGNIFICANCE inference under collinearity, it
    does not remove the collinearity itself, so individual coefficient
    magnitudes should still be read cautiously when VIF is large."""
    p = X.shape[1]
    vifs = np.full(p, np.nan)
    for j in range(p):
        y = X[:, j]
        others = np.delete(X, j, axis=1)
        if others.shape[1] == 0:
            vifs[j] = 1.0
            continue
        X1 = np.column_stack([np.ones(len(y)), others])
        beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
        yhat = X1 @ beta
        ss_res = np.sum((y - yhat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        vifs[j] = 1.0 / (1.0 - r2) if r2 < 0.9999 else np.inf
    return vifs

def _permute_matrix_nodes(M: np.ndarray, perm: np.ndarray) -> np.ndarray:
    return M[np.ix_(perm, perm)]

def _t_stat_for_predictor(y: np.ndarray, X_mat: np.ndarray, target_col_idx: int) -> float:
    """OLS t-statistic for one column of X_mat (0-indexed among predictors,
    intercept handled internally). Used as the pivotal test statistic for
    both mrqap_dsp and mrqap_freedman_lane -- Dekker, Krackhardt & Snijders
    (2007) report that MRQAP methods perform better with pivotal statistics
    (t/F) than with raw regression coefficients."""
    n = X_mat.shape[0]
    X1 = np.column_stack([np.ones(n), X_mat])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    resid = y - X1 @ beta
    dof = n - X1.shape[1]
    if dof <= 0:
        return np.nan
    sigma2 = np.sum(resid ** 2) / dof
    XtX_inv = np.linalg.pinv(X1.T @ X1)
    se2 = sigma2 * XtX_inv[target_col_idx + 1, target_col_idx + 1]
    return beta[target_col_idx + 1] / np.sqrt(se2) if se2 > 0 else np.nan

def mrqap_dsp(Y: np.ndarray, X_dict: Dict[str, np.ndarray], n_perm: int, rng: np.random.Generator) -> pd.DataFrame:
    """Run Double Semi-Partialling MRQAP using node-label permutations."""
    names = list(X_dict.keys())
    n = Y.shape[0]
    y_vec = _vectorize_upper(Y)
    X_vecs = {k: _vectorize_upper(v) for k, v in X_dict.items()}
    X_mat_full = np.column_stack([X_vecs[k] for k in names])
    beta_obs = _ols_coef(y_vec, X_mat_full)[1:]
    vifs = _vif(X_mat_full)
    p_values = np.zeros(len(names))
    obs_ts = np.zeros(len(names))
    null_dists = {}
    iu = np.triu_indices(n, k=1)
    for k_idx, k in enumerate(names):
        others = [names[j] for j in range(len(names)) if j != k_idx]
        if others:
            X_others = np.column_stack([X_vecs[o] for o in others])
            beta_xk = _ols_coef(X_vecs[k], X_others)
            xk_resid_vec = X_vecs[k] - np.column_stack([np.ones(len(X_vecs[k])), X_others]) @ beta_xk
        else:
            xk_resid_vec = X_vecs[k] - X_vecs[k].mean()
        obs_t = _t_stat_for_predictor(y_vec, X_mat_full, k_idx)
        obs_ts[k_idx] = obs_t
        xk_resid_mat = np.zeros((n, n))
        xk_resid_mat[iu] = xk_resid_vec
        xk_resid_mat = xk_resid_mat + xk_resid_mat.T
        null_ts = np.empty(n_perm)
        for b in range(n_perm):
            perm = rng.permutation(n)
            xk_perm_vec = _vectorize_upper(_permute_matrix_nodes(xk_resid_mat, perm))
            X_mat_perm = X_mat_full.copy()
            X_mat_perm[:, k_idx] = xk_perm_vec
            null_ts[b] = _t_stat_for_predictor(y_vec, X_mat_perm, k_idx)
        p_values[k_idx] = (int(np.sum(np.abs(null_ts) >= abs(obs_t))) + 1) / (n_perm + 1)
        null_dists[k] = null_ts
    df_out = pd.DataFrame({'Predictor': names, 'Beta': beta_obs, 't_obs': obs_ts, 'VIF': vifs, 'pval_DSP': p_values})
    df_out.attrs['null_distributions'] = null_dists
    return df_out

def mrqap_freedman_lane(Y: np.ndarray, X_dict: Dict[str, np.ndarray], n_perm: int, rng: np.random.Generator) -> pd.DataFrame:
    """Run Freedman-Lane MRQAP as a robustness check."""
    names = list(X_dict.keys())
    n = Y.shape[0]
    y_vec = _vectorize_upper(Y)
    X_vecs = {k: _vectorize_upper(v) for k, v in X_dict.items()}
    X_mat = np.column_stack([X_vecs[k] for k in names])
    beta_obs = _ols_coef(y_vec, X_mat)[1:]
    obs_ts = np.array([_t_stat_for_predictor(y_vec, X_mat, k) for k in range(len(names))])
    p_values = np.zeros(len(names))
    iu = np.triu_indices(n, k=1)
    for k_idx, k in enumerate(names):
        others = [names[j] for j in range(len(names)) if j != k_idx]
        if others:
            X_others = np.column_stack([X_vecs[o] for o in others])
            beta_reduced = _ols_coef(y_vec, X_others)
            yhat_reduced = np.column_stack([np.ones(len(y_vec)), X_others]) @ beta_reduced
        else:
            yhat_reduced = np.full(len(y_vec), y_vec.mean())
        resid_reduced = y_vec - yhat_reduced
        resid_mat = np.zeros((n, n))
        resid_mat[iu] = resid_reduced
        resid_mat += resid_mat.T
        yhat_mat = np.zeros((n, n))
        yhat_mat[iu] = yhat_reduced
        yhat_mat += yhat_mat.T
        null_ts = np.empty(n_perm)
        for b in range(n_perm):
            perm = rng.permutation(n)
            y_star_vec = _vectorize_upper(yhat_mat + _permute_matrix_nodes(resid_mat, perm))
            null_ts[b] = _t_stat_for_predictor(y_star_vec, X_mat, k_idx)
        obs_t = obs_ts[k_idx]
        p_values[k_idx] = (int(np.sum(np.abs(null_ts) >= abs(obs_t))) + 1) / (n_perm + 1)
    return pd.DataFrame({'Predictor': names, 'Beta': beta_obs, 't_obs': obs_ts, 'pval_FreedmanLane': p_values})

def symbolic_non_redundancy_test(D_sym, D_mantegna, D_spearman, cfg, universe, rng, n_perm=1000):
    """Estimate the manuscript MRQAP specifications for symbolic distance."""
    universe = canon_universe(universe)
    n = len(universe)
    same_sector = np.zeros((n, n))
    for i, ti in enumerate(universe):
        for j, tj in enumerate(universe):
            if i != j and cfg.sector_map.get(ti, 'Other') == cfg.sector_map.get(tj, 'Other'):
                same_sector[i, j] = 1.0
    Y = D_sym.loc[universe, universe].values
    Xm = D_mantegna.loc[universe, universe].values
    Xs = D_spearman.loc[universe, universe].values
    specs = {'A_mantegna_only': {'Mantegna': Xm, 'SameSector': same_sector}, 'B_spearman_only': {'Spearman': Xs, 'SameSector': same_sector}, 'C_joint': {'Mantegna': Xm, 'Spearman': Xs, 'SameSector': same_sector}}
    roles = {'A_mantegna_only': 'sensitivity', 'B_spearman_only': 'sensitivity', 'C_joint': 'focal_primary'}
    results = {}
    for spec_name, X_dict in specs.items():
        results[spec_name] = {'dsp': mrqap_dsp(Y, X_dict, n_perm, rng), 'freedman_lane': mrqap_freedman_lane(Y, X_dict, n_perm, rng)}
        for key in ('dsp', 'freedman_lane'):
            results[spec_name][key] = results[spec_name][key].copy()
            results[spec_name][key]['Hypothesis_role'] = roles[spec_name]
    if HAS_STATSMODELS and 'C_joint' in results:
        from statsmodels.stats.multitest import multipletests
        df_c_dsp = results['C_joint']['dsp']
        _, pvals_bh, _, _ = multipletests(df_c_dsp['pval_DSP'].values, method='fdr_bh')
        df_c_dsp['pval_DSP_BH'] = pvals_bh
        df_c_fl = results['C_joint']['freedman_lane']
        _, pvals_bh_fl, _, _ = multipletests(df_c_fl['pval_FreedmanLane'].values, method='fdr_bh')
        df_c_fl['pval_FreedmanLane_BH'] = pvals_bh_fl
    return results

def symbolic_residual_analysis(D_sym, D_mantegna, D_spearman, cfg, universe, rng, n_perm=1000, sector_map_override=None, sector_label='custom'):
    """Test sector structure in symbolic-distance residuals after conventional distances."""
    universe = canon_universe(universe)
    n = len(universe)
    smap = sector_map_override if sector_map_override is not None else cfg.sector_map
    same_sector = np.zeros((n, n))
    for i, ti in enumerate(universe):
        for j, tj in enumerate(universe):
            if i != j and smap.get(ti, 'Other') == smap.get(tj, 'Other'):
                same_sector[i, j] = 1.0
    Y = D_sym.loc[universe, universe].values
    X_dict = {'Mantegna': D_mantegna.loc[universe, universe].values, 'Spearman': D_spearman.loc[universe, universe].values}
    y_vec = _vectorize_upper(Y)
    X_mat = np.column_stack([_vectorize_upper(v) for v in X_dict.values()])
    beta = _ols_coef(y_vec, X_mat)
    yhat = np.column_stack([np.ones(len(y_vec)), X_mat]) @ beta
    resid_vec = y_vec - yhat
    r2 = 1 - np.sum((y_vec - yhat) ** 2) / np.sum((y_vec - y_vec.mean()) ** 2)
    same_sector_vec = _vectorize_upper(same_sector)
    resid_same = resid_vec[same_sector_vec == 1]
    resid_diff = resid_vec[same_sector_vec == 0]
    obs_diff = float(np.mean(resid_same) - np.mean(resid_diff)) if len(resid_same) and len(resid_diff) else np.nan
    n_nodes = Y.shape[0]
    iu = np.triu_indices(n_nodes, k=1)
    resid_mat = np.zeros((n_nodes, n_nodes))
    resid_mat[iu] = resid_vec
    resid_mat += resid_mat.T
    null_diffs = np.empty(n_perm)
    for b in range(n_perm):
        perm = rng.permutation(n_nodes)
        ss_perm_vec = _vectorize_upper(_permute_matrix_nodes(same_sector, perm))
        rs = resid_vec[ss_perm_vec == 1]
        rd = resid_vec[ss_perm_vec == 0]
        null_diffs[b] = np.mean(rs) - np.mean(rd) if len(rs) and len(rd) else np.nan
    valid = np.isfinite(null_diffs)
    p_val = (int(np.sum(np.abs(null_diffs[valid]) >= abs(obs_diff))) + 1) / (int(valid.sum()) + 1) if np.isfinite(obs_diff) else np.nan
    verdict = 'incremental_information (residual still tracks sector structure)' if np.isfinite(p_val) and p_val < 0.05 else 'non_redundant_only (residual does not show detectable additional economic structure)'
    df_result = pd.DataFrame([{'R2_mantegna_spearman_only': round(float(r2), 4), 'residual_sameSector_meanDiff': round(obs_diff, 6) if np.isfinite(obs_diff) else np.nan, 'residual_sameSector_pval': round(p_val, 6) if np.isfinite(p_val) else np.nan, 'N_perm': n_perm, 'Verdict': verdict}])
    df_result.attrs['resid_vec'] = resid_vec
    df_result.attrs['same_sector_vec'] = same_sector_vec
    return df_result

def plot_mrqap_null_distribution(dsp_df, predictor, cfg, spec_name, path):
    """Histogram of the DSP null t-statistic distribution for one focal
    predictor, with the observed t-statistic marked -- makes the p-value
    reported in mrqap_dsp_{spec}.csv visually concrete, following the same
    visual convention as plot_mc_significance elsewhere in this pipeline."""
    null_dists = dsp_df.attrs.get('null_distributions', {})
    if predictor not in null_dists:
        log.warning('plot_mrqap_null_distribution: no null distribution stored for %s (mrqap_dsp must be called directly, not reloaded from CSV).', predictor)
        return
    null_ts = null_dists[predictor]
    row = dsp_df[dsp_df['Predictor'] == predictor].iloc[0]
    obs_t, pval = (row['t_obs'], row['pval_DSP'])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(null_ts, bins=40, color='#9E9E9E', alpha=0.7, label=f'DSP null (n={len(null_ts)})')
    ax.axvline(obs_t, color='#B71C1C', lw=2.2, label=f'Observed t = {obs_t:.2f}')
    ax.axvline(-obs_t, color='#B71C1C', lw=1.0, ls='--', alpha=0.6)
    ax.set_xlabel('t-statistic (permutation null)', fontsize=9)
    ax.set_ylabel('Count', fontsize=9)
    ax.set_title(f'DSP-MRQAP null distribution — {predictor} ({spec_name}) | p={pval:.4f}', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    plt.tight_layout()
    _save_fig(fig, path, cfg)

def plot_mrqap_coefficients(dsp_df, cfg, spec_name, path):
    """Coefficient/significance summary bar chart for one MRQAP
    specification -- the standard "regression table as a figure" view,
    with BH-adjusted significance (when present) marked."""
    fig, ax = plt.subplots(figsize=(8, 5))
    preds = dsp_df['Predictor'].tolist()
    betas = dsp_df['Beta'].values
    has_bh = 'pval_DSP_BH' in dsp_df.columns
    pvals = (dsp_df['pval_DSP_BH'] if has_bh else dsp_df['pval_DSP']).values
    colors = ['#1B5E20' if p < 0.05 else '#B71C1C' for p in pvals]
    bars = ax.barh(preds, betas, color=colors, alpha=0.85)
    for bar, p in zip(bars, pvals):
        marker = '*' if p < 0.05 else 'ns'
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f'  {marker} (p={p:.3f})', va='center', fontsize=8)
    ax.axvline(0, color='black', lw=0.8)
    ax.set_xlabel('DSP-MRQAP coefficient (Beta)', fontsize=9)
    label = 'BH-adjusted p' if has_bh else 'raw p'
    ax.set_title(f'MRQAP coefficients — {spec_name} ({label})', fontsize=11, fontweight='bold')
    plt.tight_layout()
    _save_fig(fig, path, cfg)

def plot_symbolic_residuals_by_sector(df_residual, cfg, path):
    """Boxplot of the Symbolic~Mantegna+Spearman residuals, split by
    same-sector vs. different-sector pairs -- the visual counterpart of
    symbolic_residual_analysis's formal test: if the boxes visibly
    separate, that is the "incremental information" signal made concrete;
    if they overlap heavily, that supports "non-redundant only"."""
    resid_vec = df_residual.attrs.get('resid_vec')
    same_sector_vec = df_residual.attrs.get('same_sector_vec')
    if resid_vec is None:
        log.warning('plot_symbolic_residuals_by_sector: residuals not attached (symbolic_residual_analysis must be called directly, not reloaded from CSV).')
        return
    resid_same = resid_vec[same_sector_vec == 1]
    resid_diff = resid_vec[same_sector_vec == 0]
    fig, ax = plt.subplots(figsize=(7, 5))
    bp = ax.boxplot([resid_same, resid_diff], labels=['Same sector', 'Different sector'], patch_artist=True, widths=0.5)
    for patch, color in zip(bp['boxes'], ['#1565C0', '#9E9E9E']):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.axhline(0, color='black', lw=0.8, ls='--')
    verdict = df_residual['Verdict'].iloc[0]
    pval = df_residual['residual_sameSector_pval'].iloc[0]
    ax.set_ylabel('Symbolic residual (Mantegna+Spearman removed)', fontsize=9)
    ax.set_title(f'Symbolic residual by sector pairing | p={pval:.4f}\n{verdict}', fontsize=10, fontweight='bold')
    plt.tight_layout()
    _save_fig(fig, path, cfg)
