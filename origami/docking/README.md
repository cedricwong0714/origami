# Docking

## Purpose
Place two payloads on the CTPR screw and report the chord, the clash probability, and the Gaussian-chain effective concentration.

## Scientific basis
The chord, its sigma, and the facing cosine come from `structural_report`. Clash uses the delta method on the deposited Cα cloud. Effective concentration is

C_eff(r) = (3 / (2 π σ²))^(3/2) exp(−3 r² / (2 σ²))

converted from per Å³ to molar with Avogadro's number. σ for a pair of tethers is the root-sum-square of the two linker RMS values.

## Inputs
Repeat count, two repeat indexes, two radii in angstroms, and an optional linker RMS. Indexes default to the N terminus and the named graft (or the C terminus when that length has no graft).

## Outputs
Chord with its existing 95% band. Clash and C_eff only when both radii were supplied. The C_eff band is value ± 1.96 σ from dC/dr times the chord sigma. When C_eff exists, `local_kinetics` maps it through the Zakeri 2012 k_on (`k_obs = k_on * C_eff`) and the Dixon 2016 printed Kd (`θ = C_eff / (C_eff + Kd)`). `k_rev` and `k_bond` stay null. `calibrated` is false.

## Assumptions
Each payload is a sphere on a radial standoff of one linker RMS plus its radius. The two tethers are independent.

## Known limitations
A missing radius stops clash, C_eff, and the tethered rate. The 25 Å placeholder is not used. Linker uncertainty is omitted because the source printed no standard error. The tethered Spy step is not the well-mixed 10 μM Zakeri condition. NanoBiT θ uses the printed 190 μM Kd. `k_off / k_on` is reported beside it and is not substituted.

## Parameter sources
Linker RMS: van Rosmalen, Krom, Merkx (2017), DOI 10.1021/acs.biochem.7b00902, via `origami.priors.LINKER_SIGMA_A`. Screw parameters stay in the geometry priors.

## Length sweep
`sweep_lengths` evaluates the Phillips length-model melt once, then the affinity check at every repeat count from 3 to 24. It does not add a rate or a cutoff. The marked length is the highest LgBiT–SmBiT occupancy among lengths that pass the assay-temperature comparison and whose association holds. A tie takes the shorter scaffold. That mark is a ranking rule, not a validated optimum. `calibrated` stays false.

## Tests
`PYTHONPATH=/workspace python -m pytest tests/unit_tests/test_docking_sweep.py tests/unit_tests/test_docking_affinity.py tests/math_chassis/test_ssdk_chassis.py tests/math_chassis/test_docking_kinetics_engine.py -q`

## Owner
Dry-lab / math chassis maintainers.
