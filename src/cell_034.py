def _node_colors_sizes_betweenness(mst, cfg):
    """ Node color by sector, size proportional to betweenness centrality."""
    bc = nx.betweenness_centrality(mst, normalized=True)
    colors, sizes = ([], [])
    bc_max = max(bc.values()) if bc else 1.0
    for node in mst.nodes():
        sec = cfg.sector_map.get(node, 'Other')
        colors.append(cfg.sector_colors.get(sec, cfg.sector_colors['Other']))
        sizes.append(200 + 1600 * (bc.get(node, 0) / max(bc_max, 1e-09)))
    return (colors, sizes)

def plot_mst(mst, cfg, title, path, cophenetic_val=None):
    """MST visualization with betweenness-proportional node sizes."""
    fig, ax = plt.subplots(figsize=(15, 11))
    pos = nx.kamada_kawai_layout(mst, weight='weight')
    colors, sizes = _node_colors_sizes_betweenness(mst, cfg)
    weights = np.array([mst[u][v]['weight'] for u, v in mst.edges()])
    if len(weights) > 1 and weights.max() > weights.min():
        widths = 0.8 + 4.2 * (1 - (weights - weights.min()) / (weights.max() - weights.min()))
    else:
        widths = np.full_like(weights, 2.0)
    nx.draw_networkx_nodes(mst, pos, node_color=colors, node_size=sizes, ax=ax, alpha=0.9)
    nx.draw_networkx_labels(mst, pos, font_size=7.5, font_weight='bold', font_color='white', ax=ax)
    nx.draw_networkx_edges(mst, pos, width=widths, edge_color='#424242', ax=ax, alpha=0.65)
    nx.draw_networkx_edge_labels(mst, pos, {(u, v): f"{mst[u][v]['weight']:.3f}" for u, v in mst.edges()}, font_size=5.0, ax=ax)
    title_full = title + (f' | r_cof={cophenetic_val:.3f}' if cophenetic_val else '')
    present = {cfg.sector_map.get(n, 'Other') for n in mst.nodes()}
    patches = [mpatches.Patch(color=cfg.sector_colors.get(s, cfg.sector_colors['Other']), label=s) for s in sorted(present)]
    ax.legend(handles=patches, loc='upper left', fontsize=8, title='Sector', framealpha=0.85)
    ax.set_title(title_full, fontsize=13, fontweight='bold', pad=14)
    ax.axis('off')
    plt.tight_layout()
    _save_fig(fig, path, cfg)

def plot_ht(Z, nodes, cfg, title, path, cophenetic_val=None):
    """Hierarchical tree (dendrogram) visualization."""
    title_full = title + (f' | r_cof={cophenetic_val:.3f}' if cophenetic_val else '')
    fig, ax = plt.subplots(figsize=(16, 6))
    dendrogram(Z, labels=nodes, ax=ax, leaf_rotation=90, leaf_font_size=8, color_threshold=0.75 * float(Z[:, 2].max()))
    for lbl in ax.get_xticklabels():
        t = lbl.get_text()
        sec = cfg.sector_map.get(t, 'Other')
        lbl.set_color(cfg.sector_colors.get(sec, cfg.sector_colors['Other']))
    present = {cfg.sector_map.get(n, 'Other') for n in nodes}
    patches = [mpatches.Patch(color=cfg.sector_colors.get(s, cfg.sector_colors['Other']), label=s) for s in sorted(present)]
    ax.legend(handles=patches, loc='upper right', fontsize=7.5, title='Sector', framealpha=0.85)
    ax.set_ylabel('Ultrametric distance', fontsize=10)
    ax.set_title(title_full, fontsize=13, fontweight='bold')
    plt.tight_layout()
    _save_fig(fig, path, cfg)

