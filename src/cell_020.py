def _symbolic_dist_pair(a, b, dist_type):
    """Symbolic regime-disagreement distance between two discrete series.
    Used as a pairwise reference helper."""
    if dist_type == 'ordinal':
        return math.sqrt(float(np.mean(np.abs(a.astype(float) - b.astype(float)) / 2.0)))
    return math.sqrt(float(np.mean((a != b).astype(float))))

def symbolic_distance_matrix(df_sym, cfg, min_common):
    """Symbolic regime-disagreement distance matrix.

    Discrete states are one-hot encoded on each jointly valid pairwise support.
    Nominal disagreement or ordinal absolute differences are accumulated with
    matrix products; pairs with fewer than `min_common` observations are set
    to missing."""
    pivot = pivot_panel(df_sym, 'symbol')
    tickers = pivot.columns.tolist()
    n = len(tickers)
    Sv = pivot.astype('float64').values
    valid = ~np.isnan(Sv)
    n_pair = valid.T.astype(float) @ valid.astype(float)
    categories = sorted(pd.unique(Sv[valid]).tolist())
    K = len(categories)
    if K == 0:
        D = np.full((n, n), np.nan)
        np.fill_diagonal(D, 0.0)
        return pd.DataFrame(D, index=tickers, columns=tickers)
    OH = np.zeros((K, Sv.shape[0], n))
    for k, cat in enumerate(categories):
        OH[k] = (Sv == cat) & valid
    if cfg.symbolic_dist_type == 'ordinal':
        total_abs_diff = np.zeros((n, n))
        for k1 in range(K):
            for k2 in range(K):
                if categories[k1] == categories[k2]:
                    continue
                w_k1k2 = abs(categories[k1] - categories[k2])
                total_abs_diff += w_k1k2 * (OH[k1].T @ OH[k2])
        with np.errstate(invalid='ignore', divide='ignore'):
            D = np.sqrt(np.clip(total_abs_diff / n_pair / 2.0, 0.0, None))
    else:
        agree = np.zeros((n, n))
        for k in range(K):
            agree += OH[k].T @ OH[k]
        with np.errstate(invalid='ignore', divide='ignore'):
            D = np.sqrt(np.clip(1.0 - agree / n_pair, 0.0, None))
    D[n_pair < min_common] = np.nan
    np.fill_diagonal(D, 0.0)
    return pd.DataFrame(D, index=tickers, columns=tickers)

def mantegna_distance_matrix(df_ret, cfg, min_common):
    """Mantegna distance d(i,j)=sqrt(2*(1-rho_Pearson)).

    Pearson correlations use pairwise deletion. Joint-valid counts, sums,
    squares, and cross-products are computed with masked matrix products, then
    converted to pair-specific covariance and variance terms."""
    pivot = pivot_panel(df_ret, 'r_log')
    tickers = pivot.columns.tolist()
    Xv = pivot.values.astype(float)
    valid = ~np.isnan(Xv)
    Xz = np.where(valid, Xv, 0.0)
    n_pair = valid.T.astype(float) @ valid.astype(float)
    sum_col_j_over_ij = valid.T.astype(float) @ Xz
    sum_col_i_over_ij = sum_col_j_over_ij.T
    sq_col_j_over_ij = valid.T.astype(float) @ (Xz * Xz)
    sq_col_i_over_ij = sq_col_j_over_ij.T
    cross = Xz.T @ Xz
    with np.errstate(invalid='ignore', divide='ignore'):
        mean_i = sum_col_i_over_ij / n_pair
        mean_j = sum_col_j_over_ij / n_pair
        cov = cross / n_pair - mean_i * mean_j
        var_i = sq_col_i_over_ij / n_pair - mean_i ** 2
        var_j = sq_col_j_over_ij / n_pair - mean_j ** 2
        rho = cov / np.sqrt(var_i * var_j)
    rho = np.clip(rho, -1.0, 1.0)
    D = np.sqrt(np.clip(2.0 * (1.0 - rho), 0.0, None))
    D[n_pair < min_common] = np.nan
    np.fill_diagonal(D, 0.0)
    return pd.DataFrame(D, index=tickers, columns=tickers)

def _spearman_pairloop(pivot, min_common):
    """Exact pairwise-deletion Spearman distance for panels containing
    missing observations."""
    tickers = pivot.columns.tolist()
    n = len(tickers)
    D = np.full((n, n), np.nan)
    np.fill_diagonal(D, 0.0)
    for i, j in combinations(range(n), 2):
        xi, xj = (pivot.iloc[:, i], pivot.iloc[:, j])
        common = xi.notna() & xj.notna()
        if int(common.sum()) < min_common:
            continue
        rho_s, _ = spearmanr(xi[common].values, xj[common].values)
        if not np.isfinite(rho_s):
            continue
        rho_s = float(np.clip(rho_s, -1.0, 1.0))
        D[i, j] = D[j, i] = math.sqrt(max(0.0, 2.0 * (1.0 - rho_s)))
    return pd.DataFrame(D, index=tickers, columns=tickers)

def spearman_distance_matrix(df_ret, cfg, min_common):
    """Spearman distance d(i,j)=sqrt(2*(1-rho_Spearman)).

    Complete panels are ranked column-wise and correlated in matrix form. When
    any values are missing, ranks are recomputed on each pair's jointly valid
    observations so pairwise-deletion semantics are preserved."""
    pivot = pivot_panel(df_ret, 'r_log')
    if pivot.isna().values.any():
        return _spearman_pairloop(pivot, min_common)
    tickers = pivot.columns.tolist()
    Xv = pivot.values.astype(float)
    T_ = Xv.shape[0]
    if T_ < min_common:
        n = len(tickers)
        return pd.DataFrame(np.full((n, n), np.nan), index=tickers, columns=tickers)
    R = np.apply_along_axis(rankdata, 0, Xv)
    Rc = (R - R.mean(axis=0)) / R.std(axis=0, ddof=1)
    rho = Rc.T @ Rc / (T_ - 1)
    rho = np.clip(rho, -1.0, 1.0)
    D = np.sqrt(np.clip(2.0 * (1.0 - rho), 0.0, None))
    np.fill_diagonal(D, 0.0)
    return pd.DataFrame(D, index=tickers, columns=tickers)

def drop_isolated_tickers(D, min_peers):
    valid_peers = D.notna().sum(axis=1) - 1
    keep = valid_peers[valid_peers >= min_peers].index.tolist()
    return D.loc[keep, keep].copy()

def graph_from_distance(D):
    """Construct the weighted complete graph implied by the finite entries
    of a distance matrix."""
    tickers = D.index.tolist()
    n = len(tickers)
    Dv = D.values
    iu, ju = np.triu_indices(n, k=1)
    w = Dv[iu, ju]
    finite = np.isfinite(w)
    G = nx.Graph()
    G.add_nodes_from(tickers)
    for i, j, wij in zip(iu[finite], ju[finite], w[finite]):
        G.add_edge(tickers[i], tickers[j], weight=float(wij))
    return G

def force_largest_connected_component(D):
    G = graph_from_distance(D)
    if G.number_of_nodes() == 0:
        raise RuntimeError('force_lcc: empty graph.')
    comps = list(nx.connected_components(G))
    if len(comps) == 1:
        keep = canon_universe(D.index.tolist())
        return (D.loc[keep, keep].copy(), keep)
    largest = sorted(comps, key=lambda s: len(s), reverse=True)[0]
    keep = canon_universe(list(largest))
    return (D.loc[keep, keep].copy(), keep)
