def run_pipeline(cfg: Config = CFG):
    """Run the publication-focused reproducibility pipeline.

    Raw third-party inputs are acquired at runtime and are not part of the
    public repository. The function writes derived tables/figures to
    ``cfg.out_dir`` and returns the main in-memory objects for inspection.
    """
    ensure_dir(cfg.out_dir)
    rngs = make_rngs(cfg.seed)
    write_manifest(cfg, rngs, os.path.join(cfg.out_dir, 'manifest.json'))

    # Data, coverage, returns and descriptive statistics.
    df_prices, provenance = download_prices(cfg)
    safe_write_csv(provenance, os.path.join(cfg.out_dir, 'data_provenance.csv'))
    df_prices, coverage = filter_by_coverage(df_prices, cfg)
    safe_write_csv(coverage, os.path.join(cfg.out_dir, 'ticker_coverage.csv'))
    df_ret = null_splice_transition_returns(compute_log_returns(df_prices))
    stats = compute_descriptive_stats(df_ret, cfg)
    safe_write_csv(stats, os.path.join(cfg.out_dir, 'descriptive_stats.csv'))

    # Symbolic representation and three snapshot dependence structures.
    df_sym = symbolize_global(df_ret, cfg)
    thresholds = compute_symbol_thresholds(df_ret, cfg)
    snapshot, topo_rows = {}, []
    for method in ALL_METHODS:
        universe, D, mst = select_fixed_universe_snapshot(df_ret, df_sym, cfg, method)
        snapshot[method] = (universe, D, mst)
        D.to_csv(os.path.join(cfg.out_dir, f'D_{method}_snapshot.csv'))
        safe_write_csv(mst_edge_table(mst, cfg.sector_map),
                       os.path.join(cfg.out_dir, f'edges_{method}.csv'))
        row = topological_metrics(mst)
        hub, degree, tied, _ = select_hub(mst)
        row.update(Method=method, N_nodes=mst.number_of_nodes(),
                   N_edges=mst.number_of_edges(), Hub=hub,
                   Hub_degree=degree, Hub_tied=tied)
        topo_rows.append(row)
        U = ultrametric_from_mst(mst, universe)
        Z, nodes = build_ht_linkage(U)
        coph = cophenetic_correlation(Z, D, nodes)
        safe_write_csv(pd.DataFrame([{'Method': method, 'r_cophenetic': coph}]),
                       os.path.join(cfg.out_dir, f'cophenetic_{method}.csv'))
        plot_mst(mst, cfg, f'MST {method} — BMV {cfg.start[:4]}–{cfg.end_display_year}',
                 os.path.join(cfg.out_dir, f'mst_{method}.pdf'), coph)
        plot_ht(Z, nodes, cfg, f'HT {method} — BMV {cfg.start[:4]}–{cfg.end_display_year}',
                os.path.join(cfg.out_dir, f'ht_{method}.pdf'), coph)
    topology = pd.DataFrame(topo_rows)
    safe_write_csv(topology, os.path.join(cfg.out_dir, 'snapshot_topology.csv'))

    # Primary permutation null and weaker circular-shift null.
    null_summary, null_msts = [], {}
    for null_name in ('permutation', 'circular_shift'):
        cfg_null = replace(cfg, mc_null_model=null_name)
        null_msts[null_name] = {}
        for method in ALL_METHODS:
            universe, _, mst = snapshot[method]
            th = {t: thresholds[t] for t in universe if t in thresholds} if method == 'symbolic' else None
            mc, j0, nm = mst_edge_length_order_statistic_test(
                df_ret, th, method, cfg_null,
                derive_rng(rngs, 'mc', null_name, method), universe, mst)
            safe_write_csv(mc, os.path.join(cfg.out_dir, f'mc_{null_name}_{method}.csv'))
            null_msts[null_name][method] = nm
            deg = degree_distribution_test(
                mst, null_msts=nm,
                rng=derive_rng(rngs, 'degree', null_name, method),
                n_null=cfg.n_gd_mc)
            deg['Primary_null_model'] = f'empirical random-MST null ({null_name} data)'
            safe_write_csv(deg, os.path.join(cfg.out_dir,
                                             f'degree_dist_{null_name}_{method}.csv'))
            null_summary.append({
                'Null_model': null_name,
                'Method': method,
                'N_edges': len(mc),
                'N_sig_BH_two_sided': int(mc['Sig_BH'].sum()),
                'N_sig_BH_one_sided': int(mc['Sig_BH_onesided'].sum()),
                'Jaccard_H0': j0,
            })
    null_summary = pd.DataFrame(null_summary)
    safe_write_csv(null_summary, os.path.join(cfg.out_dir, 'null_model_agreement_summary.csv'))

    # Identity-preserving edge bootstrap support.
    for method in ALL_METHODS:
        universe, _, mst = snapshot[method]
        th = {t: thresholds[t] for t in universe if t in thresholds} if method == 'symbolic' else None
        support = edge_bootstrap_support(
            df_ret, th, method, cfg, derive_rng(rngs, 'edge_boot', method),
            universe, mst)
        safe_write_csv(support, os.path.join(cfg.out_dir,
                                             f'edge_bootstrap_support_{method}.csv'))

    # Rolling normalized tree length and stationarity-aware uncertainty bands.
    gd_series, stationarity_rows, episodes = {}, [], []
    for method in ALL_METHODS:
        universe = snapshot[method][0]
        mode = 'strict' if method == 'symbolic' else None
        for window in cfg.windows:
            diag = RollingDiagnostics()
            gd = rolling_global_distance(df_ret, df_sym if method == 'symbolic' else None,
                                         method, window, cfg, universe, mode, diag)
            st = test_gd_stationarity(gd, method, window, cfg)
            stationarity_rows.append(st)
            conclusion = st['Conclusion'].iloc[0]
            lo, hi, scheme = bootstrap_ntl_by_stationarity(
                gd, cfg, derive_rng(rngs, 'rolling', method, window), conclusion,
                block_size=cfg.block_size_bootstrap)
            export_rolling_csv(gd, lo, hi,
                               os.path.join(cfg.out_dir, f'ntl_{method}_w{window}.csv'))
            br = characterize_breaks(gd, lo, hi, method, window)
            if not br.empty:
                episodes.append(br)
            if window == 240:
                gd_series[method] = gd
    stationarity = pd.concat(stationarity_rows, ignore_index=True)
    safe_write_csv(stationarity, os.path.join(cfg.out_dir, 'stationarity_adf_kpss.csv'))
    if episodes:
        safe_write_csv(pd.concat(episodes, ignore_index=True),
                       os.path.join(cfg.out_dir, 'out_of_band_episodes.csv'))

    # Cross-representation convergence.
    universe_all = canon_universe(sum([snapshot[m][0] for m in ALL_METHODS], []))
    convergence = convergence_table_3way(snapshot, gd_series, universe_all)
    safe_write_csv(convergence, os.path.join(cfg.out_dir, 'convergence_3way_full.csv'))

    # MRQAP focal joint model and symbolic residual analysis.
    common = canon_universe(set(snapshot['mantegna'][0]) &
                            set(snapshot['spearman'][0]) &
                            set(snapshot['symbolic'][0]))
    if len(common) >= 10:
        Dm = snapshot['mantegna'][1]
        Ds = snapshot['spearman'][1]
        Dy = snapshot['symbolic'][1]
        mr = symbolic_non_redundancy_test(
            Dy, Dm, Ds, cfg, common, derive_rng(rngs, 'mrqap'), n_perm=1000)
        safe_write_csv(mr['C_joint']['dsp'],
                       os.path.join(cfg.out_dir, 'mrqap_dsp_C_joint.csv'))
        safe_write_csv(mr['C_joint']['freedman_lane'],
                       os.path.join(cfg.out_dir, 'mrqap_freedmanlane_C_joint.csv'))
        residual = symbolic_residual_analysis(
            Dy, Dm, Ds, cfg, common, derive_rng(rngs, 'residual'), n_perm=1000)
        safe_write_csv(residual,
                       os.path.join(cfg.out_dir, 'symbolic_residual_analysis_custom.csv'))

    # Targeted robustness checks and regulatory triangulation.
    no_elektra = []
    for method in ALL_METHODS:
        _, _, mst = snapshot[method]
        if 'ELEKTRA.MX' not in mst.nodes():
            no_elektra.append({'Method': method, 'Skipped_reason':
                               'ELEKTRA.MX not in analyzed universe'})
            continue
        info, mst_noek, _, _ = mst_without_elektra(
            df_ret, df_sym, cfg, method, base_universe=list(mst.nodes()))
        full = {frozenset([u, v]) for u, v in mst.edges()
                if u != 'ELEKTRA.MX' and v != 'ELEKTRA.MX'}
        reduced = {frozenset([u, v]) for u, v in mst_noek.edges()}
        info['Jaccard_vs_full'] = len(full & reduced) / len(full | reduced)
        no_elektra.append(info)
    safe_write_csv(pd.DataFrame(no_elektra),
                   os.path.join(cfg.out_dir, 'robustness_no_elektra.csv'))
    partition = robustness_partition_analysis(df_ret, cfg, snapshot['symbolic'][0])
    safe_write_csv(partition, os.path.join(cfg.out_dir, 'partition_robustness.csv'))
    dsib = triangulate_hubs_against_dsib(cfg)
    safe_write_csv(dsib, os.path.join(cfg.out_dir, 'cnbv_dsib_validation.csv'))

    return {
        'prices': df_prices,
        'returns': df_ret,
        'symbols': df_sym,
        'snapshot': snapshot,
        'topology': topology,
        'null_summary': null_summary,
        'rolling_ntl_w240': gd_series,
        'convergence': convergence,
        'stationarity': stationarity,
        'partition_robustness': partition,
        'cnbv_triangulation': dsib,
    }
