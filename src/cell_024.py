def global_distance(mst):
    return float(sum((a['weight'] for _, _, a in mst.edges(data=True))))

def global_distance_norm(mst):
    """Normalized Tree Length (NTL) = GD / (N-1). Order parameter."""
    n = mst.number_of_nodes()
    return np.nan if n <= 1 else global_distance(mst) / (n - 1)

def average_path_length_topo(mst):
    """Average shortest path length in hops (unweighted)."""
    return nx.average_shortest_path_length(mst, weight=None)

def average_path_length_weighted(mst):
    """Average shortest path length using edge weights."""
    return nx.average_shortest_path_length(mst, weight='weight')

def tree_diameter_topo(mst):
    """Topological diameter (max hops between any pair)."""
    return nx.diameter(mst)

def tree_diameter_weighted(mst):
    """Weighted diameter (max weighted distance between any pair)."""
    lengths = dict(nx.all_pairs_dijkstra_path_length(mst, weight='weight'))
    return max((max(d.values()) for d in lengths.values()))

def degree_assortativity(mst):
    """Degree assortativity coefficient. Negative = disassortative (hub-spoke)."""
    return nx.degree_assortativity_coefficient(mst)

def degree_entropy(mst):
    """Shannon entropy of the degree distribution (bits)."""
    deg_seq = [d for _, d in mst.degree()]
    freq = np.array(list(Counter(deg_seq).values()), dtype=float)
    freq = freq / freq.sum()
    return float(-np.sum(freq * np.log2(freq + 1e-15)))

def topological_metrics(mst):
    """Compute all topological metrics for a given MST. Returns dict."""
    return {'NTL': round(global_distance_norm(mst), 6), 'APL_topo': round(average_path_length_topo(mst), 4), 'APL_weighted': round(average_path_length_weighted(mst), 4), 'Diameter_topo': tree_diameter_topo(mst), 'Diameter_weighted': round(tree_diameter_weighted(mst), 4), 'Assortativity': round(degree_assortativity(mst), 4), 'Degree_entropy': round(degree_entropy(mst), 4)}

def mst_edge_table(mst, sector_map):
    rows = []
    for k, (u, v, d) in enumerate(sorted(mst.edges(data=True), key=lambda e: e[2]['weight']), 1):
        rows.append({'Link': k, 'Ticker_i': u, 'Sector_i': sector_map.get(u, 'Other'), 'Ticker_j': v, 'Sector_j': sector_map.get(v, 'Other'), 'Distance': round(float(d['weight']), 6), 'Same_sector': sector_map.get(u, 'Other') == sector_map.get(v, 'Other')})
    return pd.DataFrame(rows)

def select_hub(mst):
    """Select the MST's hub (highest-degree node), breaking ties
    explicitly instead of silently picking whichever node happens to come
    first in networkx's internal iteration order (which is what
    `max(mst.degree(), key=lambda x: x[1])` does on a tie -- an artifact
    of insertion order, not a meaningful criterion).

    Tie-break order: (1) highest degree, (2) highest betweenness
    centrality among degree-tied nodes, (3) alphabetical ticker order as a
    final deterministic fallback. Returns (hub_ticker, hub_degree,
    was_tied, co_hub_tickers) -- was_tied and co_hub_tickers let callers
    report/inspect ties rather than silently hiding them.
    """
    degrees = dict(mst.degree())
    if not degrees:
        raise RuntimeError('select_hub: empty graph.')
    max_deg = max(degrees.values())
    co_hubs = sorted((n for n, d in degrees.items() if d == max_deg))
    was_tied = len(co_hubs) > 1
    if was_tied:
        btw = nx.betweenness_centrality(mst, weight='weight', normalized=True)
        hub_ticker = sorted(co_hubs, key=lambda n: (-btw.get(n, 0.0), n))[0]
    else:
        hub_ticker = co_hubs[0]
    return (hub_ticker, max_deg, was_tied, co_hubs)

def mst_degree_table(mst, sector_map):
    return pd.DataFrame([{'Ticker': n, 'Sector': sector_map.get(n, 'Other'), 'Degree': int(d)} for n, d in sorted(mst.degree(), key=lambda x: x[1], reverse=True)])

def betweenness_centrality_table(mst, sector_map):
    bc = nx.betweenness_centrality(mst, normalized=True)
    rows = [{'Ticker': t, 'Sector': sector_map.get(t, 'Other'), 'Betweenness': round(v, 4), 'Degree': int(mst.degree(t))} for t, v in sorted(bc.items(), key=lambda x: x[1], reverse=True)]
    return pd.DataFrame(rows)

def _random_labeled_tree_degrees(n: int, rng: np.random.Generator) -> np.ndarray:
    """Degree sequence of a uniformly random labeled tree on n nodes, drawn
    via a uniformly random Pruefer sequence (length n-2, i.i.d. uniform over
    the n labels). Every labeled tree on n nodes corresponds to exactly one
    Pruefer sequence, so this samples the uniform distribution over labeled
    trees exactly -- this is the correct reference distribution for "is this
    MST's degree sequence consistent with a random tree", not a Poisson
    approximation."""
    if n <= 2:
        return np.full(max(n, 1), 1.0)
    seq = rng.integers(0, n, size=n - 2)
    deg = np.ones(n, dtype=int)
    counts = np.bincount(seq, minlength=n)
    deg += counts
    return deg

