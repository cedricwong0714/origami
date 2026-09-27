# Model audit

Fact-check of what is implemented. A passing test is not calibration.

## Verdict

| Model | Formula status | Biological status |
|---|---|---|
| CTPR helix | Coordinates from `src.core.ctpr_geometry` (`screw_point_nm`), converted at the boundary as 1 nm = 10 Å. `structural_report` adds pitch, repeats per turn, helix curvature and torsion, site phase, and the worm-like-chain end-to-end RMS from `wlc_mean_square_end_to_end` | Canonical values are rise **11.0 Å** (1.1 nm), twist **45°** (π/4 rad), docking radius **21.5 Å** (1.8 + 0.35 nm), scaffold cylinder **18.0 Å**. Eight repeats complete one turn (Kajander et al. 2007). Contour is `n * rise`, matching `generate_scaffold_geometry`. Persistence length is `PERSISTENCE_LENGTH_NM` (15 nm) from that module, a CLASP-docs rigid-rod cutoff, not a new measurement. Jacobian sigmas in `origami/priors.py` are still the previous engineering widths, not `DEFAULT_RISE_STD_NM` / `DEFAULT_TWIST_STD_DEG`. Chord intervals propagate those widths. `calibrated` stays false |
| Scaffold thermal gate | Pass only when a supplied \(T_m\) row matches \(n\) and \(T_m > T_{\mathrm{assay}}\). No interpolation and no \(T_m(n)\) formula | Default prior is Phillips et al. 2012 CTPRa DSC, Table I, DOI 10.1002/pro.2018. Comparison temperature defaults to 37 C as an E. coli operating assumption, not a temperature from that table. The same table's unfolding ΔG at 10°C is reported and does not decide pass/fail. Among lengths that pass steric and Tm gates, the largest printed value in that column is named and does not change `next_n`. Cortajarena 2011 DSC, Phillips CTPRa CD, and Phillips CTPR DSC are separate named series. The Phillips CTPR DSC series has its own same-table ΔG companion. `calibrated` stays false |
| Jacobian covariance | Correct first-order error propagation | σ on twist is large (~30% of the mean), so the linearization is approximate |
| Steric P(clash) | Gaussian delta method on sphere–sphere distance | Spheres, not molecular surfaces. `steric_report` now includes site–site covariance. Calling `clash_probability` without `cross_covariance` treats sites as independent and **overstates** distance noise |
| Joint failure probability | Product of (1−p) | Assumes independent clash events. Approximate |
| Gaussian-chain C_eff | Standard ideal-chain contact density with σ² = ⟨R²⟩ | σ = 18 Å is **not** a measured persistence length. This is not a GP |
| Physics score | Defined scalar, not a law of nature | 1 mM reference inside the log is a unit choice, not a K_m |
| Matérn-5/2 GP | Standard kernel + Cholesky posterior. Affine (α, β) is **ridge-regularized toward (1, 0)** and not fit from fewer than 3 points | Learns residuals of S(n). Not trained on wet lab. Unregularized 2-point least squares was non-identifiable and produced ~10^7 means; that is a software bug, not biology | |
| BO (UCB, EI, entropy) | Standard discrete acquisition | Entropy is Gaussian differential entropy, not a full experimental Fisher design. Team lengths n=2, n=3, n=14, and n=20 are recorded beside the scan and are not training targets. n=14 is outside the default Phillips CTPRa DSC range, so the thermal mask does not rank it |
| Repeat-count register | Comparison only. No new score | n=2 and n=20 are team bounds. n=3 is the biomarker measurement length. n=14 is the channeling candidate. `channeling_candidate_is_steric_minimum` is true only when the end-pair clash scan first clears the existing clash limit at n=14. The untrained acquisition is reported as `active_learner_next_n` and is not fitted to these lengths |
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
