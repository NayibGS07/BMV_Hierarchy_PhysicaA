# BMV hierarchical dependence pipeline

Reproducibility package for the manuscript **“Common backbone, different topology: Triangulating dependence representations in the Mexican equity market”**, prepared for *Physica A: Statistical Mechanics and its Applications*.

## Scope

The analysis uses a fixed ex-post candidate panel of 38 BMV issues and a realized universe of 35 issues after the manuscript's data-availability rules. It triangulates three dependence representations—Mantegna/Pearson distance, Spearman distance, and symbolic regime synchronization—and compares their minimum spanning trees, hierarchical structure, statistical significance, robustness, and rolling network integration.

The public package intentionally focuses on the code and derived research outputs needed to audit the article. Development-history notes, version/fix comments, notebook execution outputs, local absolute paths, duplicate intermediate plots, raw market prices, and copies of third-party index documents have been removed.

## Repository contents

- `BMV_Hierarchy_PhysicaA.ipynb` — cleaned publication notebook.
- `requirements.txt` — environment used for reproduction; exact versions are pinned where recorded by the original run manifest.
- `results/` — curated derived tables that support the main manuscript claims.
- `figures/` — the seven manuscript figures in vector PDF format with embedded fonts.
- `provenance/analysis_manifest.json` — sanitized configuration/environment manifest.
- `provenance/source_checksums.csv` — SHA-256 checksums for excluded local source files.
- `data/README.md` — data access and redistribution rationale.
- `CITATION.cff` — citation metadata for GitHub/Zenodo archiving.

## Reproduce the analysis

1. Create a fresh Python environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Open `BMV_Hierarchy_PhysicaA.ipynb` and run all cells from top to bottom.
4. Generated full-run outputs are written to `./bmv_outputs/` and are intentionally ignored by Git.

The random seed is fixed at 42. Monte Carlo order-statistic inference uses 1,000 replicas for both the independence-permutation and independent circular-shift nulls in the archived analysis; degree-distribution inference uses the values recorded in the manifest.

## Data availability and licensing constraints

Underlying adjusted daily market prices were obtained through Yahoo Finance. They are not redistributed in this repository. Users should retrieve data from the original provider under its current terms. Likewise, copies of BMV/MexDer notices and the S&P/BMV IPC constituent export used during the research are not included. See `data/README.md` and `provenance/source_checksums.csv`.

Because third-party source data are excluded, a future rerun may differ slightly if the upstream provider revises historical adjusted prices or ticker availability. The curated derived tables preserve the exact results used for the manuscript, while the checksum documents the authors' original local market-data snapshot.

## Citation and archival release

The intended archival workflow is GitHub release `v1.0.0` → Zenodo GitHub integration → Zenodo DOI. The manuscript should cite the resulting software DOI after the release is archived. `CITATION.cff` is included so GitHub and Zenodo can ingest citation metadata without a competing `.zenodo.json` file.

## License

No software license has been asserted in this preparation copy. The repository owner should choose the intended code license before the public `v1.0.0` release. A permissive license such as MIT or BSD-3-Clause is common for research software, but that choice grants legal reuse rights and should be made by the authors.
