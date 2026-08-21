# v1.1.0 — manuscript-aligned reproducibility release

This release consolidates the repository against the frozen Physica A manuscript.

## Changes from v1.0.0

- Defines the fixed ex-post 38-issue candidate universe as a study-specific construction: the 35 constituents of the S&P/BMV IPC composition effective 23 March 2026 plus ALPEKA.MX, HERDEZ.MX, and ELEKTRA.MX; historical composition notices are used separately for turnover analysis.
- Aligns the CNBV ISL table with the 2026 evaluation used in the manuscript (Banorte: Grade II).
- Expands the public rolling pipeline to the four manuscript specifications: Mantegna, Spearman, symbolic-strict, and symbolic-in-window, across 120/240/360/480-day windows.
- Records the stationarity-aware rolling bootstrap outputs used in the paper (2,000 replicas; pointwise 90% bands).
- Adds rolling hub-stability outputs for 120/240/480-day windows.
- Adds leave-one-out and complete-graph edge-perturbation robustness outputs.
- Adds the derived IPC ticker-level and issuer-level turnover series plus an auditable composition-history representation.
- Archives the exact source files for all seven numbered manuscript figures, together with selected supplementary diagnostics retained for reproducibility.
- Adds `ARTICLE_CROSSWALK.md`, manuscript SHA-256 provenance, a complete published-file inventory, and regenerated SHA-256 checksums for the frozen numerical and figure artifacts.

## Reproducibility boundary

Raw Yahoo Finance prices and third-party exchange/index documents are not redistributed. See `data/README.md` and `provenance/source_checksums.csv`.

## Zenodo archive

The historical `v1.0.0` archive remains unchanged at DOI `10.5281/zenodo.22032020`.

This manuscript-aligned `v1.1.0` release is archived as a new Zenodo version at:

**DOI:** `10.5281/zenodo.22047513`

**Record:** https://zenodo.org/records/22047513
