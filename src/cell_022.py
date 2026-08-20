def build_mst_from_D(D):
    """Compute the publication analysis for this step."""
    tickers = D.index.tolist()
    n = len(tickers)
    Dv = D.values
    iu, ju = np.triu_indices(n, k=1)
    w = Dv[iu, ju]
    finite = np.isfinite(w)
    if not finite.any():
        raise RuntimeError('build_mst: no edges.')
    if np.any(w[finite] == 0.0):
        mst = nx.minimum_spanning_tree(graph_from_distance(D), algorithm='kruskal', weight='weight')
        if mst.number_of_edges() == 0:
            raise RuntimeError('build_mst: no edges.')
        n_nodes, m_edges = (mst.number_of_nodes(), mst.number_of_edges())
        if n_nodes >= 2 and m_edges != n_nodes - 1:
            raise RuntimeError(f'MST is not a tree (|V|={n_nodes}, |E|={m_edges}).')
        return mst
    rows, cols, vals = (iu[finite], ju[finite], w[finite])
    sparse_full = csr_matrix((vals, (rows, cols)), shape=(n, n))
    mst_sparse = scipy_minimum_spanning_tree(sparse_full)
    mst_coo = mst_sparse.tocoo()
    mst = nx.Graph()
    mst.add_nodes_from(tickers)
    for i, j, wij in zip(mst_coo.row, mst_coo.col, mst_coo.data):
        mst.add_edge(tickers[i], tickers[j], weight=float(wij))
    if mst.number_of_edges() == 0:
        raise RuntimeError('build_mst: no edges.')
    n_nodes, m_edges = (mst.number_of_nodes(), mst.number_of_edges())
    if n_nodes >= 2 and m_edges != n_nodes - 1:
        raise RuntimeError(f'MST is not a tree (|V|={n_nodes}, |E|={m_edges}).')
    return mst

def ultrametric_from_mst(mst, nodes):
    """Subdominant ultrametric from MST: d*(i,j) = max edge weight on path."""
    if not nx.is_tree(mst):
        raise RuntimeError('ultrametric: not a tree.')
    nodes = canon_universe(nodes)
    n = len(nodes)
    U = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            path = nx.shortest_path(mst, nodes[i], nodes[j])
            max_w = max((mst[path[k]][path[k + 1]]['weight'] for k in range(len(path) - 1)))
            U[i, j] = U[j, i] = float(max_w)
    return pd.DataFrame(U, index=nodes, columns=nodes)

def build_ht_linkage(U):
    """Build hierarchical tree linkage matrix from ultrametric."""
    nodes = U.index.tolist()
    Uv = U.values.copy()
    if np.isnan(Uv).any():
        Uv = np.nan_to_num(Uv, nan=float(np.nanmax(Uv) * 1.05))
    np.fill_diagonal(Uv, 0.0)
    Z = sp_linkage(squareform(Uv, checks=False), method='single')
    return (Z, nodes)

def cophenetic_correlation(Z, D, nodes):
    """Compute the publication analysis for this step."""
    nodes_c = canon_universe(nodes)
    D_al = D.loc[nodes_c, nodes_c].values.copy()
    np.fill_diagonal(D_al, 0.0)
    d_cond = squareform(D_al, checks=False)
    coph_cond = cophenet(Z)
    finite = np.isfinite(d_cond)
    n_dropped = int((~finite).sum())
    if n_dropped > 0:
        log.warning('cophenetic_correlation: excluding %d/%d pairs with non-finite original distance (no imputation).', n_dropped, len(d_cond))
    if finite.sum() < 2:
        return float('nan')
    c = float(np.corrcoef(d_cond[finite], coph_cond[finite])[0, 1])
    return c

def select_fixed_universe_snapshot(df_ret, df_sym_global, cfg, method):
    """Build snapshot distance matrix and MST for a given method."""
    min_common = _effective_min_common(cfg)
    if method == 'symbolic':
        D = symbolic_distance_matrix(df_sym_global, cfg, min_common)
    elif method == 'mantegna':
        D = mantegna_distance_matrix(df_ret, cfg, min_common)
    elif method == 'spearman':
        D = spearman_distance_matrix(df_ret, cfg, min_common)
    else:
        raise ValueError(f'Unknown method: {method}')
    D = drop_isolated_tickers(D, cfg.min_valid_peers)
    D, universe = force_largest_connected_component(D)
    universe = canon_universe(universe)
    D = D.loc[universe, universe].copy()
    return (universe, D, build_mst_from_D(D))
