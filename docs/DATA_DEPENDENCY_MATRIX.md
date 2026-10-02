# Data dependency matrix

Maps the wet-lab plan (Phases 2 to 4) onto the math chassis. "Intake" means a slot exists in `origami/lab/schema.py` or the plate-reader importer. "Math" means code that consumes the number. Status words describe software only; nothing here is validated and `calibrated` is false everywhere.

Scope decisions (user, 2026-10-02):
- The only payload is CaM-M13. SpyTag/SpyCatcher and LgBiT/SmBiT are core modules, not payloads.
- Enzymes (OtsA/OtsB) are not tested in the lab. Their priors stay in `origami/priors.py` as literature entries and are out of scope for the design engine.
- Canonical GP is the sklearn one (`src/gp_model/residual_gp.py`).
- No CD, thermal shift, SEC or cryo-EM. Stability therefore stays literature-only (Phillips 2012, Cortajarena 2011) for the whole project.
- The Phase 2 list names CTPR-8, -14 and -17. The earlier instruction was not to use n = 17. The code uses 3, 8, 14 until this is settled.

## Needs no lab data (code or literature only)

| Item | State |
|---|---|
| Structure: rise, twist, radius vs PDB | Done, tested against 2AVP, 2HYZ, 2FO7 |
| Stability length models, Gibbs-Helmholtz with Phillips Table I Tm, dG, dHcal | Done; dCp source unresolved, implied-dCp back-calculation added and labelled derived |
| Docking clash, default payload = CaM-M13 (PDB 2BBM) | Done; side-chain exclusion is a caller-set parameter (no sourced value yet) |
| LgBiT size (7SNY 22.5 A alone, 7SNX 20.4 A in complex) | Derived and stored; not used as a clash radius because it is a core module |
| Kinetics: Spy lumped rate (Zakeri 2012), CaM-M13 peptide Kd 0.19 nM | In priors |
| Sensitivity (elasticities), ablation, cost-aware ranking, replicate choice | Done |
| Multi-fidelity model (dry lab vs wet lab) | Not built; needs a design decision on fidelity levels (see below) |
| Non-Euclidean kernels (sequence or graph) | Not built; needs a decision on the feature representation |

## Needs lab data

| Plan item | Intake | Math that consumes it |
|---|---|---|
| T1.1-1.5 BCA, expression, solubility, purity, MW | prep slots (concentration, soluble fraction, mass check) | prep flags only; no model |
| T2/3 native PAGE shift, geometry series expression | `n_repeats`, prep flags | gates which designs enter the learner |
| T4.8 Ca dose-response | `calcium`, `calcium_rlu`, `wt_rlu` | residual GP, EC50 estimate, ablation |
| T4.9 NanoLuc standard curve | `assay_window` slots | absolute quantification, not yet connected to the GP target |
| T4.10 Scrambled M13 | `scrambled_rlu` | specificity ratio |
| T4.11 Inter-day CV | not a slot | needs an uncertainty-budget module (error propagation) |
| P3 Exp 7 temperature | `rlu_25_C`, `rlu_30_C`, `rlu_37_C` | temperature sensitivity only |
| P3 Exp 12 locking kinetics | `time_min`, `fraction_locked` | k_lock fit (lumped Spy rate) |
| P4 4-tube bridging | `tube1_rlu` to `tube4_rlu` | bridging verdict |
| P3 Exp 1, 2, 3, 4, 5, 6, 8, 9, 10, 11 | no slots yet | add after the protocols are fixed (instrument calibration, furimazine decay, normalization comparison, Fluo-3 free Ca, background vs expression, linearity, freeze-thaw, lysis, negative panel, irreversibility) |

## Open items that block a number
- Fusion CaM-M13 Kd: no value found. An attempted source (a Ca-indicator review) contained no such measurement; a CaM-M13 hybrid paper reports Ca binding constants, not a tethered Kd. Slot stays vacant.
- Recruitment k_on: the existing 1e6 M-1 s-1 in `CLASPParameters` has no citation. Sensitivity analysis shows how much it matters.
- Errey 2010 OtsA assay details: SI not retrieved. Out of lab scope.
