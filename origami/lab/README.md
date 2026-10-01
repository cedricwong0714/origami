# Lab intake

## Purpose
One schema and one run for the experiments this team is actually performing: prep gels and concentration, assay window, calcium dose–response, SpyCatcher lock times, and the four-tube bridge.

## Scientific basis
Each section calls the matching equation. Prep does not update the screw. Calcium EC50 is not a Kd. The lock fit is one lumped rate. Bridging output is three ratios.

## Inputs
`POST /api/lab/run` with any subset of `prep`, `assay_window`, `calcium`, `lock`, and `bridging`.

## Outputs
A report whose `calibrated` field is false. Sections that were not filled in say so.

## Assumptions
The caller’s numbers are already in the units named on the schema.

## Known limitations
Melting temperature, payload radius, fusion Kd, k_rev, k_bond, and enzyme k_cat / K_m are not slots. The residual Gaussian process stays unfitted because these assays have no physics score on the luminescence scale.

## Parameter sources
The lock section echoes the Zakeri 2012 literature k_on from `origami.priors.SPY_K_ON_PER_M_S` as a reference beside a lab fit. It does not overwrite that prior.

## Tests
`PYTHONPATH=/workspace python -m pytest tests/math_chassis/test_lab_chassis.py -q`

## Owner
Dry-lab / math chassis maintainers.
