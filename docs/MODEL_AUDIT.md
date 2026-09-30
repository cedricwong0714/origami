# Model audit

Fact-check of what is implemented. A passing test is not calibration.

## Verdict

| Model | Formula status | Biological status |
|---|---|---|
| CTPR helix | Coordinates from `src.core.ctpr_geometry` (`screw_point_nm`), converted at the boundary as 1 nm = 10 Å. `structural_report` adds pitch, repeats per turn, helix curvature and torsion, site phase, the worm-like-chain end-to-end RMS, and a comparison to the deposited C-alpha screw | Runtime rise is the mean of seven Kabsch/screw steps on PDB 2AVP, 2HYZ, and 2FO7 (Kajander et al. 2007, DOI 10.1107/S0907444907024353): **8.416 Å**. The previous CLASP prior was 11.0 Å. Twist stays **45°** because that angle is inside the deposited range 43.17–49.96° and keeps eight repeats per turn; the deposited mean twist is 46.01°. Rise and twist Jacobian sigmas are the sample standard deviations of those steps. The scaffold radius is the deposited repeat-centroid mean, **12.186 Å**. The docking radius is the inter-repeat junction mean, **12.363 Å**. Both sit inside the outer C-alpha shell (18.42–20.09 Å). The old cylinder was 18.0 Å and the old docking radius was 21.5 Å. Persistence length stays the 15 nm project cutoff. The article PDF was not open, so no sentence was copied from it. `calibrated` stays false |
| Scaffold thermal gate | Pass only when a supplied \(T_m\) row matches \(n\) and \(T_m > T_{\mathrm{assay}}\). No interpolation and no \(T_m(n)\) formula | Default prior is Phillips et al. 2012 CTPRa DSC, Table I, DOI 10.1002/pro.2018. Comparison temperature defaults to 37 C as an E. coli operating assumption, not a temperature from that table. The same table's unfolding ΔG at 10°C is reported and does not decide pass/fail. Among lengths that pass steric and Tm gates, the largest printed value in that column is named and does not change `next_n`. Cortajarena 2011 DSC, Phillips CTPRa CD, and Phillips CTPR DSC are separate named series. `stability_panel` reports all four at every library n and does not average them. The Phillips CTPR DSC series has its own same-table ΔG companion. The printed ΔG is that table cell and does not change when a user edits Tm. ΔG(Tm) = 0 is the two-state identity. A full Gibbs–Helmholtz curve still needs caller-supplied ΔHcal and ΔCp, which are not in the JSON. With an anchor ΔG and a Tm, an effective enthalpy is available only under the explicit assumption ΔCp = 0; that ΔH_eff is not the Phillips calorimetric ΔH. confidence tier hypothesis_only, extrapolation, `calibrated` stays false |
| Jacobian covariance | Correct first-order error propagation | σ on twist is large (~30% of the mean), so the linearization is approximate |
| Steric P(clash) | Gaussian delta method. Payload bodies are spheres. The scaffold is the placed C-alpha trace | Side chains are not in the trace, so the excluded volume is understated. Calling `clash_probability` without `cross_covariance` treats sites as independent and **overstates** distance noise. A caller mass can be compared to Erickson 2009 Rmin (eq 2.2, DOI 10.1007/s12575-009-9008-x); that bound is not the clash radius |
| Payload mass / sequence | Checksum of the typed protein sequence. Rmin = 0.066 M^{1/3} nm | Sequence is not generated here. OtsA/OtsB are still empty allowlist IDs. MW is not a Stokes radius |
| Joint failure probability | Product of (1−p) | Assumes independent clash events. Approximate |
| Worm-like-chain C_eff | Contact density with σ² = ⟨R²⟩ from the Kratky–Porod chain | One (GGGGS)3 tether uses b0 = 3.8 Å and the G4S2 persistence length 3.7 Å from van Rosmalen et al. 2017, DOI 10.1021/acs.biochem.7b00902. (GGGGS) is not G4S2. A pair adds the two variances. This is not a GP |
| Physics score | Defined scalar, not a law of nature | 1 mM reference inside the log is a unit choice, not a K_m |
| Matérn-5/2 GP | Standard kernel + Cholesky posterior. Affine (α, β) is **ridge-regularized toward (1, 0)** and not fit from fewer than 3 points | Learns residuals of S(n). Not trained on wet lab. Unregularized 2-point least squares was non-identifiable and produced ~10^7 means; that is a software bug, not biology | |
| BO (UCB, EI, entropy) | Standard discrete acquisition | Entropy is Gaussian differential entropy, not a full experimental Fisher design. Team lengths n=2, n=3, n=14, and n=20 are recorded beside the scan and are not training targets. n=14 is outside the default Phillips CTPRa DSC range, so the thermal mask does not rank it. The same `recommend` ranks Δi in the separation scan and is not a second learner |
| Repeat-count register | Comparison only. No new score | n=2 and n=20 are team bounds. n=3 is the biomarker measurement length. n=14 is the channeling candidate. `channeling_candidate_is_steric_minimum` is true only when the end-pair clash scan first clears the existing clash limit at n=14. The untrained acquisition is reported as `active_learner_next_n` and is not fitted to these lengths. `confirm_library` writes the same scan to one row per n for download |
| Repeat separation | Δi on one scaffold. Chord, phase, and facing from `structural_report`. Clash, `C_eff`, and the physics score from `physics_report`. A new unfitted `ResidualGP` then `recommend` ranks those scores | Δi is not total length n. The GP is not fit, so the posterior mean equals the physics score and the variance is flat. UCB therefore follows that score under `recommend`'s clash limit, including its fall-through. Repeat-count observations are not passed in. If the scaffold thermal state is not `pass` and not `not_scored`, `next_delta_i` is None. Multiples of one turn are flagged because the faces realign. Team length 14 is not a Δi target. `calibrated` and `gp_fitted` stay false |
| Recruitment ODE | Langmuir mass action; θ_ss = C/(C+Kd) | Kd = 0.19 ± 0.09 nM is the **peptide** value from Biochemistry 2006, 45:12547–12559, DOI 10.1021/bi060857u. Not a CLASP fusion. **No k_on in that paper** |
| Damköhler ODE | Da = k_capture/k_escape; P = Da/(1+Da); ODE matches that steady state | k_escape, k_cat/K_m, and v_prod are **caller inputs**. No enzyme constants are stored |

## What was wrong and is now explicit

1. `priors.py` used to say σ² = Nb²/3 while `linkers.py` implements σ² = ⟨R²⟩ = Nb². The comment now matches the code.
2. Clash variance previously added the two site covariances and dropped Cov(site i, site j). Shared helical-parameter error correlates the sites, so the old variance was too large. `steric_report` passes the cross-covariance.

## Still not claimed

- No project wet-lab fit.
- No 3D reaction–diffusion PDE.
- No Michaelis–Menten saturation inside the channel (capture is the unsaturated limit).
- Calcium gating is a binary `signal_on` switch, not a four-site Ca²⁺ binding model.
