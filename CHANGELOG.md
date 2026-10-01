# Changelog

## Unreleased — 2026-10-01 (lab chassis)

### Added
- Lab intake for the experiments in the current plan: prep concentration and gel calls, standard curve, furimazine half-life, CV, calcium logistic EC50, scrambled-M13 ratio, luminosities at 25 °C, 30 °C, and 37 °C, SpyCatcher lock progress curve, and four-tube bridging ratios.
- `GET /api/lab/schema` and `POST /api/lab/run`. The wiki page is `/lab`.
- EC50 does not replace the CaM–M13 peptide Kd. Lock fits one lumped rate or a caller-chosen pseudo-first-order rate. `k_rev` and `k_bond` are not fit. A rate whose 95% band reaches zero is omitted. Bridging ratios have no fold-change cutoff.
- Melting temperature, payload radius, fusion Kd, and enzyme k_cat / K_m are not slots. The residual Gaussian process stays unfitted. `calibrated` stays false. A passing test is not scientific validation.
  Reviewed by: not a human wet-lab review.

## Unreleased — 2026-09-30 (kinetics literature priors)

### Added
- Stage-1 kinetics uses sourced literature priors so recruitment and covalent simulate can run before lab data. CaM–M13 Kd stays the Biochemistry 2006 peptide value (DOI 10.1021/bi060857u). Spy k_on is Zakeri et al. 2012 PNAS 1.4e3 ± 43 M^-1 s^-1 (DOI 10.1073/pnas.1115485109; SpyTag-MBP + SpyCatcher, 10 μM, 25 °C, SDS-PAGE). Default covalent path is lumped irreversible bimolecular adduct. spy_k_rev and spy_k_bond stay vacant until lab ingestion. NanoBiT Kd 190 μM, kon ≈ 500 M^-1 s^-1, koff 0.2 s^-1 from Dixon et al. 2016 (DOI 10.1021/acschembio.5b00753) are listed, not simulated. `calibrated` stays false. `confidence_tier` is `hypothesis_only`. Lab override fields are empty. Passing tests is not scientific validation.
  Reviewed by: not a human wet-lab review.

## Unreleased — 2026-09-30 (ΔG length-fit identifiability)

### Changed
- A saturating length fit is not reported when any coefficient standard error is not finite, or when the prediction sigma at n = 3, 8, or 14 is larger than the absolute prediction. That observable falls back to `y(n) = a + b*n` on the same rows. The shown value and 95% band are that line. If the line is also non-identifiable, no point value is reported. For unfolding ΔG the warning is: the rows do not determine ΔG(n).
- Phillips 2012 CTPRa DSC unfolding ΔG uses that line. The saturating coefficients are not shown. The Tm fit for that series stays the saturating form. `calibrated` stays false. Model version of `ctpr_length_curve` is 2.
  Reason: the saturating ΔG covariance was not an interior estimate (`y_1` on the positivity floor; 95% bands thousands of kcal mol-1 wide). Non-identifiable parameters are not presented as fitted values.
  ΔHcal and ΔCp were not added. `ctpr_thermal_literature.json` was not edited. Series are not averaged.
  Reviewed by: not a human wet-lab review. A passing test of this fit is not scientific validation.

## Unreleased — 2026-09-30 (per-series length fit)

### Added
- `origami/stability/length_fit.py` fits one series at a time. With at least four Tm or ΔG points the model is `y(n) = y_inf - (y_inf - y_1) * exp(-(n-1)/lambda)`, with `y_inf`, `y_1`, and `lambda` positive. With two or three points the model is `y(n) = a + b*n`. Fewer than two points are not fit.
- `GET /api/stability/confirm` evaluates that model at n = 3, 8, and 14. The comparison at 37 °C uses the calculated melting temperature. A 95% band is value ± 1.96 σ from the linearized `curve_fit` covariance and is labeled a linear approximation, not a wet-lab confidence interval. `confidence_tier` is `hypothesis_only`. `calibrated` stays false.
- The literature lookup remains `stability_panel` and `GET /api/stability/panel`. A paper cell is returned as `paper_tm_C` or `paper_delta_g` when a row exists. It is not the primary number.
  Reason: the confirmation screen was leaving n = 14 blank. The number is now the model at that length. n = 14 is past the longest cited length in each checked-in series, and the payload says so.
  ΔHcal and ΔCp were not added. They are not in `ctpr_thermal_literature.json` and they are not estimated here. Series are not averaged. Cortajarena's missing ΔG column is not filled from Phillips.
  Reviewed by: not a human wet-lab review. A passing test of this fit is not scientific validation.

