# SSDK completion roadmap

Engineering-readiness estimate for the Structure, Stability, Docking, and Kinetics chassis, plus the lab-independent models and the GP, Bayesian optimization, and XGBoost layers.

These percentages measure whether the software can run, cite its inputs, carry uncertainty, accept the planned data, and be tested. They are not calibration scores. A passing test is not scientific validation, and `calibrated` stays false until a project dataset is approved for that claim.

Audit date: 2026-10-02, branch `cursor/origami-math-engine-9d85` at the time of the audit.

## Scorecard

| Slice | Engineering readiness | Present | Remaining |
|---|---:|---|---|
| Structure | 92% | Deposited Cα screw, chord, phase, WLC flexibility, Jacobian uncertainty, canonical payload library & Erickson 2009 scaling | Side-chain excluded volume, per-construct Cryo-EM coordinates |
| Stability | 80% | Phillips 2012 CTPRa Tm and ΔG length models, identifiability fallback, Gibbs–Helmholtz arithmetic | ΔHcal and ΔCp are absent from the checked-in table, so the full curve stays conditional |
| Docking | 82% | Chord, clash, Gaussian-chain effective concentration, tethered Spy and NanoBiT outputs, structured payload lookup | Linker standard error was not printed in the source paper |
| Kinetics | 75% | Peptide CaM–M13 occupancy, lumped Spy ODE, optional three-step Spy ODE, NanoBiT ODE, Damköhler transfer, OtsA/OtsB literature constants | Wet-lab recruitment kon and fusion Kd remain vacant until assay ingestion |
| SSDK orchestration | 85% | `POST /api/ssdk/chassis`, `POST /api/ssdk/learn`, residual Matérn GP, UCB / EI / entropy, lab intake GP wiring | Single unified CLI entry point across all four slices |
| Gaussian process | 85% | Custom Cholesky Matérn GP, sklearn Matérn GP, and an older RBF time-series GP | Grouped validation across batch effects |
| Bayesian optimization | 82% | Discrete UCB, EI, entropy, and continuous EIG / UCB / EI | Multi-objective Pareto frontier across stability vs throughput |
| XGBoost | 75% | Optional residual meta-learner gated at 15 rows, LOO RMSE evaluation, trained on GP residual, uncertainty propagation | Prospective validation on wet-lab held-out plates |
| Stacked ensemble | 80% | Mechanistic prediction, then GP residual, then optional XGBoost meta-correction with combined uncertainty propagation | Prospectively calibrated multi-plate dataset |
| Lab-data intake | 80% | Prep, assay window, calcium, lock, bridging slots, and optional residual GP fitting to physics scores | Automated plate reader CSV/JSON parsing pipeline |

Goal-level reading of the same tree: non-negotiable MVP about 85%, strong competition version about 70%, lab-independent mathematical models about 85%. A prospectively calibrated predictor is not a current claim.

## What the lab will measure

The intake schema accepts preparation concentration and solubility, a standard curve, furimazine half-life, CV, a calcium dose–response, scrambled-M13 ratio, luminescence at 25 °C, 30 °C, and 37 °C, a SpyCatcher lock time course, and four bridging tubes.

The same schema records these as not collected: melting temperature, circular dichroism, size-exclusion volume, cryo-EM coordinates, payload radius, fusion CaM–M13 Kd, SpyCatcher k_rev, SpyCatcher k_bond, and enzyme k_cat / K_m.

Literature or structure has to carry every quantity on that second list. The lumped Zakeri rate remains the covalent model until a source actually measures the three-step decomposition.

## Short term

1. Keep one model matrix: equation, units, source, uncertainty, interpolation domain, lab or literature status, confidence tier, entry point, and test.
2. Resolve the scaffold-length lists. The structural UI uses 3, 8, and 14. The lab schema names 8, 14, and 17. Other registers mention 2, 3, 14, and 20.
3. Keep the test suite installable from `pip install -e ".[dev]"`. API tests need FastAPI and an HTTP client. The XGBoost fit needs the optional package in that same extra until CI grows a separate ML job.
4. Keep numeric goldens aligned with sourced parameter changes. The calcium occupancy golden was realigned to the Biochemistry 2006 peptide Kd already in `CAM_M13_KD_CA_SAT_M`. The constant was not edited again.
5. Retrieve, rather than invent, payload radii, Phillips ΔHcal and ΔCp where the paper prints them, and enzyme constants for the exact constructs and conditions. Leave a slot null when the source does not print the number.
6. Give `origami freeze` an honest uncertainty label. The command still uses a fixed ±30% band because `predict_luminescence` does not propagate parameter error. The file now names that method.

## Long term

1. Finish lab-independent inputs. Every non-lab parameter is sourced, bounded, or explicitly null. Every prediction carries uncertainty, a confidence tier, and an extrapolation flag.
2. Keep one residual-GP interface and one acquisition interface. Domain code supplies features and constraints. Physics remains the mean function.
3. Connect approved observations to the physics score on the same scale. Fit the SSDK residual only after the target, units, and batch metadata are explicit.
4. Extend Bayesian optimization with pending experiments, replicate-versus-new-design choice, assay cost, and a written reason for each recommendation.
5. Activate XGBoost only after grouped validation shows a gain over the mechanistic model plus the GP, and only after the tree layer has its own uncertainty. Fifteen rows are a software gate, not evidence that the fit is identifiable.
6. Freeze predictions before looking at held-out outcomes. Report coverage, error, rank correlation, and an ablation of physics, GP, and XGBoost.
7. Leave a 3D reaction–diffusion model as a stretch goal. The current Damköhler reduction is the model the stored inputs can support.

## Known duplication

`origami.design_engine.gp.ResidualGP` and `src.gp_model.residual_gp.ResidualGP` are separate implementations. A third RBF GP still serves the older Learn time-series path. Acquisition is likewise split between `origami.design_engine.active_learning` and `src.experiment_design`. Consolidation is a later change. This roadmap does not merge them in place.

## Owner

Dry-lab and math-chassis maintainers. Human review is required before any number from this roadmap is treated as a wet-lab decision.
