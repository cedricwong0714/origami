# Changelog

## Unreleased — 2026-09-27

### Changed
- CTPR axial rise: changed from 1.1 nm (11.0 Å) to 0.8416139416984938 nm (8.416139416984938 Å).
  Reason: the runtime screw was outside the repeat-to-repeat screws fitted to deposited C-alpha coordinates.
  Old source: CLASP docs prior (Dueber et al. 2009; SCABs 2024), not a crystal refit.
  New source: PDB 2AVP, 2HYZ, and 2FO7, cited by Kajander et al. (2007) Acta Crystallogr D 63:800–811, DOI 10.1107/S0907444907024353. Mean of seven Kabsch screw steps on 34-residue blocks. The article PDF was not open; the value is not a sentence from that PDF.
  Impact: axial separations, pitch, contour length, chord distances, clash probabilities, effective concentrations, and both acquisition recommendations.
  Reviewed by: not a human wet-lab review. `calibrated` stays false.
- CTPR rise uncertainty: changed from 2.0 Å to 0.4760507886412968 Å.
  Reason: the previous width was an engineering Jacobian sigma.
  New source: sample standard deviation (divisor n−1) of the same seven deposited steps.
  Impact: chord intervals and clash probabilities.
- CTPR twist uncertainty: changed from 0.12 rad to 0.04096380633913714 rad (2.3470532160238053°).
  Reason: same deposited sample standard deviation.
  The twist mean stays 45°. That angle is inside the deposited range and still puts eight repeats in one turn.
  Impact: chord intervals and clash probabilities.

### Unchanged
- Scaffold cylinder radius 1.8 nm and docking radius 21.5 Å. The deposited outer C-alpha shell is 18.42–20.09 Å, and the repeat-centroid radius is about 12.19 Å. Those radii were not substituted.
- Persistence length 15 nm. It is not in the deposited coordinate table.
- Team lengths 2, 3, 14, and 20. They are still not acquisition targets.
