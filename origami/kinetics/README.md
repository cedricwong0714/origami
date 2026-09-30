# Kinetics

## Purpose

Stage-1 scaffold kinetics: literature CaM–M13 Kd and Zakeri Spy k_on so models can run; vacant lab k_rev/k_bond until ingestion.

## Scientific basis

Langmuir recruitment and a lumped irreversible Spy adduct (or a 3-step ODE when lab rates are supplied). See `docs/kinetics-workflow.md`.

## Inputs

See `GET /api/kinetics/schema`.

## Outputs

Schema JSON and simulate payloads with `calibrated: false` and `confidence_tier: hypothesis_only`.

## Assumptions

Well-mixed compartments. Literature numbers are not fusion assays.

## Known limitations

Spy k_rev and k_bond vacant. NanoBiT listed, not integrated.

## Parameter sources

`CAM_M13_KD_M`, `SPY_K_ON_PER_M_S`, Dixon NanoBiT constants in `origami.priors`.

## Tests

`pytest tests/math_chassis/test_kinetics.py`

## Owner

Math chassis team.