## Unreleased — 2026-09-30 (confirmation page uncertainty)

### Changed
- `stability_panel` and `GET /api/stability/confirm` omit the Tm interval when the literature row prints no Tm uncertainty. `thermal_gate` still uses a zero-width envelope for pass/fail. The confirmation page shows that missing sigma as omitted. n = 14 stays extrapolated on all four series. Phillips 2012 CTPRa CD and CTPR DSC stay extrapolated at n = 8.
  Reviewed by: not a human wet-lab review. A passing test of this lookup is not scientific validation.

## Unreleased — 2026-09-30 (ΔCp = 0 uncertainty)

### Added
- `effective_enthalpy_delta_cp_zero` propagates a caller-supplied anchor ΔG sigma and Tm sigma by a first-order delta method. The 95% band is value ± 1.96 σ and is labeled as a linear approximation, not a wet-lab confidence interval. At the anchor temperature the band matches the anchor uncertainty. A missing sigma stays null and is not replaced with zero.
- `stability_panel` copies the printed Tm uncertainty. A null table uncertainty is no longer reported as 0.
  Reviewed by: not a human wet-lab review. A passing test of this arithmetic is not scientific validation.

## Unreleased — 2026-09-30 (ΔCp = 0 effective enthalpy)

### Added
- When the caller supplies a finite Tm and a finite anchor ΔG at a known reference temperature, `effective_enthalpy_delta_cp_zero` reports ΔH_eff = ΔG(T_ref) / (1 − T_ref/Tm), ΔG(T) = ΔH_eff (1 − T/Tm), and ΔS_eff = ΔH_eff / Tm, temperatures in kelvin, only under the explicit assumption ΔCp = 0.
- ΔH_eff is an effective enthalpy under that assumption. It is not the Phillips et al. 2012 DSC ΔHcal. No ΔHcal or ΔCp was added to `ctpr_thermal_literature.json`. The printed Table I ΔG cell is unchanged when Tm changes. confidence tier is hypothesis_only, is_extrapolation is true, and calibrated stays false. A missing anchor does not invent ΔG(T). Tm equal to the anchor temperature is refused because ΔH is not identifiable.
  Reviewed by: not a human wet-lab review. A passing test of this arithmetic is not scientific validation.

## Unreleased — 2026-09-30 (Gibbs–Helmholtz calculator)

### Added
- Two-state Gibbs–Helmholtz arithmetic for caller-supplied ΔHcal, ΔCp, and Tm. ΔH(T) = ΔHcal + ΔCp (T − Tm), ΔS(T) = ΔHcal/Tm + ΔCp ln(T/Tm), ΔG(T) = ΔH(T) − T ΔS(T), with temperatures in kelvin. ΔG(Tm) is 0 when the inputs are consistent.
- The literature table still has only Tm and printed ΔG. ΔHcal and ΔCp are not stored and are not back-calculated. A missing calorimetry input returns no curve. `calibrated` stays false. The curve is not a measurement of the Hong Kong team fusion.
  Reviewed by: not a human wet-lab review.

## Unreleased — 2026-09-27 (teammate checkpoint)

### Added
- Saved n=8 dry-lab JSON/CSV after the chassis/sandbox-related pytest pass, plus a static viewer in `web/checkpoint/` for a temporary Vercel drop. The page does not run the models. `calibrated` stays false.
  Reviewed by: not a human wet-lab review.

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
