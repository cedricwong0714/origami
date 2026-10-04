# Data dependency matrix

Maps the wet-lab plan (Phases 2 to 4) onto the math chassis. "Intake" means a slot exists in `origami/lab/schema.py` or the plate-reader importer. "Math" means code that consumes the number. Status words describe software only; nothing here is validated and `calibrated` is false everywhere.

Scope decisions (user, 2026-10-02):
- The only payload is CaM-M13. SpyTag/SpyCatcher and LgBiT/SmBiT are core modules, not payloads.
- Enzymes (OtsA/OtsB) are not tested in the lab. Their priors stay in `origami/priors.py` as literature entries and are out of scope for the design engine.
- Legacy learner still uses `origami.design_engine` GP on physics scores. **Multi-fidelity luminescence** (dry=0 / wet=1) is wired on `POST /api/ssdk/learn` via `multifidelity_luminescence` (`src/gp_model/multifidelity.py` + `origami/ssdk/multifidelity_luminescence.py`). Sklearn residual GP remains for other paths.
- No CD, thermal shift, SEC or cryo-EM. Stability therefore stays literature-only (Phillips 2012, Cortajarena 2011) for the whole project.
- **n = 17** is not a calibrated design point but any repeat count the user enters (3–24) is computable, including n = 17.

## Needs no lab data (code or literature only)

| Item | State |
|---|---|
| Structure: rise, twist, radius vs PDB | Done, tested against 2AVP, 2HYZ, 2FO7 |
| Stability length models, Gibbs-Helmholtz with Phillips Table I Tm, dG, dHcal | Done; dCp source unresolved, implied-dCp back-calculation added and labelled derived |
| Docking clash, default payload = CaM-M13 (PDB 2BBM) | Done; side-chain exclusion is a caller-set parameter (no sourced value yet) |
| LgBiT size (7SNY 22.5 A alone, 7SNX 20.4 A in complex) | Derived and stored; not used as a clash radius because it is a core module |
| Kinetics: Spy lumped rate (Zakeri 2012), CaM-M13 peptide Kd 0.19 nM | In priors |
| Sensitivity (elasticities), ablation, cost-aware ranking, replicate choice | Done |
| Multi-fidelity luminescence (dry physics + wet y) | Done on `/api/ssdk/learn`; luminescence only; thresholds/CVs from `data/config/active_learning_config.json` (unmeasured) |
| Non-Euclidean kernels (ESM-2 / sequence) | Optional block on the shared SSDK feature matrix (sklearn, per-assay GP, and luminescence multi-fidelity). ESM-2 falls back to one-hot without torch |

## Needs lab data

| Plan item | Intake | Math that consumes it |
|---|---|---|
| T1.1-1.5 BCA, expression, solubility, purity, MW | prep slots (concentration, soluble fraction, mass check) | prep flags only; no model |
| T2/3 native PAGE shift, geometry series expression | `n_repeats`, prep flags | gates which designs enter the learner |
| T4.8 Ca dose-response | `calcium`, `calcium_rlu`, `wt_rlu` | residual GP, EC50 estimate, ablation |
| T4.9 NanoLuc standard curve | `assay_window` slots | `quantify_luminescence` on `POST /api/ssdk/learn` converts luminescence RLU to amount when the caller opts in. Default `y` is unchanged |
| T4.10 Scrambled M13 | `scrambled_rlu` | specificity ratio |
| T4.11 Inter-day CV | `quality.inter_day_rlu`, `quality.inter_operator_rlu` | `origami/lab/uncertainty_budget.py` → suggested GP σ |
| P3 Exp 1 instrument | `quality.plate_reader_reference_rlu` | recorded; no auto-calibration |
| P3 Exp 3 normalization | `quality.normalization_a_rlu`, `normalization_b_rlu` | ratio only |
| P3 Exp 4 Fluo-3 | `quality.fluo3_free_ca_M` | compare to calcium titration |
| P3 Exp 5 background | `quality.background_rlu`, `expressed_rlu` | signal/background |
| P3 Exp 6 linearity | `quality.linearity_amount`, `linearity_rlu` | same line fit as assay window |
| P3 Exp 8 freeze-thaw | `quality.freeze_thaw_rlu` | CV budget |
| P3 Exp 9 lysis | `quality.lysis_soluble_fraction` | fraction only |
| P3 Exp 10 negative panel | `quality.negative_control_rlu` | max RLU over list |
| P3 Exp 11 irreversibility | `quality.competitor_fold`, `complex_fraction_after_h` | reversal flag |
| P3 Exp 7 temperature | `rlu_25_C`, `rlu_30_C`, `rlu_37_C` | temperature sensitivity only |
| P3 Exp 12 locking kinetics | `time_min`, `fraction_locked` | k_lock fit (lumped Spy rate) |
| P4 4-tube bridging | `tube1_rlu` to `tube4_rlu` | bridging verdict |
| Plate versus frozen scaffold | `origami compare-plate`, optional `calcium_uM` | checksum, then within-interval against the frozen luminescence key. No calcium, or a quantity the plate does not measure, stays unscored |

## Open items that block a number
- Fusion CaM-M13 apparent Ca2+ Kd **80 nM**: secondhand (Nagai 2014 citing Porumb 1994) in `FUSION_CAM_M13_CA_KD_M`. Not the free-peptide Kd.
- Recruitment k_on **1e6 M-1 s-1**: explicit assumption with runtime warning; not a measurement.
- Errey 2010 OtsA assay details: SI not retrieved. Out of lab scope.

## Dry-lab inputs the math chassis is waiting on (from the team)
1. Scaffold freeze examples for CTPR-3, -8, and -14 are checked in, and a plate can be scored against them when `calcium_uM` is present. The luminescence ±30% band is still a placeholder: the eight ODE parameters have no sourced sigma, so parameter error is not propagated. Written pass/fail rules for a real plate are still open.
2. Group labels for the ablation (batch or construct names) and the planned replicate count per design.
3. Assay noise or CV from the plate-reader specification, and a cost per experiment (hours or wells), for the replicate-versus-new and cost-aware ranking.
4. Measured luminescence thresholds and assay CVs to replace placeholders in `active_learning_config.json`.
5. A sourced side-chain exclusion radius, or approval to use a named van der Waals convention.

## Resolved by literature
- Phillips 2012 dCp: taken from Cortajarena and Regan 2011, DOI 10.1002/pro.564, Table I (dCp 0.7, 0.9, 0.9, 1.9, 2.7, 2.8 kcal mol-1 K-1 for CTPRa2, 3, 4, 6, 8, 10), measured in 150 mM NaCl, pH 6.8. Verified against the Phillips text: "dCp ... obtained from Regan and co-workers (ref. 20)". With these inputs the calculator gives dG(10 C) 0.5 to 5.0 kcal mol-1 above the printed values, so Phillips' exact inputs are not reproducible from the tables.
