# Model audit

Fact-check of what is implemented. A passing test is not calibration.

## Verdict

| Model | Formula status | Biological status |
|---|---|---|
| CTPR SE(3) helix | Correct rigid-body composition | Rise 9 Å, twist 0.42 rad, radius 22 Å are **engineering priors**, not a refit of PDB 2AVP/2HYZ |
| Jacobian covariance | Correct first-order error propagation | σ on twist is large (~30% of the mean), so the linearization is approximate |
| Steric P(clash) | Gaussian delta method on sphere–sphere distance | Spheres, not molecular surfaces. `steric_report` now includes site–site covariance. Calling `clash_probability` without `cross_covariance` treats sites as independent and **overstates** distance noise |
| Joint failure probability | Product of (1−p) | Assumes independent clash events. Approximate |
| Gaussian-chain C_eff | Standard ideal-chain contact density with σ² = ⟨R²⟩ | σ = 18 Å is **not** a measured persistence length. This is not a GP |
| Physics score | Defined scalar, not a law of nature | 1 mM reference inside the log is a unit choice, not a K_m |
| Matérn-5/2 GP | Standard kernel + Cholesky posterior | Learns residuals of S(n). Not trained on wet lab |
| BO (UCB, EI, entropy) | Standard discrete acquisition | Entropy is Gaussian differential entropy, not a full experimental Fisher design |
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
