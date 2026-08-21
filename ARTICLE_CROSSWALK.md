# Article-to-repository crosswalk

This file maps the frozen manuscript **“Common backbone, different topology: Triangulating dependence representations in the Mexican equity market”** to the reproducibility artifacts prepared for release `v1.1.0`.

Frozen manuscript SHA-256:

`46a6c49720c6a1dc9c134856a65b7178586fc4f8494d1c453960ca9b2d0f74cc`

The manuscript PDF itself is not redistributed here. The hash is recorded in `provenance/frozen_manuscript_sha256.txt`.

## Main manuscript elements

| Manuscript element | Primary repository artifact(s) | Pipeline source |
|---|---|---|
| Table 1 — non-normality of daily log-returns | `results/descriptive_stats.csv` | `src/cell_016.py`, `src/cell_038.py` |
| Figure 1 — cross-method convergence | `figures/fig2_convergence_heatmap.png`, `results/convergence_3way_full.csv` | `src/cell_030.py`, `src/cell_034.py`, `src/cell_038.py` |
| Table 2 — snapshot topology / hubs / cophenetic correlation | `results/snapshot_topology.csv`, `results/cophenetic_*.csv` | `src/cell_024.py`, `src/cell_038.py` |
| Figure 2 — three snapshot MSTs | `figures/fig1a_mst_mantegna.png`, `figures/fig1b_mst_spearman.png`, `figures/fig1c_mst_symbolic.png`, `results/edges_*.csv` | `src/cell_024.py`, `src/cell_034.py`, `src/cell_038.py` |
| Table 3 — degree-distribution tests | `results/degree_dist_permutation_*.csv`, `results/degree_dist_circular_shift_*.csv` | `src/cell_024.py`, `src/cell_038.py` |
| Table 4 — agreement of the two Monte Carlo nulls | `results/null_model_agreement_summary.csv`, `results/mc_permutation_*.csv`, `results/mc_circular_shift_*.csv` | `src/cell_024.py`, `src/cell_038.py` |
| Figure 3 — Mantegna order-statistic Monte Carlo tests | `figures/fig8a_mc_permutation_mantegna.png`, `figures/fig8b_mc_circular_shift_mantegna.png` | `src/cell_034.py`, `src/cell_038.py` |
| Table 5 — focal DSP-MRQAP joint model | `results/mrqap_dsp_C_joint.csv`, `results/mrqap_freedmanlane_C_joint.csv` | `src/cell_036.py`, `src/cell_038.py` |
| Figure 4 — MRQAP coefficients and symbolic residuals | `figures/fig3a_mrqap_coefficients.png`, `figures/fig3b_residuals_by_sector.png`, `results/symbolic_residual_analysis_custom.csv` | `src/cell_036.py`, `src/cell_038.py` |
| Figure 5 — Spearman rolling NTL, 480 days | `figures/fig4_ntl_spearman_w480.png`, `results/ntl_spearman_w480.csv`, `results/out_of_band_episodes.csv` | `src/cell_028.py`, `src/cell_034.py`, `src/cell_038.py` |
| Figure 6 — Mantegna rolling NTL, 480 days | `figures/fig9a_ntl_mantegna_w480.png`, `results/ntl_mantegna_w480.csv`, `results/out_of_band_episodes.csv` | `src/cell_028.py`, `src/cell_034.py`, `src/cell_038.py` |
| Table 6 — CNBV 2026 ISL triangulation | `results/cnbv_dsib_validation.csv` | `src/cell_014.py`, `src/cell_038.py` |
| Table 7 — notable edge bootstrap support | `results/edge_bootstrap_support_*.csv` | `src/cell_024.py`, `src/cell_038.py` |
| Table 8 — Mantegna leave-one-out sensitivity | `results/leave_one_out_mantegna.csv` | `src/cell_032.py`, `src/cell_038.py` |
| Table 9 — top-two-hub leave-one-out comparison | `results/leave_one_out_*.csv` | `src/cell_032.py`, `src/cell_038.py` |
| Table 10 — symbolic partition sensitivity | `results/partition_robustness.csv` | `src/cell_032.py`, `src/cell_038.py` |
| Figure 7 — IPC turnover | `figures/fig7_ipc_turnover.png`, `results/ipc_turnover_by_ticker.csv`, `results/ipc_turnover_by_issuer.csv` | `src/cell_033.py`, `src/cell_038.py` |

## Additional manuscript claims and robustness checks

- **38-issue candidate universe / 35-issue realized universe:** `results/ticker_coverage.csv`, `results/data_provenance.csv`, `src/cell_006.py`.
- **March-2026 IPC reference composition:** `provenance/ipc_composition_history.csv`.
- **Snapshot matrices and backbone edges:** `results/D_*_snapshot.csv`, `results/edges_*.csv`.
- **Rolling stationarity and pointwise bootstrap bands:** `results/stationarity_adf_kpss.csv`, all 16 `results/ntl_*_w*.csv`.
- **Rolling hub stability:** `results/hub_stability_all.csv`, `results/hub_stability_summary.csv`, and method/window-specific hub files.
- **Edge perturbation robustness:** `results/edge_perturbation_*.csv`.
- **ELEKTRA non-applicability check:** `results/robustness_no_elektra.csv`.
- **Index-turnover provenance:** `provenance/ipc_composition_history.csv`, `provenance/ipc_issuer_aliases.csv`, `provenance/ipc_history_gaps.csv`, `provenance/ipc_corporate_actions.csv`.
- **Exact artifact integrity:** `SHA256SUMS.txt`.

## Archived supplementary diagnostics not displayed in the current manuscript

The release also preserves figure outputs generated during the audited analysis but not displayed as numbered manuscript figures, including:

- `figures/fig5a_ht_mantegna.png`
- `figures/fig5b_ht_symbolic.png`
- `figures/fig6_desc_stats.png`

These files are retained as reproducibility diagnostics and are not cited as numbered figures in the current manuscript.

## Data redistribution boundary

Raw Yahoo Finance price histories, the S&P/BMV IPC constituent export, and copies of BMV/MexDer notices are not redistributed. The repository contains the code, source checksums, derived composition history, derived result tables, and manuscript figure sources needed to audit the reported results. Future upstream downloads may differ if a provider revises historical data.
