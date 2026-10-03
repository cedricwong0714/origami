# data/predictions/frozen/

Frozen prospective predictions (CLASP Docs §1.6). Each file is written before
the corresponding wet-lab experiment runs and carries a SHA-256
`file_checksum` so any later modification is detectable.

Do not edit files here by hand. Frozen predictions are produced by
`src/predictions/freeze.py` and are immutable once written.

`scaffold-n3.json`, `scaffold-n8.json`, and `scaffold-n14.json` are
examples for the planned repeat counts. Contour, axial span, and the
Phillips length curve change with n. The calcium luminescence curve in
those files does not: `predict_luminescence` has no repeat-count
argument. Its interval is the fixed ±30% placeholder
(`fixed_relative_placeholder_pm_30_percent`), `confidence_tier` is
`hypothesis_only`, and `calibrated` is false. Regenerating them after a
model change requires a new prediction id, or `overwrite=True` with the
reason recorded in `CHANGELOG.md`.
