# Bridging ratios

## Purpose
Turn the four luminescence tubes of the streptavidin bridging assay into three ratios and a sign pattern.

## Scientific basis
Signal over background is tube 2 / tube 1. Competition is tube 3 / tube 2. Hook is tube 4 / tube 2. The pattern is tube 2 above tube 1, and tubes 3 and 4 below tube 2. There is no fold-change cutoff.

## Inputs
Four RLU values. Optional replicate sigmas. Streptavidin setpoints, defaulting to 50 nM and 1 µM from the team protocol. Those defaults are experimental design choices, not a measured Kd.

## Outputs
Three ratios. A 95% band only when both sigmas in a quotient were supplied. `calibrated` is false.

## Assumptions
Background and bridge RLU are non-zero. The tubes were read inside the assay window.

## Known limitations
This is not a docking radius, not a sphere-clash probability, and not an enzyme flux.

## Parameter sources
No biological constants. Protocol setpoints are in `PROTOCOL_BRIDGE_M` and `PROTOCOL_HOOK_M`.

## Tests
`PYTHONPATH=/workspace python -m pytest tests/math_chassis/test_lab_chassis.py -q`

## Owner
Dry-lab / math chassis maintainers.
