# SSDK surrogate learning

## Purpose
Run structure, stability, docking, and kinetics as separate models, then let a small set of surrogate readouts update the residual on the docking score and recommend the next length.

## Scientific basis
The docking score is `(1 − P_instability) × log10(1 + C_eff / 1 mM)`. The 1 mM denominator is the ranking convention already in `origami.physical.score`, not a measured K_m. The residual model is `y = α S + β + r(n) + ε` with a Matérn-5/2 kernel. α stays 1 until three distinct lengths are present. Acquisition is constrained UCB, expected improvement, or posterior entropy over the discrete repeat counts.

## Inputs
Surrogate rows: repeat count, readout, optional sigma. Optional payload radii in angstroms. Optional kinetics block with SpyTag and SpyCatcher concentrations and an optional lab k_lock.

## Outputs
A posterior mean and 95% band at each candidate length, the next length to measure, screw contour, Phillips 2012 CTPRa DSC Tm and ΔG at the highlighted lengths, and a kinetics time course only when that block is posted. `calibrated` is false. `gp_fitted` is true only at three or more distinct lengths.

## Assumptions
The surrogate y is on one scale across lengths. Radii, when omitted, are the 25 Å placeholder and are named as such.

## Known limitations
The surrogate does not edit the screw, the melting-temperature model, or the Zakeri k_on. Stability does not veto a length in this search. Passing tests are not scientific validation.

## Parameter sources
Screw geometry, Phillips 2012 CTPRa DSC, the linker RMS, the CaM–M13 peptide Kd, and the Zakeri 2012 k_on stay in `origami.priors` and the stability table. Surrogate y is not a prior.

## Tests
`PYTHONPATH=/workspace python -m pytest tests/math_chassis/test_ssdk_learn.py tests/math_chassis/test_active_learning.py -q`

## Owner
Dry-lab / math chassis maintainers.
