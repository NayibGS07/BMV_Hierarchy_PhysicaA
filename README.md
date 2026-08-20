# BMV hierarchical dependence pipeline

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22032020.svg)](https://doi.org/10.5281/zenodo.22032020)

Reproducibility package for the manuscript **“Common backbone, different topology: Triangulating dependence representations in the Mexican equity market”**, prepared for *Physica A: Statistical Mechanics and its Applications*.

This repository is being consolidated as **v1.1.0**, the manuscript-aligned reproducibility release. The historical `v1.0.0` release remains immutable and permanently archived at Zenodo under DOI [10.5281/zenodo.22032020](https://doi.org/10.5281/zenodo.22032020).

## Scope

The study uses a fixed ex-post candidate panel of 38 BMV issues and a realized universe of 35 issues after the manuscript's data-availability rules. It triangulates four rolling specifications derived from three dependence representations:

- Mantegna/Pearson distance;
- Spearman distance;
- symbolic regime synchronization with fixed full-sample thresholds (`symbolic-strict`);
- symbolic regime synchronization with thresholds recomputed inside each rolling window (`symbolic-in-window`, rolling sensitivity only).

The snapshot analysis compares the three primary dependence representations through minimum spanning trees, subdominant ultrametric hierarchies, bootstrap reliability, Monte Carlo null models, degree-distribution inference, MRQAP, robustness checks, and external CNBV regulatory triangulation.

## Repository contents

- `BMV_Hierarchy_PhysicaA.ipynb` — lightweight publication notebook; executes the modules in `src/` sequentially.
- `src/` — publication pipeline, including data acquisition, network construction, inference, rolling analysis, robustness checks, and IPC-turnover reconstruction from curated provenance.
- `requirements.txt` — reproducibility environment.
- `results/` — frozen machine-readable derived outputs supporting the manuscript.
- `figures/` — exact figure-source PNG files used by the frozen manuscript.
- `provenance/` — sanitized run metadata, source-file checksums, derived IPC composition history, and frozen-manuscript hash.
- `ARTICLE_CROSSWALK.md` — manuscript figure/table/claim → repository artifact → source-code mapping.
- `PUBLISHED_FILES.txt` — inventory of the public reproducibility package.
- `SHA256SUMS.txt` — SHA-256 checksums for public frozen artifacts.
- `RELEASE_NOTES_v1.1.0.md` — changes relative to `v1.0.0`.
- `data/README.md` — data access and redistribution rationale.
- `CITATION.cff` — software citation metadata.

## Frozen manuscript alignment

The manuscript version audited against this package has SHA-256:

`66b3322fd04e3b74b8f96ae496a1beef27c28c7677e4a25a6ddd8f46cf99ae48`

The manuscript PDF itself is not redistributed here. See `provenance/frozen_manuscript_sha256.txt` and `ARTICLE_CROSSWALK.md`.

The exact manuscript figure sources are archived in `figures/`; the corresponding numerical sources are preserved in `results/`. This is important because future downloads from upstream market-data providers may differ if historical adjusted prices or ticker availability are revised.

## Reproduce the analysis

1. Create a fresh Python environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Open `BMV_Hierarchy_PhysicaA.ipynb` from the repository root.
4. Run all cells from top to bottom.
5. Generated outputs are written to `./bmv_outputs/` and are intentionally ignored by Git.

The random seed is fixed at **42**. The archived manuscript analysis uses:

- 1,000 replicas for edge-level block-bootstrap support;
- 1,000 replicas for each Monte Carlo edge-length null (independence permutation and independent circular shift);
- 1,000 node permutations for MRQAP/residual tests;
- 2,000 replicas for rolling NTL uncertainty bands;
- pointwise 90% rolling bands (5th–95th percentiles);
- rolling windows of 120, 240, 360, and 480 trading days;
- rolling hub-stability windows of 120, 240, and 480 trading days.

Unless explicitly overridden, moving-block length follows the manuscript rule based on the cube root of the available series length, bounded below by 5 and above by half the series length.

## Data availability and licensing constraints

Underlying adjusted daily market prices were obtained through Yahoo Finance and are **not redistributed** in this repository. Users should retrieve data from the original provider under its current terms. Copies of BMV/MexDer notices and the S&P/BMV IPC constituent export are likewise not included.

To make the index-turnover calculation auditable without redistributing third-party documents, `provenance/ipc_composition_history.csv` stores the derived long-form composition snapshots used by the turnover routine, together with source identifiers and a separate alias/corporate-action mapping. Original local source-file hashes remain recorded in `provenance/source_checksums.csv`.

Because third-party source data are excluded, a future rerun may differ slightly if an upstream provider revises historical data. The frozen `results/` and `figures/` directories preserve the exact artifacts audited against the manuscript.

## Citation and archival releases

### v1.0.0

Historical release `v1.0.0` is permanently archived in Zenodo:

**DOI:** [10.5281/zenodo.22032020](https://doi.org/10.5281/zenodo.22032020)

> García Sabag, O. N., & Aguilar Arteaga, V. A. (2026). *BMV hierarchical dependence pipeline* (v1.0.0) [Software]. Zenodo. https://doi.org/10.5281/zenodo.22032020

### v1.1.0

`v1.1.0` is the manuscript-aligned consolidated release. After the GitHub tag/release is created, it should be archived as a **new Zenodo version** rather than modifying the `v1.0.0` archive. The version-specific DOI will be added here once Zenodo assigns it.

## License

Original code and repository-authored derived metadata are released under the MIT License. Third-party market data and exchange/index documents are not included and remain subject to their respective providers' terms. See `LICENSE` and `data/README.md`.
