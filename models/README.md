# models/

Mathematical and ML artifacts for ORIGAMI.

| Path | Tracked in git? | Purpose |
|------|-----------------|---------|
| `kinetic_models/` | **Yes** (JSON defaults) | Mechanism rate priors used by profiles |
| `structure_predictions/` | Metadata only | AF3 / ESMFold outputs → prefer Zenodo for large PDBs |
| `benchmarks/` | **Yes** (index + tiny fixtures) | Held-out evaluation manifests |

Heavy binaries (checkpoints, full PDB libraries) must go to [Zenodo](https://zenodo.org) and be linked from the root README — do not commit multi‑MB weights here.
