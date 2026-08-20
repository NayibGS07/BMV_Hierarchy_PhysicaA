def _pairwise_convergence(mst_a, mst_b, D_a, D_b, name_a, name_b, universe, gd_a=None, gd_b=None):
    """Compute the publication analysis for this step."""
    universe = canon_universe(universe)
    nodes_a, nodes_b = (set(mst_a.nodes()), set(mst_b.nodes()))
    same_node_set = nodes_a == nodes_b
    common_nodes = nodes_a & nodes_b
    es_a = frozenset((frozenset([u, v]) for u, v in mst_a.edges() if u in common_nodes and v in common_nodes))
    es_b = frozenset((frozenset([u, v]) for u, v in mst_b.edges() if u in common_nodes and v in common_nodes))
    inter, un = (len(es_a & es_b), len(es_a | es_b))
    jaccard = inter / un if un > 0 else np.nan
    try:
        tb = [t for t in universe if t in D_a.index and t in D_b.index]
        Da, Db = (D_a.loc[tb, tb].values, D_b.loc[tb, tb].values)
        idx = np.triu_indices_from(Da, k=1)
        fa, fb = (Da[idx], Db[idx])
        valid = np.isfinite(fa) & np.isfinite(fb)
        corr_d, _ = pearsonr(fa[valid], fb[valid]) if valid.sum() > 2 else (np.nan, np.nan)
    except Exception:
        corr_d = np.nan
    corr_gd = np.nan
    if gd_a is not None and gd_b is not None:
        c = pd.DataFrame({'a': gd_a, 'b': gd_b}).dropna()
        if len(c) > 10:
            corr_gd, _ = pearsonr(c['a'].values, c['b'].values)
    hub_a_ticker, hub_a_degree, _, _ = select_hub(mst_a)
    hub_b_ticker, hub_b_degree, _, _ = select_hub(mst_b)
    return {'Pair': f'{name_a} vs {name_b}', 'Same_node_set': same_node_set, 'N_common_nodes': len(common_nodes), 'Jaccard': round(float(jaccard), 4) if np.isfinite(jaccard) else np.nan, 'Corr_matrices': round(float(corr_d), 4) if np.isfinite(corr_d) else np.nan, f'Hub_{name_a}': f'{hub_a_ticker} (g={hub_a_degree})', f'Hub_{name_b}': f'{hub_b_ticker} (g={hub_b_degree})', 'Hubs_match': hub_a_ticker == hub_b_ticker, 'Corr_NTL_rolling': round(float(corr_gd), 4) if np.isfinite(corr_gd) else np.nan}

def convergence_table_3way(snapshot, gd_series, universe_all):
    """3x3 convergence table for all method pairs."""
    pairs = [('mantegna', 'symbolic'), ('mantegna', 'spearman'), ('spearman', 'symbolic')]
    rows = []
    for na, nb in pairs:
        if na not in snapshot or nb not in snapshot:
            continue
        _, D_a, mst_a = snapshot[na]
        _, D_b, mst_b = snapshot[nb]
        gd_a = gd_series.get(na)
        gd_b = gd_series.get(nb)
        rows.append(_pairwise_convergence(mst_a, mst_b, D_a, D_b, na, nb, universe_all, gd_a, gd_b))
    return pd.DataFrame(rows)