def _topology_stats(mst):
    degrees = np.array([d for _, d in mst.degree()])
    n = mst.number_of_nodes()
    max_deg = int(degrees.max())
    counts = np.bincount(degrees)
    p = counts[counts > 0] / n
    entropy = float(-np.sum(p * np.log2(p)))
    return (max_deg, entropy)

def _holm_correction(pvals, alpha=0.05):
    """Compute the publication analysis for this step."""
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj_p = min(1.0, (m - rank) * pvals[idx])
        running_max = max(running_max, adj_p)
        adj[idx] = running_max
    return (adj, bool(np.any(adj < alpha)))

def degree_distribution_test(mst, null_msts=None, rng: np.random.Generator=None, n_null: int=10000):
    """Test of the MST's topology (max degree, degree entropy) against two
    reference null models:

    PRIMARY -- `null_msts` (if provided): actual MST objects built under
    the SAME cross-sectional-independence null used for the edge-length
    order-statistic test (see mst_edge_length_order_statistic_test). This
    is a genuine "random MST built from i.i.d.-null return data" null and
    is the scientifically appropriate reference for "is this backbone's
    hub structure unusual given the data" -- NOT a Uniform Spanning Tree.

    SECONDARY -- Pruefer-sequence uniform labeled tree (always computed,
    reported for reference/comparability with the purely combinatorial
    "any labeled tree equally likely" baseline). A Uniform Spanning Tree
    and a random Minimum Spanning Tree built from i.i.d. edge weights on
    the complete graph are DIFFERENT probability distributions over
    labeled trees (see e.g. Babson et al., "Models of Random Spanning
    Trees", Random Structures & Algorithms, 2026) -- this null answers a
    different, weaker question ("unusual vs. a combinatorially uniform
    tree") and should not be reported as the paper's primary
    "Rejects_random_tree" conclusion when the data-driven null is available.

    Multiple-testing note: max degree and entropy are combined into a
    single Rejects_random_tree decision via Holm-Bonferroni (not two
    independent 5% tests, which would inflate the family-wise error rate).
    """
    if rng is None:
        rng = np.random.default_rng(0)
    n = mst.number_of_nodes()
    obs_max_deg, obs_entropy = _topology_stats(mst)
    out = {'N_nodes': n, 'Max_degree': obs_max_deg, 'Mean_degree': round(float(np.mean([d for _, d in mst.degree()])), 2), 'Degree_entropy': round(obs_entropy, 4)}
    if null_msts:
        pn_max = np.array([_topology_stats(m)[0] for m in null_msts])
        pn_ent = np.array([_topology_stats(m)[1] for m in null_msts])
        p_maxdeg_primary = (int(np.sum(pn_max >= obs_max_deg)) + 1) / (len(pn_max) + 1)
        p_entropy_primary = (int(np.sum(pn_ent <= obs_entropy)) + 1) / (len(pn_ent) + 1)
        adj_p, rejects_primary = _holm_correction(np.array([p_maxdeg_primary, p_entropy_primary]))
        out.update({'Primary_null_model': 'empirical random-MST null (independence-permutation data)', 'Primary_N_null_reps': len(null_msts), 'Primary_null_max_degree_mean': round(float(pn_max.mean()), 3), 'pval_max_degree_primary_holm': round(float(adj_p[0]), 6), 'pval_entropy_primary_holm': round(float(adj_p[1]), 6), 'Rejects_random_tree': rejects_primary})
    else:
        out.update({'Primary_null_model': 'NOT PROVIDED -- pass null_msts from mst_edge_length_order_statistic_test for the correct primary test', 'pval_max_degree_primary_holm': np.nan, 'pval_entropy_primary_holm': np.nan, 'Rejects_random_tree': None})
    null_max_deg = np.empty(n_null)
    null_entropy = np.empty(n_null)
    for b in range(n_null):
        d = _random_labeled_tree_degrees(n, rng)
        null_max_deg[b] = d.max()
        counts = np.bincount(d)
        p = counts[counts > 0] / n
        null_entropy[b] = -np.sum(p * np.log2(p))
    p_maxdeg_sec = (int(np.sum(null_max_deg >= obs_max_deg)) + 1) / (n_null + 1)
    p_entropy_sec = (int(np.sum(null_entropy <= obs_entropy)) + 1) / (n_null + 1)
    adj_p_sec, rejects_sec = _holm_correction(np.array([p_maxdeg_sec, p_entropy_sec]))
    out.update({'Secondary_null_model': 'uniform random labeled tree (Pruefer sequence MC) -- combinatorial baseline only', 'Secondary_N_null_reps': n_null, 'pval_max_degree_secondary_holm': round(float(adj_p_sec[0]), 6), 'pval_entropy_secondary_holm': round(float(adj_p_sec[1]), 6), 'Rejects_uniform_labeled_tree': rejects_sec})
    return pd.DataFrame([out])