def _plot_rolling_series(series, cfg, window, method, ylabel, title, path, lo=None, hi=None, scatter_up=None, scatter_dn=None):
    """Generic rolling series plotter with optional CI band and events."""
    g = series.dropna()
    fig, ax = plt.subplots(figsize=(14, 5))
    if lo is not None and hi is not None:
        lo_r = lo.reindex(g.index)
        hi_r = hi.reindex(g.index)
        ax.fill_between(g.index, lo_r.values, hi_r.values, alpha=0.15, color='#E53935', label=f'CI {cfg.ci_gd[0] * 100:.0f}–{cfg.ci_gd[1] * 100:.0f}% (block-bootstrap)')
        ax.plot(lo_r.index, lo_r.values, lw=0.85, ls='--', color='#E53935', alpha=0.6)
        ax.plot(hi_r.index, hi_r.values, lw=0.85, ls='--', color='#E53935', alpha=0.6)
    ax.plot(g.index, g.values, lw=1.6, color='#1565C0', label=f'{ylabel} (w={window}, {method})', zorder=3)
    if scatter_up is not None and len(scatter_up):
        ax.scatter(scatter_up.index, scatter_up.values, color='#B71C1C', s=22, zorder=5, label=f'↑ fragmentation (n={len(scatter_up)})')
    if scatter_dn is not None and len(scatter_dn):
        ax.scatter(scatter_dn.index, scatter_dn.values, color='#0D47A1', s=22, zorder=5, label=f'↓ integration (n={len(scatter_dn)})')
    all_v = g.values
    if lo is not None:
        all_v = np.concatenate([hi.reindex(g.index).dropna().values, lo.reindex(g.index).dropna().values, g.values])
    ymax = float(np.nanmax(all_v))
    yrange = max(ymax - float(np.nanmin(all_v)), 1e-09)
    for label_ev, date_str in cfg.historical_events.items():
        date = pd.Timestamp(date_str)
        if g.index.min() <= date <= g.index.max():
            ax.axvline(date, color='#555', lw=0.8, ls=':', alpha=0.75)
            ax.text(date, ymax - 0.02 * yrange, label_ev, fontsize=6, ha='center', va='top', bbox=dict(boxstyle='round,pad=0.2', fc='lightyellow', alpha=0.75, ec='#aaa'))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=38, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.legend(fontsize=7.5, loc='upper left', framealpha=0.88)
    plt.tight_layout()
    _save_fig(fig, path, cfg)

def plot_ntl_with_ci(gd, lo, hi, cfg, window, method, title, path):
    """NTL rolling plot with block-bootstrap CI."""
    g = gd.dropna()
    lo_r = lo.reindex(g.index)
    hi_r = hi.reindex(g.index)
    bu = g[g > hi_r]
    bd = g[g < lo_r]
    _plot_rolling_series(gd, cfg, window, method, 'NTL', title, path, lo=lo, hi=hi, scatter_up=bu, scatter_dn=bd)

def plot_rolling_apl(apl_series, cfg, window, method, path):
    """ Rolling APL_weighted plot."""
    title = f'Rolling APL (weighted) — {method} w={window} | BMV'
    _plot_rolling_series(apl_series, cfg, window, method, 'APL (weighted)', title, path)

def plot_rolling_diameter(diam_series, cfg, window, method, path):
    """ Rolling topological diameter plot."""
    title = f'Rolling diameter (topo) — {method} w={window} | BMV'
    _plot_rolling_series(diam_series, cfg, window, method, 'Diameter (hops)', title, path)

def plot_rolling_entropy(ent_series, cfg, window, method, path):
    """ Rolling degree entropy plot."""
    title = f'Rolling degree entropy — {method} w={window} | BMV'
    _plot_rolling_series(ent_series, cfg, window, method, 'Degree entropy (bits)', title, path)

