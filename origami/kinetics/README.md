# Kinetics

## Purpose

Stage-1 scaffold kinetics: literature CaM–M13 recruitment and vacant SpyTag rate slots until wet-lab ingestion.

## Scientific basis

Langmuir recruitment (`origami.physical.recruitment`) and a two-step covalent mass-action ODE (`covalent.py`). SpyTag rates are not read from `models/kinetic_models/`.

## Inputs

See `docs/kinetics-workflow.md` and `GET /api/kinetics/schema`.

## Outputs

Schema JSON and simulate payloads with `calibrated: false`.

## Assumptions

Well-mixed compartments; explicit user rates for SpyTag time courses.

## Known limitations

Three SpyTag slots vacant; no automatic defaults.

## Parameter sources

`CAM_M13_KD_M` in `origami.priors`. SpyTag: none until stage-1 data.

## Tests

`pytest tests/math_chassis/test_kinetics.py`

## Owner

Math chassis team.
