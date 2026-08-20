# v1.1.0 — manuscript-aligned reproducibility release

This release consolidates the repository against the frozen Physica A manuscript.

## Changes from v1.0.0

- Aligns the CNBV ISL table with the 2026 evaluation used in the manuscript (Banorte: Grade II).
- Expands the public rolling pipeline to the four manuscript specifications: Mantegna, Spearman, symbolic-strict, and symbolic-in-window, across 120/240/360/480-day windows.
- Records the stationarity-aware rolling bootstrap outputs used in the paper (2,000 replicas; pointwise 90% bands).
- Adds rolling hub-stability outputs for 120/240/480-day windows.
- Adds leave-one-out and complete-graph edge-perturbation robustness outputs.
- Adds the derived IPC ticker-level and issuer-level turnover series plus an auditable composition-history representation.
- Archives the exact manuscript figure source files.
- Adds `ARTICLE_CROSSWALK.md`, manuscript SHA-256 provenance, a complete published-file inventory, and SHA-256 checksums.

## Reproducibility boundary

Raw Yahoo Finance prices and third-party exchange/index documents are not redistributed. See `data/README.md` and `provenance/source_checksums.csv`.

## Archival workflow

After this commit is tagged/released as `v1.1.0`, create a new Zenodo version from that GitHub release. Do not alter or overwrite the archived `v1.0.0` record.
