# Provenance

This directory records the reproducibility boundary for the manuscript-aligned `v1.1.0` release.

- `analysis_manifest.json` — sanitized configuration/environment manifest from the archived analysis.
- `source_checksums.csv` — SHA-256 hashes for excluded local third-party source files.
- `ipc_composition_history.csv` — derived long-form representation of the official IPC composition snapshots used for turnover analysis. Original exchange/index documents are not redistributed.
- `ipc_issuer_aliases.csv` — mapping used to collapse documented ticker/share-series transitions to issuer-level turnover.
- `ipc_corporate_actions.csv` — documented corporate-action/ticker-transition records used by the turnover audit.
- `ipc_history_gaps.csv` — intervals where the composition history spans more than the regular reconstitution cadence.
- `frozen_manuscript_sha256.txt` — hash of the manuscript version audited against this release.

The derived provenance tables do not replace the original official notices; they make the exact transformation used by the public code auditable while respecting redistribution constraints.
