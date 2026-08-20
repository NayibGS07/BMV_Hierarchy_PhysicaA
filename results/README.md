# Curated derived results

This directory contains the frozen derived tables used to audit the final manuscript.

The package intentionally excludes raw Yahoo Finance price histories and copies of third-party BMV/MexDer/S&P documents. Those remain subject to their providers' terms. The corresponding provenance boundary is documented in `../data/README.md` and `../provenance/`.

## Contents

The curated tables cover:

- realized-universe coverage and data-acquisition provenance;
- snapshot distance matrices, MST edges, topology and cophenetic correlations;
- edge-bootstrap support;
- Monte Carlo order-statistic inference under permutation and circular-shift nulls;
- empirical random-MST degree/entropy tests;
- DSP-MRQAP, Freedman–Lane robustness, and symbolic residual analysis;
- all 16 rolling NTL specifications and stationarity-aware confidence bands;
- out-of-band episodes and rolling hub stability;
- leave-one-out, edge-perturbation, symbolic-partition and ELEKTRA checks;
- IPC ticker-level and issuer-level turnover;
- CNBV 2026 ISL regulatory triangulation.

See `../ARTICLE_CROSSWALK.md` for the manuscript element → artifact → source-code mapping. Exact file hashes are listed in `../SHA256SUMS.txt`.
