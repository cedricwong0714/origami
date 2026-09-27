# ORIGAMI design sandbox

## Purpose

Local input → process → result view for one CLASP scaffold. The form calls
`origami.engine.run_design`. It does not add a second scorer.

## Scientific basis

Geometry, clash, linker width, thermal gate, and occupancy are the same
functions the math chassis already uses. Sources stay on those parameters
(`origami/priors.py`, `origami/stability/series.py`, `origami/linker_prior.py`).
This module does not introduce a new biological constant.

## Inputs

- `design_id`: string
- `n_repeats`: integer in [3, 24]
- optional payload rows with `payload_id`, `role`, `fusion_terminus`,
  `repeat_index`, `radius_A` (Å), `linker_sigma_A` (Å), optional
  `protein_sequence`, and optional `mw_Da` + `mw_source`
- optional `thermal_prior` and `t_assay_C` (°C)
- optional user-entered observations `{n_repeats, y, source}`

## Outputs

`run_sandbox` returns `input`, `process`, `result` (`DesignReport.to_dict()`),
and the n-library posterior arrays. `calibrated` is false.

## Assumptions

The sandbox only wraps existing engine behavior. Empty payloads use the
default 25 Å heuristic radius on each end repeat.

## Known limitations

No sequence export. Sequences are only stored as typed, with a checksum.
Mass is not converted into the clash radius. The residual GP stays unfitted
until the caller enters y. Payload shape is still a sphere.

## Parameter sources

None added here. See `origami/priors.py`.

## Tests

```bash
python -m pytest tests/unit_tests/test_sandbox_service.py
```

## Owner

Hong Kong team ORIGAMI software.