def plot_mc_significance(df_mc, cfg, method, path):
    """MST edge-length order-statistic test plot (see
    mst_edge_length_order_statistic_test docstring for scope)."""
    fig, ax = plt.subplots(figsize=(12, 5))
    x, obs = (df_mc['Rank'].values, df_mc['Observed'].values)
    ci_cols = [c for c in df_mc.columns if c.startswith('CI_')]
    lo_c, hi_c = (ci_cols[0], ci_cols[-1])
    ax.fill_between(x, df_mc[lo_c].values, df_mc[hi_c].values, alpha=0.25, color='#9E9E9E', label='Null CI')
    ax.plot(x, df_mc[lo_c].values, lw=0.8, color='#757575', ls='--')
    ax.plot(x, df_mc[hi_c].values, lw=0.8, color='#757575', ls='--')
    sig_bh = df_mc['Sig_BH'].values.astype(bool)
    sig_raw = df_mc['Sig_raw'].values.astype(bool)
    ax.scatter(x[sig_bh], obs[sig_bh], color='#1B5E20', s=50, zorder=6, edgecolors='#004D00', linewidths=1.0, label='Sig. BH (FDR 5%)')
    so = sig_raw & ~sig_bh
    if so.any():
        ax.scatter(x[so], obs[so], color='#66BB6A', s=35, zorder=5, label='Sig. raw only')
    ax.scatter(x[~sig_raw], obs[~sig_raw], color='#B71C1C', s=35, zorder=5, marker='x', label='Not significant')
    ax.set_xlabel('Edge rank (1 = shortest distance)', fontsize=9)
    ax.set_ylabel('Observed distance', fontsize=9)
    ax.set_title(f'MST edge-length order-statistic test — {method} | null={cfg.mc_null_model} | FDR 5%', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    plt.tight_layout()
    _save_fig(fig, path, cfg)

def plot_descriptive_stats(df_stats, cfg, path):
    """Excess kurtosis and skewness bar plot."""
    if df_stats.empty:
        return
    df_s = df_stats.sort_values('Excess_kurtosis', ascending=False)
    colors = [cfg.sector_colors.get(s, cfg.sector_colors['Other']) for s in df_s['Sector']]
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    for ax, col, xlabel in zip(axes, ['Excess_kurtosis', 'Skewness'], ['Excess kurtosis', 'Skewness (+ = right tail)']):
        ax.barh(df_s['Ticker'], df_s[col], color=colors, alpha=0.8)
        ax.axvline(0, color='black', lw=0.8, ls='--')
        ax.set_xlabel(xlabel, fontsize=9)
        ax.tick_params(axis='y', labelsize=7)
    present = set(df_s['Sector'])
    patches = [mpatches.Patch(color=cfg.sector_colors.get(s, cfg.sector_colors['Other']), label=s) for s in sorted(present)]
    fig.legend(handles=patches, loc='lower center', ncol=4, fontsize=8, framealpha=0.85, bbox_to_anchor=(0.5, -0.08))
    n_reject = int((~df_stats['Normal_5pct']).sum())
    fig.suptitle(f'Descriptive statistics — {n_reject}/{len(df_stats)} reject normality (JB 5%)', fontsize=12, fontweight='bold')
    plt.tight_layout()
    _save_fig(fig, path, cfg)

def plot_convergence_heatmap(conv_df, jaccard_h0, cfg, path):
    """ 3x3 convergence heatmap (Jaccard, Corr matrices, Corr NTL rolling)."""
    methods = ['mantegna', 'spearman', 'symbolic']
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, metric, label in zip(axes, ['Jaccard', 'Corr_matrices', 'Corr_NTL_rolling'], ['Jaccard index', 'Distance matrix corr.', 'NTL rolling corr.']):
        mat = np.eye(3)
        for _, row in conv_df.iterrows():
            pair = row['Pair']
            val = row[metric] if metric in row and np.isfinite(row[metric]) else 0.0
            for mi, mn in enumerate(methods):
                for mj, mm in enumerate(methods):
                    if f'{mn} vs {mm}' == pair or f'{mm} vs {mn}' == pair:
                        if mi != mj:
                            mat[mi, mj] = mat[mj, mi] = val
        im = ax.imshow(mat, cmap='YlOrRd', vmin=0, vmax=1, aspect='equal')
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f'{mat[i, j]:.3f}', ha='center', va='center', fontsize=10, fontweight='bold', color='white' if mat[i, j] > 0.7 else 'black')
        ax.set_xticks(range(3))
        ax.set_yticks(range(3))
        ax.set_xticklabels(methods, fontsize=9, rotation=30)
        ax.set_yticklabels(methods, fontsize=9)
        ax.set_title(label, fontsize=11, fontweight='bold')
    fig.suptitle('Cross-metric convergence', fontsize=13, fontweight='bold')
    plt.tight_layout()
    _save_fig(fig, path, cfg)
