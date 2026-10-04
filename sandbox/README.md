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
the n-library posterior arrays, a `confirmation` table (structure + thermal
gate + physics for n = 3..24), a `scene` of the placed Cα cloud, and a `drylab` measurement set
(structure rows, an unmixed stability panel, and the next n and Δi to measure).
`calibrated` is false. The residual GP is not fit on the dry-lab scores.

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
python -m pytest tests/unit_tests/test_sandbox_service.py tests/unit_tests/test_modelling_sandbox.py
```

## Live modelling sandbox

`sandbox/modelling.py` scores one length, a length series, binding, and a
next-length suggestion. It calls `evaluate_chassis`, `simulate_kinetics`,
and `learn_ssdk`. Clash needs two radii. Binding needs concentrations.

```bash
pip install -e ".[ui]"
streamlit run sandbox/modelling.py --server.port 48621 --server.address 0.0.0.0
```

Root entry: `host_modelling.py`.

## Owner

Hong Kong team ORIGAMI software.
