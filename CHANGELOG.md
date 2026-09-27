# Changelog

## Unreleased — 2026-09-27 (dry-lab measurements)

### Added
- `stability_panel` reports Phillips 2012 CTPRa DSC, Phillips 2012 CTPRa CD, Phillips 2012 CTPR DSC, and Cortajarena 2011 CTPRa DSC separately. They are not averaged. Missing n stays extrapolated.
- `drylab_dataset` stores structural measurements (contour, chord, facing, clash, C_eff, Cα radial extent, Δi scan) and the next measurement coordinates. `next_n` and `next_delta_i` are coordinates to measure, not use-case optima. The residual GP is not fit on these scores. `calibrated` stays false.
  Reviewed by: not a human wet-lab review.

## Unreleased — 2026-09-27 (sandbox confirmations)

### Added
- `confirm_library` exports one row per n = 3..24: screw contour, rigid-rod flag, end-pair chord, physics score, clash, Phillips 2012 CTPRa DSC gate, and printed ΔG.
- `geometry_scene` exports the placed Cα cloud and payload centers for the scaffold that was run.
- The sandbox shows those tables, a CSV download, and the Cα plot. `calibrated` stays false. No Tm(n) model was added.
  Reviewed by: not a human wet-lab review.

## Unreleased — 2026-09-27 (payload sequence and mass)

### Added
- Optional `protein_sequence` (canonical amino acids + SHA-256) and `mw_Da` + `mw_source` on payload import.
- Erickson (2009) eq 2.2 Rmin from that mass (DOI 10.1007/s12575-009-9008-x). Rmin is a lower bound. It is not written into `radius_A`.
  Reviewed by: not a human wet-lab review.

## Unreleased — 2026-09-27 (design sandbox)

### Added
- `sandbox/service.py` and `sandbox/app.py` wrap `run_design` for input, process, and result data.
  The sandbox does not add a scorer. `calibrated` stays false. `next_n` is labeled as acquisition, not a team optimum.
  Reviewed by: not a human wet-lab review.

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
- Persistence length 15 nm. It is not in the deposited coordinate table.
- Team lengths 2, 3, 14, and 20. They are still not acquisition targets.
- The residual GP is still unfitted. The retrieved literature has no assay of the design score, so it was not trained on a substitute target. `calibrated` stays false.

## Unreleased — 2026-09-27 (geometry follow-up)

### Changed
- Scaffold radius: changed from 1.8 nm (18.0 Å) to 1.2185585199113613 nm (12.185585199113614 Å).
  Reason: 1.8 nm was a cylinder prior, not the repeat centroid.
  New source: mean centroid radius of the same seven deposited screw steps.
  Impact: backbone curvature. Payload clash no longer uses this radius as a cylinder.
- Docking radius: changed from 21.5 Å to 12.363166305578243 Å.
  Reason: the 0.35 nm loop offset had no source.
  New source: mean radial distance of the inter-repeat junction (midpoint of C-alpha 34 and the next C-alpha 1) on those seven steps.
  Impact: docking-site coordinates, chords, clash, and effective concentration.
- Linker width: changed from 18 Å to the Kratky–Porod RMS of one (GGGGS)3 chain.
  Source: van Rosmalen, Krom, and Merkx (2017) Biochemistry 56:6565–6574, DOI 10.1021/acs.biochem.7b00902. Residue length 3.8 Å. G4S2 persistence length 3.7 Å.
  (GGGGS) is not G4S2. The persistence length was not interpolated. No standard error was printed, so the parameter sigma is 0.
  Impact: payload standoff and C_eff. A pair of tethers adds the two variances.
- Payload clash: the scaffold body is the placed C-alpha trace. The payload remains a sphere of the caller radius around a center one tether RMS out from the junction.
  Reviewed by: not a human wet-lab review. `calibrated` stays false.
