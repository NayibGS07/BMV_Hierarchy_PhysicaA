def run_pipeline(cfg: Config = CFG):
    """Run the manuscript-aligned reproducibility pipeline.

    Raw third-party market and exchange/index source files are not written to
    the public output tree. The run produces derived numerical tables and
    publication plots under ``cfg.out_dir``.
    """
    ensure_dir(cfg.out_dir)
    rngs = make_rngs(cfg.seed)
    write_manifest(cfg, rngs, os.path.join(cfg.out_dir, "manifest.json"))

    # Data acquisition, provenance, coverage, returns, and descriptives.
    df_prices, data_provenance = download_prices(cfg)
    safe_write_csv(data_provenance, os.path.join(cfg.out_dir, "data_provenance.csv"))
    df_prices, coverage = filter_by_coverage(df_prices, cfg)
    safe_write_csv(coverage, os.path.join(cfg.out_dir, "ticker_coverage.csv"))
    df_ret = null_splice_transition_returns(compute_log_returns(df_prices))
    descriptive = compute_descriptive_stats(df_ret, cfg)
    safe_write_csv(descriptive, os.path.join(cfg.out_dir, "descriptive_stats.csv"))
    plot_descriptive_stats(descriptive, cfg, os.path.join(cfg.out_dir, "desc_stats.png"))

    # Symbolization and fixed thresholds used by the snapshot/null analyses.
    df_sym = symbolize_global(df_ret, cfg)
    thresholds = compute_symbol_thresholds(df_ret, cfg)
    safe_write_csv(
        pd.DataFrame([
            {"Ticker": t, "a_i": a, "b_i": b}
            for t, (a, b) in thresholds.items()
        ]),
        os.path.join(cfg.out_dir, "symbol_thresholds.csv"),
    )

    # Snapshot dependence matrices, MSTs, ultrametric hierarchies, and metrics.
    snapshot = {}
    topology_rows = []
    for method in ALL_METHODS:
        universe, D, mst = select_fixed_universe_snapshot(df_ret, df_sym, cfg, method)
        snapshot[method] = (universe, D, mst)
        D.to_csv(os.path.join(cfg.out_dir, f"D_{method}_snapshot.csv"), encoding="utf-8")
        safe_write_csv(mst_edge_table(mst, cfg.sector_map),
                       os.path.join(cfg.out_dir, f"edges_{method}.csv"))
        safe_write_csv(mst_degree_table(mst, cfg.sector_map),
                       os.path.join(cfg.out_dir, f"degree_{method}.csv"))
        safe_write_csv(betweenness_centrality_table(mst, cfg.sector_map),
                       os.path.join(cfg.out_dir, f"betweenness_{method}.csv"))

        topo = topological_metrics(mst)
        hub, hub_degree, hub_tied, _ = select_hub(mst)
        bc = nx.betweenness_centrality(mst, normalized=True)
        bc_leader, bc_max = max(bc.items(), key=lambda x: x[1])
        topo.update({
            "Method": method,
            "N_nodes": mst.number_of_nodes(),
            "N_edges": mst.number_of_edges(),
            "Hub": hub,
            "Hub_degree": hub_degree,
            "Hub_tied": hub_tied,
            "Betw_leader": bc_leader,
            "Betw_max": round(float(bc_max), 4),
            "Dist_min": round(min(d["weight"] for _, _, d in mst.edges(data=True)), 4),
            "Dist_max": round(max(d["weight"] for _, _, d in mst.edges(data=True)), 4),
        })
        topology_rows.append(topo)

        U = ultrametric_from_mst(mst, universe)
        Z, nodes = build_ht_linkage(U)
        coph = cophenetic_correlation(Z, D, nodes)
        safe_write_csv(pd.DataFrame([{"Method": method, "r_cophenetic": coph}]),
                       os.path.join(cfg.out_dir, f"cophenetic_{method}.csv"))
        plot_mst(mst, cfg,
                 f"MST {method} — BMV {cfg.start[:4]}–{cfg.end_display_year}",
                 os.path.join(cfg.out_dir, f"mst_{method}.png"), coph)
        plot_ht(Z, nodes, cfg,
                f"HT {method} — BMV {cfg.start[:4]}–{cfg.end_display_year}",
                os.path.join(cfg.out_dir, f"ht_{method}.png"), coph)

        corr_mod = correlation_intra_inter_module(df_ret, mst, cfg, universe)
        corr_mod["Method"] = method
        safe_write_csv(corr_mod, os.path.join(cfg.out_dir, f"corr_intra_inter_{method}.csv"))

    topology = pd.DataFrame(topology_rows)
    safe_write_csv(topology, os.path.join(cfg.out_dir, "snapshot_topology.csv"))

    # Snapshot convergence before rolling-series correlations are added.
    universe_all = canon_universe(sum([snapshot[m][0] for m in ALL_METHODS], []))
    convergence_snapshot = convergence_table_3way(snapshot, {}, universe_all)
    safe_write_csv(convergence_snapshot,
                   os.path.join(cfg.out_dir, "convergence_3way_snapshot.csv"))

    # Targeted robustness checks.
    no_elektra_rows = []
    for method in ALL_METHODS:
        _, D, mst = snapshot[method]
        if "ELEKTRA.MX" not in mst.nodes():
            no_elektra_rows.append({
                "Method": method,
                "N_nodes": mst.number_of_nodes(),
                "Hub": None,
                "Hub_degree": None,
                "NTL": None,
                "Jaccard_vs_full": np.nan,
                "Skipped_reason": "ELEKTRA.MX not in analyzed universe (see data_provenance.csv)",
            })
        else:
            info, mst_noek, _, _ = mst_without_elektra(
                df_ret, df_sym, cfg, method, base_universe=list(mst.nodes()))
            full_edges = {
                frozenset([u, v]) for u, v in mst.edges()
                if u != "ELEKTRA.MX" and v != "ELEKTRA.MX"
            }
            reduced_edges = {frozenset([u, v]) for u, v in mst_noek.edges()}
            union = full_edges | reduced_edges
            info["Jaccard_vs_full"] = round(len(full_edges & reduced_edges) / len(union), 4) if union else np.nan
            info["Skipped_reason"] = ""
            no_elektra_rows.append(info)

        loo = leave_one_out_sensitivity(df_ret, df_sym, cfg, method, mst, top_k=5)
        safe_write_csv(loo, os.path.join(cfg.out_dir, f"leave_one_out_{method}.csv"))

        pert = edge_perturbation_robustness(
            D, mst, cfg, derive_rng(rngs, "perturb", method))
        pert["Method"] = method
        safe_write_csv(pert, os.path.join(cfg.out_dir, f"edge_perturbation_{method}.csv"))

    safe_write_csv(pd.DataFrame(no_elektra_rows),
                   os.path.join(cfg.out_dir, "robustness_no_elektra.csv"))

    partition = robustness_partition_analysis(df_ret, cfg, snapshot["symbolic"][0])
    safe_write_csv(partition, os.path.join(cfg.out_dir, "partition_robustness.csv"))

    # IPC reconstitution dynamics from the curated, derived composition history.
    ipc_turnover = compute_ipc_turnover_from_curated()
    issuer_turnover = compute_issuer_turnover_from_curated()
    safe_write_csv(ipc_turnover, os.path.join(cfg.out_dir, "ipc_turnover_by_ticker.csv"))
    safe_write_csv(issuer_turnover, os.path.join(cfg.out_dir, "ipc_turnover_by_issuer.csv"))
    plot_ipc_turnover(ipc_turnover, cfg, os.path.join(cfg.out_dir, "ipc_turnover.png"))
    if Path("provenance/ipc_corporate_actions.csv").exists():
        safe_write_csv(pd.read_csv("provenance/ipc_corporate_actions.csv"),
                       os.path.join(cfg.out_dir, "ipc_corporate_actions.csv"))

    # External regulatory triangulation.
    cnbv = triangulate_hubs_against_dsib(cfg)
    safe_write_csv(cnbv, os.path.join(cfg.out_dir, "cnbv_dsib_validation.csv"))

    # Formal matrix-level non-redundancy tests.
    common = canon_universe(
        set(snapshot["mantegna"][0]) &
        set(snapshot["spearman"][0]) &
        set(snapshot["symbolic"][0])
    )
    mrqap_results = None
    residual = None
    if len(common) >= 10:
        Dm = snapshot["mantegna"][1]
        Ds = snapshot["spearman"][1]
        Dy = snapshot["symbolic"][1]
        mrqap_results = symbolic_non_redundancy_test(
            Dy, Dm, Ds, cfg, common, derive_rng(rngs, "mrqap"), n_perm=1000)
        for spec_name, res in mrqap_results.items():
            safe_write_csv(res["dsp"],
                           os.path.join(cfg.out_dir, f"mrqap_dsp_{spec_name}.csv"))
            safe_write_csv(res["freedman_lane"],
                           os.path.join(cfg.out_dir, f"mrqap_freedmanlane_{spec_name}.csv"))
            plot_mrqap_coefficients(
                res["dsp"], cfg, spec_name,
                os.path.join(cfg.out_dir, f"mrqap_coefficients_{spec_name}.png"))
        if "C_joint" in mrqap_results:
            plot_mrqap_null_distribution(
                mrqap_results["C_joint"]["dsp"], "SameSector", cfg, "C_joint",
                os.path.join(cfg.out_dir, "mrqap_null_distribution_C_joint_SameSector.png"))
        residual = symbolic_residual_analysis(
            Dy, Dm, Ds, cfg, common, derive_rng(rngs, "mrqap_residual"), n_perm=1000)
        safe_write_csv(residual,
                       os.path.join(cfg.out_dir, "symbolic_residual_analysis_custom.csv"))
        plot_symbolic_residuals_by_sector(
            residual, cfg, os.path.join(cfg.out_dir, "symbolic_residuals_by_sector.png"))

    # Monte Carlo order-statistic tests under both null constructions.
    universe_mc_sym = [t for t in snapshot["symbolic"][0] if t in thresholds]
    min_common = _effective_min_common(cfg)
    sym_mc = df_sym[df_sym["Ticker"].isin(universe_mc_sym)][["Fecha", "Ticker", "symbol"]].copy()
    D_mc = symbolic_distance_matrix(sym_mc, cfg, min_common).loc[universe_mc_sym, universe_mc_sym]
    D_mc = drop_isolated_tickers(D_mc, cfg.min_valid_peers)
    D_mc, universe_mc_sym = force_largest_connected_component(D_mc)
    mst_mc_sym = build_mst_from_D(D_mc)
    thresholds_mc = {t: thresholds[t] for t in universe_mc_sym}

    mc_results = {}
    jaccard_primary = {}
    for null_name in ("permutation", "circular_shift"):
        cfg_null = replace(cfg, mc_null_model=null_name)
        mc_results[null_name] = {}
        for method in ALL_METHODS:
            if method == "symbolic":
                mc, j0, null_msts = mst_edge_length_order_statistic_test(
                    df_ret, thresholds_mc, method, cfg_null, rngs.mc,
                    universe_mc_sym, mst_mc_sym)
                mst_for_degree = mst_mc_sym
            else:
                universe, _, mst = snapshot[method]
                mc, j0, null_msts = mst_edge_length_order_statistic_test(
                    df_ret, None, method, cfg_null, rngs.mc, universe, mst)
                mst_for_degree = mst
            mc_results[null_name][method] = mc
            safe_write_csv(mc, os.path.join(cfg.out_dir, f"mc_{null_name}_{method}.csv"))
            plot_mc_significance(
                mc, cfg_null, method,
                os.path.join(cfg.out_dir, f"mc_{null_name}_{method}.png"))
            deg = degree_distribution_test(
                mst_for_degree, null_msts=null_msts,
                rng=derive_rng(rngs, "degree_test", method, null_name))
            deg["Primary_null_model"] = f"empirical random-MST null ({null_name} data)"
            safe_write_csv(deg,
                           os.path.join(cfg.out_dir, f"degree_dist_{null_name}_{method}.csv"))
            if null_name == "permutation":
                jaccard_primary[method] = j0

    agreement_rows = []
    for method in ALL_METHODS:
        a = mc_results["permutation"][method][["Rank", "Sig_BH"]]
        b = mc_results["circular_shift"][method][["Rank", "Sig_BH"]]
        cmp = a.merge(b, on="Rank", suffixes=("_permutation", "_circular_shift"))
        agreement_rows.append({
            "Method": method,
            "N_ranks": len(cmp),
            "Sig_permutation": int(cmp["Sig_BH_permutation"].sum()),
            "Sig_circular_shift": int(cmp["Sig_BH_circular_shift"].sum()),
            "Agreement_pct": round(100 * (cmp["Sig_BH_permutation"] == cmp["Sig_BH_circular_shift"]).mean(), 1),
        })
    null_agreement = pd.DataFrame(agreement_rows)
    safe_write_csv(null_agreement,
                   os.path.join(cfg.out_dir, "null_model_agreement_summary.csv"))
    jaccard_expected = pd.DataFrame([
        {"Method": m, "Jaccard_expected_H0": round(float(v), 4)}
        for m, v in jaccard_primary.items()
    ])
    safe_write_csv(jaccard_expected,
                   os.path.join(cfg.out_dir, "jaccard_expected_mc.csv"))

    # Identity-preserving edge bootstrap support.
    for method in ALL_METHODS:
        if method == "symbolic":
            support = edge_bootstrap_support(
                df_ret, thresholds_mc, method, cfg,
                derive_rng(rngs, "edge_support", method),
                universe_mc_sym, mst_mc_sym)
        else:
            universe, _, mst = snapshot[method]
            support = edge_bootstrap_support(
                df_ret, None, method, cfg,
                derive_rng(rngs, "edge_support", method), universe, mst)
        safe_write_csv(support,
                       os.path.join(cfg.out_dir, f"edge_bootstrap_support_{method}.csv"))

    # Rolling NTL: Mantegna, Spearman, symbolic-strict, symbolic-in-window.
    gd_for_convergence = {}
    stationarity_rows = []
    episode_rows = []
    hub_frames = []
    seasonality_rows = []

    def run_rolling_spec(method, universe, symbol_mode=None):
        method_label = method + (f"/{symbol_mode}" if symbol_mode else "")
        for window in cfg.windows:
            diag = RollingDiagnostics()
            gd = rolling_global_distance(
                df_ret, df_sym if method == "symbolic" else None,
                method, window, cfg, universe, symbol_mode, diag)
            stationarity = test_gd_stationarity(gd, method_label, window, cfg)
            stationarity_rows.append(stationarity)
            conclusion = stationarity["Conclusion"].iloc[0]
            lo, hi, scheme = bootstrap_ntl_by_stationarity(
                gd, cfg, derive_rng(rngs, method, symbol_mode or "", window),
                conclusion, block_size=cfg.block_size_bootstrap)

            stem = os.path.join(cfg.out_dir, f"ntl_{method}")
            if symbol_mode:
                stem += f"_{symbol_mode}"
            stem += f"_w{window}"
            export_rolling_csv(gd, lo, hi, stem + ".csv")
            plot_ntl_with_ci(
                gd, lo, hi, cfg, window, method_label,
                f"Rolling NTL — {method_label} w={window} | BMV [band: {scheme}]",
                stem + ".png")

            breaks = characterize_breaks(gd, lo, hi, method_label, window)
            if not breaks.empty:
                episode_rows.append(breaks)
            seasonality_rows.append({
                "Method": method_label,
                "Window": window,
                "CV_max": seasonality_cv_log(gd, method_label, window),
            })
            with open(stem.replace("ntl_", "diag_") + ".json", "w", encoding="utf-8") as f:
                json.dump(diag.as_dict(), f, ensure_ascii=False, indent=2)

            if window == 240 and (method != "symbolic" or symbol_mode == "strict"):
                gd_for_convergence[method] = gd
            if window in cfg.hub_stability_windows and (method != "symbolic" or symbol_mode == "strict"):
                hub = hub_stability_rolling(
                    df_ret, df_sym if method == "symbolic" else None,
                    method, window, cfg, universe, symbol_mode)
                if not hub.empty:
                    hub_frames.append(hub)

    run_rolling_spec("mantegna", snapshot["mantegna"][0])
    run_rolling_spec("spearman", snapshot["spearman"][0])
    for mode in cfg.rolling_symbol_mode:
        run_rolling_spec("symbolic", snapshot["symbolic"][0], mode)

    stationarity_all = pd.concat(stationarity_rows, ignore_index=True)
    safe_write_csv(stationarity_all,
                   os.path.join(cfg.out_dir, "stationarity_adf_kpss.csv"))
    if episode_rows:
        episodes_all = pd.concat(episode_rows, ignore_index=True)
        safe_write_csv(episodes_all,
                       os.path.join(cfg.out_dir, "out_of_band_episodes.csv"))
    else:
        episodes_all = pd.DataFrame()
    seasonality = pd.DataFrame(seasonality_rows)
    safe_write_csv(seasonality, os.path.join(cfg.out_dir, "seasonality_cv.csv"))

    if hub_frames:
        hubs_all = pd.concat(hub_frames, ignore_index=True)
        safe_write_csv(hubs_all, os.path.join(cfg.out_dir, "hub_stability_all.csv"))
        summary_rows = []
        for (method, window), grp in hubs_all.groupby(["Method", "Window"]):
            for rank, (ticker, count) in enumerate(grp["Hub_ticker"].value_counts().head(5).items(), 1):
                summary_rows.append({
                    "Method": method,
                    "Window": window,
                    "Rank": rank,
                    "Hub": ticker,
                    "Windows": int(count),
                    "Pct": round(100 * count / len(grp), 2),
                    "Sector": cfg.sector_map.get(ticker, "Other"),
                })
        hub_summary = pd.DataFrame(summary_rows)
        safe_write_csv(hub_summary,
                       os.path.join(cfg.out_dir, "hub_stability_summary.csv"))
    else:
        hubs_all = pd.DataFrame()
        hub_summary = pd.DataFrame()

    convergence = convergence_table_3way(snapshot, gd_for_convergence, universe_all)
    safe_write_csv(convergence, os.path.join(cfg.out_dir, "convergence_3way_full.csv"))
    plot_convergence_heatmap(
        convergence, jaccard_primary, cfg,
        os.path.join(cfg.out_dir, "convergence_heatmap.png"))

    return {
        "prices": df_prices,
        "returns": df_ret,
        "symbols": df_sym,
        "snapshot": snapshot,
        "topology": topology,
        "convergence": convergence,
        "null_agreement": null_agreement,
        "stationarity": stationarity_all,
        "episodes": episodes_all,
        "hub_stability": hubs_all,
        "hub_stability_summary": hub_summary,
        "partition_robustness": partition,
        "cnbv_triangulation": cnbv,
        "ipc_turnover": ipc_turnover,
        "ipc_turnover_issuer": issuer_turnover,
        "mrqap": mrqap_results,
        "symbolic_residual": residual,
    }
