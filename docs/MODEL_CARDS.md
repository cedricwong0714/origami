# Model cards

One card per live calculator. A card describes software behaviour. It is not a validation.

Shared limits: `calibrated` is false. Human review is required before a wet-lab decision. A passing pytest run checks code and pinned figures, not a construct.

## Structure

| | |
|---|---|
| Entry | `GET /api/sa/scaffold/{n}`, wiki `/` |
| Inputs | Repeat count n, integer, 3 to 24 |
| Outputs | Contour (nm), axial span (Å), rigid vs flexible at a 15 nm contour cutoff, 95% chord band |
| Source | Deposited Cα screws, PDB 2AVP, 2HYZ, 2FO7, refit in this repository. Not a fusion crystal |
| Uncertainty | Linearised band from deposited scatter |
| Not included | Side-chain excluded volume (caller may set `ca_exclusion_A`; no literature radius is stored) |

## Stability

| | |
|---|---|
| Entry | `GET /api/stability/panel`, `GET /api/stability/thermo/prefill`, `POST /api/stability/thermo`, wiki `/stability` |
| Inputs | Series name (default Phillips 2012 CTPRa DSC). Calculator: Tm, ΔH_cal, ΔCp, temperature |
| Outputs | Tm and ΔG lookup; ΔG(T) from the Gibbs–Helmholtz equation with constant ΔCp |
| Source | Phillips 2012 table; ΔCp from Cortajarena & Regan 2011 Table I where the row exists. Implied ΔCp from printed ΔG is labelled derived, not literature |
| Uncertainty | Printed sigma when the table has one. Missing sigma stays null |
| Known gap | With those inputs, ΔG(10 °C) is 0.5–5.0 kcal/mol above Phillips’ printed ΔG. The test pins the gap. Series are not mixed. Lengths past the longest cited row are marked extrapolated |

## Docking and sterics

| | |
|---|---|
| Entry | `POST /api/ssdk/chassis` docking block, wiki `/ssdk` |
| Inputs | Repeat count, two site indices, two payload radii in Å. Default radius is the CaM–M13 complex size from PDB 2BBM |
| Outputs | Chord, facing cosine, clash probability on a placed Cα cloud, Gaussian-chain effective concentration |
| Source | Screw geometry above. Linker RMS from van Rosmalen, Krom & Merkx 2017 G4S2 persistence length (no printed standard error, so sigma is 0) |
| Uncertainty | Chord band from geometry scatter. Effective-concentration band when the linker model provides one |
| Not included | A sourced side-chain radius. Enzymes are literature-only and out of the wet plan |

## Kinetics

| | |
|---|---|
| Entry | `POST /api/kinetics/simulate`, wiki `/kinetics` |
| Inputs | Mode plus concentrations the caller types. Rates default to stored priors only when that mode says so |
| Outputs | Occupancy, time course, or complementation. Hypothesis-only when a required rate was not supplied |
| Priors | Free CaM–M13 peptide Kd 0.19 nM (Biochemistry 2006). Fusion apparent Ca²⁺ Kd 80 nM is secondhand (Nagai 2014 citing Porumb 1994), not the peptide Kd. Spy lumped rate 1.4×10³ M⁻¹ s⁻¹ (Zakeri 2012). Reversal was not observed; no numeric k_rev is stored. Recruitment k_on 1×10⁶ M⁻¹ s⁻¹ is an assumption and warns on every call. NanoBiT Kd 190 μM (Dixon 2016) |
| Not included | A three-step Spy decomposition with measured k_on, k_off, and k_bond |

## Active learning

| | |
|---|---|
| Entry | `POST /api/ssdk/learn`, wiki `/ssdk` and `/learn` |
| Older learner | Residual Gaussian process on the docking physics score. `next_n` is the next length to measure. Fewer than three distinct lengths does not optimise kernel hyperparameters |
| Multi-fidelity luminescence | Dry fidelity 0 = physics score. Wet fidelity 1 = caller `y`. Matérn-5/2 with one length scale per feature. 2×2 coregionalization. Dry noise fixed at 0.1 (prior choice; dry points have no replicates). One output: luminescence |
| Pass rule | Pass if μ − 1.96σ ≥ threshold. Threshold, assay CVs, and costs live in `data/config/active_learning_config.json` and are `unmeasured` or `prior_choice` until replaced |
| Acquisition | Expected improvement divided by cost. Cost unit is arbitrary |
| Not included | A joint model of five wet assays, heteroscedastic noise, constrained optimisation, batch expected improvement, ESM-2 features on this path |

Sequence encoding for a later construct model prefers ESM-2 and falls back to one-hot when the libraries are absent. The SSDK path above does not call it.

## Lab intake

| | |
|---|---|
| Entry | `GET /api/lab/schema`, `POST /api/lab/run`, `POST /api/lab/plate`, wiki `/lab` and `/intake` |
| Behaviour | A missing section stays “not submitted”. Plate CSV subtracts blanks per batch and records SHA-256 of the file text. Phase 3 `quality` replicates return a CV and a suggested observation σ. They do not edit the config file |
| Not a model | Prep flags and gel calls do not move screw coordinates or invent a payload radius |
