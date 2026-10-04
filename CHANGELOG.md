# Changelog

## Unreleased — 2026-10-04 (studio copy)

### Changed
- Studio page text is written as short intros, steps, and plain-language reads of the numbers.

## Unreleased — 2026-10-04 (Vercel + Render deploy)

### Added
- `web/structural/DEPLOY.md` documents deploying the studio on Vercel with the FastAPI calculator on Render.
- On Vercel builds, Next.js skips static export and rewrites `/api/*` to `STRUCTURAL_API_URL`.
- `render.yaml` includes an `origami-structural-api` Python service for the calculator API.

## Unreleased — 2026-10-04 (studio dark mode)

### Added
- Dark mode for the Next.js studio. The page background uses grey `#242220`. Cards, borders, charts, and the 2D helix canvas follow the same theme tokens. A Light/Dark toggle in the navigation bar saves the choice in `localStorage`.

## Unreleased — 2026-10-04 (length sweep)

### Added
- `POST /api/docking/sweep` scores every repeat count from 3 to 24 with the existing Phillips length-model melt and the existing affinity check. The studio page Choose a length draws melting temperature, bound fraction, LgBiT–SmBiT occupancy, SpyCatcher–SpyTag half-life, and clash on that sweep.
- The marked length is the highest LgBiT–SmBiT occupancy among lengths above the assay temperature whose association holds. A tie takes the shorter scaffold. The mark is that ranking rule. `calibrated` stays false.

## Unreleased — 2026-10-04 (studio copy and model charts)

### Added
- `GET /api/stability/curve` returns the Phillips length model from n = 3 to n = 24 for the melt chart.
- The studio draws that melt curve, a docking concentration comparison, and kinetic isotherm or time-course plots.

### Changed
- Studio page text states the design question each model answers.

## Unreleased — 2026-10-04 (SSDK studio runs any repeat count)

### Added
- `GET /api/stability/predict` evaluates the Phillips 2012 CTPRa DSC length model at any repeat count from 3 to 24, including n = 14 when the paper has no table cell.
- `POST /api/docking/affinity` compares a typed Kd or Ka with the screw’s local concentration. Held means bound fraction at least 1/2 (Langmuir midpoint, not a paper cutoff). LgBiT–SmBiT and SpyCatcher–SpyTag are scored at that concentration only when the association holds.
- Studio navigation is the four SSDK slices: structural analysis, stability confirmation, docking verification, kinetic modelling. The compare chart accepts repeat counts other than 3, 8, and 14.

### Changed
- Lab intake, plate upload, the guide page, and the single-length page are not in the studio navigation.

## Unreleased — 2026-10-04 (literature metadata fetch)

### Added
- `origami fetch-literature` and `/api/literature/doi` + `/api/literature/search` pull Crossref bibliographic records and Europe PMC abstracts when present. Publisher PDFs are not downloaded. Search hits are not installed as priors.

## Unreleased — 2026-10-04 (CamSol citation, secondhand Kd, graft index)

### Changed
- CamSol scores cite Sormanni & Vendruscolo 2019 (DOI 10.1101/cshperspect.a033845). Scores stay dry.
- Fusion 80 nM Ca2+ Kd stays secondhand. A team reading of Porumb 1994 pCa50% = 6.3 (500 nM) is stored separately and is not the Langmuir Kd.
- A 2e9 M^-1 s^-1 CaM–M13 kon was stated without a DOI and is not installed. Recruitment kon remains the warned 1e6 assumption.
- Clash still uses the 2BBM Cα sphere; ca_exclusion stays 0; Spy k_rev stays vacant; Phillips ΔG gap stays unexplained; ODE sigmas stay vacant.
- M13 graft index for n = 8 is the 4th repeat (matches the pasted sequence). SpyCatcher is N-term and LgBiT is C-term on the SSDK feature distances. Default construct flags are CaM off scaffold, M13 grafted.

## Unreleased — 2026-10-04 (software interchange)

### Added
- Team-supplied CaM–M13 sequences for n = 3, 8, 14 in `data/constructs/team_cam_m13_series.json` with SHA-256 checksums and CamSol intrinsic scores (dry, pH stated as 7.4–7.6).
- Protein GenBank and SBOL 3 XML export of those strings. Amino acids only; no codon table.
- SBML Level 2 for the three shipped kinetics modes (recruitment Langmuir, lumped Spy adduct, NanoBiT). Rates come from existing slots or the caller.
- Chassis JSON passport, batch CSV chassis table, labelled synthetic learner fixtures, PDB C-alpha size scales that do not replace the CTPR screw.
- `origami export-genbank`, `export-sbol`, `export-sbml`, `passport`, `benchmark`, `synthetic`, `batch-chassis`. Matching `/api/export/*` routes.
- Guided wizard page `/wizard`. Architecture diagram in `docs/ARCHITECTURE.md`. Notebook `notebooks/origami_chassis_demo.ipynb`.
- Mechanism “profile” intake only accepts the three existing kinetics modes. A free-form ODE is rejected.

### Not in this slice
- SynBioHub upload, UI translation, offline packaging, COPASI as a runtime dependency.

## Unreleased — 2026-10-04 (chassis score at the primary next length)

### Added
- `chassis_at_next_n` on the learn response. It is `evaluate_chassis` at `recommendation.next_n`. Caller radii are forwarded. The default placeholder radius is not treated as a measured radius, so clash stays uncomputed. Kinetics runs only when the posted block includes `mode`. `slices` are unchanged. `calibrated` stays false.
- The SSDK learn panel and the learn page list the primary next length beside the design-engine length, the luminescence multi-fidelity length, and the batch, plus contour, clash, and kinetics from that chassis snapshot.

## Unreleased — 2026-10-04 (one SSDK command for chassis, learn, and plate)

### Added
- `origami ssdk chassis`, `origami ssdk learn`, and `origami ssdk learn-plate`. The plate command takes observations from the CSV and every other learn field from `--json-body`.
- Optional plate columns `output` and `fidelity`. Replicates are averaged only when those match. A locking row stays a locking observation.
- `recommendation` on the learn response names the primary next length and lists the design-engine length, the luminescence multi-fidelity length, and the batch. Those lengths are not averaged.

## Unreleased — 2026-10-04 (one feature matrix for the SSDK Gaussian processes)

### Changed
- Sklearn residual, the five per-assay multi-fidelity GPs, and the luminescence multi-fidelity GP now train and predict on one matrix (`geometry_feature_matrix`). Linker RMS and CaM/M13 placement are no longer dropped on the luminescence multi-fidelity path. The response records `feature_matrix_sha256` on all three blocks.
- A non-luminescence observation is not a wet point for the luminescence multi-fidelity GP. It stays on its own assay GP.
- Optional sequence features are appended to that same matrix, including the multi-fidelity luminescence fit. Model version for that block is `mf-lum-v0.2`.

## Unreleased — 2026-10-03 (plate versus freeze, blocked ODE error, standard-curve target)

### Added
- `origami compare-plate` and `POST /api/lab/plate-vs-frozen` score a blank-corrected plate against `scaffold-n3.json`, `scaffold-n8.json`, and `scaffold-n14.json`. A row is compared only when `calcium_uM` matches a frozen luminescence key. Contour and the Phillips curve are reported as untested. A checksum mismatch refuses the file.
- The intake page can run that comparison. The ±30% band is still the interval, and the response says ODE parameter error was not propagated.
- `quantify_luminescence` on `POST /api/ssdk/learn` converts luminescence from RLU to amount with a caller-supplied standard curve. Other outputs stay on the caller scale. The default remains the raw `y`.

### Changed
- New luminescence freezes record `parameter_error_propagated: false` and the eight ODE parameters that have no sourced sigma. Peptide Kd and the Spy bimolecular sigma are not applied to those parameters. The checked-in scaffold files were not rewritten.

## Unreleased — 2026-10-03 (scaffold freeze examples for n = 3, 8, 14)

### Added
- `origami freeze --scaffold --n-repeats N` writes contour, axial span, and the Phillips length curve at that repeat count, plus the calcium luminescence curve.
- Checked-in examples: `data/predictions/frozen/scaffold-n3.json`, `scaffold-n8.json`, `scaffold-n14.json`.
- Contour and axial-span intervals are the deposited rise sample standard deviation scaled by the repeat factor and 1.96. They are not a wet-lab confidence interval.
- Luminescence in those files does not depend on n. Its interval remains predicted value times 0.7 and 1.3 (`fixed_relative_placeholder_pm_30_percent`, `hypothesis_only`). The Phillips ΔG in the file is the length-curve fit, not the Gibbs–Helmholtz calculator, and the two are not reconciled here.

## Unreleased — 2026-10-03 (learn-ssdk command and five-assay table)

### Added
- `origami learn-ssdk --json-body '...'` prints learner family, both next-n values, overall status, and the batch. `--full` prints the JSON.
- SSDK learn panel lists μ, σ, and pass for each fitted assay at the reported next n.
- A purity miss multiplies that length's batch weight by 0.25. An unfitted assay does not.

## Unreleased — 2026-10-03 (optional sequence features and residual scatter)

### Added
- `sequence` on `POST /api/ssdk/learn`. Default encoding is amino-acid composition. `sequence_encoding=esm2` uses ESM-2 only when `pip install -e ".[esm]"` has provided torch and transformers; otherwise the recorded method is the one-hot fallback. ESM-2 is not a default dependency.
- `origami/ssdk/hetero_noise.py`: a second GP on log squared residual. It is reported beside the residual standard deviation, does not replace assay CVs, and is not written to the config. Set `use_heteroscedastic_std` true to use it in the acquisition score.

## Unreleased — 2026-10-03 (canonical sklearn learner and five-output batch)

### Added
- Default `learner` on `POST /api/ssdk/learn` is `sklearn` (Matérn-2.5 residual). `design_engine` remains available. The response names `learner_family`, including `design_engine_fallback` when there is no wet luminescence row.
- Separate two-fidelity GPs for luminescence, locking fraction, expression, solubility, and purity. An output with no row is omitted.
- Feature row adds screw radius, three default module distances, linker RMS from the existing Kratky–Porod function, and CaM/M13 placement flags.
- Greedy batch of 1–12 lengths. Solubility or purity below the placeholder lower-95% gate multiplies EI/cost by 0.25.
- SSDK learn panel shows the family, the design-engine n beside it, and the batch.

## Unreleased — 2026-10-03 (judge page, model cards, API cheat sheet)

### Added
- `docs/JUDGE.md`, `docs/MODEL_CARDS.md`, `docs/API.md`.
- User manual and `/guide` now state the same rule: geometry and literature tables stay under the Gaussian process, and a luminescence pass uses an unmeasured threshold.

## Unreleased — 2026-10-02 (finish: quality slots, guide UI, meta API)

### Added
- Phase 3 **quality** schema slots and `run_quality` / `uncertainty_budget` (inter-day CV → suggested GP noise).
- `GET /api/meta/dependencies`, `GET /api/meta/active-learning-config`.
- Next.js **`/guide`** (Dependencies) page; Learn page shows multi-fidelity gates; lab residual GP returns `multifidelity_luminescence`.

## Unreleased — 2026-10-02 (multi-fidelity learn wired + SSDK gates UI)

### Added
- `POST /api/ssdk/learn` returns `multifidelity_luminescence`: two-fidelity GP on luminescence (dry physics + wet `y`), pass/fail on lower 95% bound, cost-weighted EI for `wet_NanoBiT`.
- `origami/ssdk/features.py`, `origami/ssdk/multifidelity_luminescence.py`; observations accept optional `fidelity` 0 or 1.
- SSDK page: **Predictions & gates (luminescence)** panel with JSON observations and candidate table.
- `docs/DATA_DEPENDENCY_MATRIX.md` synced to current scope.

## Unreleased — 2026-10-02 (two-fidelity GP and adopted kinetics figures)

### Added
- `src/gp_model/multifidelity.py`: two-fidelity GP, dry=0 / wet=1, Matern-5/2 with per-feature length scales, 2x2 coregionalization. Dry noise fixed at 0.1 (prior choice, no replicates). Bounds are prior choices.
- `src/gp_model/sequence_encoding.py`: ESM-2 preferred; falls back to one-hot when torch/transformers are absent, and records which method ran.
- `src/experiment_design/frozen_table.py`: pass iff mu - 1.96 sigma >= threshold; cost-weighted EI; frozen table that refuses overwrite.
- `data/config/active_learning_config.json`: thresholds, CVs and costs, all tagged unmeasured or prior choice.
- Priors: fusion CaM–M13 apparent Ca2+ Kd 80 nM (Nagai 2014 citing Porumb 1994; secondhand, sigma unknown). Spy reversal recorded as unobserved, with no numeric k_rev. Recruitment kon 1e6 M^-1 s^-1 is an explicit assumption that warns on every call; derived koff = 0.08 s^-1.

### Unchanged
- Free-peptide CaM–M13 Kd stays 0.19 nM. Spy lumped rate stays 1.4e3 M^-1 s^-1. Repeat count stays any integer the user enters (n=17 is computable, not a calibrated point).

## Unreleased — 2026-10-02 (SSDK literature priors, scaffold registers, and stacked ensemble uncertainty)

### Changed / added 2026-10-02 (user decisions)
- Default payload radius: 25.0 A (MW-scaling placeholder, sigma 8.0) changed to 22.513 A (sigma 4.763), PDB 2BBM CaM-M13 complex, sqrt(5/3) x C-alpha Rg; sigma is the SD of the three CaM states 1PRW/2BBM/1CLL. Reason: CaM-M13 is the only payload in the lab plan. Old source: order-of-magnitude MW heuristic. New source: `scripts/derive_payload_radii.py`. Impact: every default-radius clash and effective-concentration result. Reviewed by: user instruction; not independently reviewed.
- `data/stability/ctpr_thermal_literature.json`: added `delta_Hcal` (kcal mol-1) with uncertainty on the nine Phillips 2012 DSC rows, from Table I (retrieved text). `thermo_prefill` now returns them. No dCp in the table, so the calculator still cannot draw the ΔG(T) curve from prefill alone. With dCp = 0 the printed dHcal gives ΔG(10 C) of 10.3 (n=3) and 32.8 (n=8) kcal mol-1 against printed 4.8 and 14.3, so dCp matters. `origami/stability/implied_cp.py` back-calculates the self-consistent dCp (derived, not literature).
- `steric_report` and `scaffold_overlap_probability` accept `ca_exclusion_A` (default 0.0, unchanged behaviour) for side-chain exclusion. No sourced value was found, so none is defaulted. Correction: an earlier note said the scaffold was not modelled; it is, as a placed C-alpha cloud.
- LgBiT added to `payload_radii.json` (7SNY 22.5 A, 7SNX chain A 20.4 A). Titles and resolutions verified through the RCSB core API.
- Not adopted: a pasted "fusion CaM-M13 Kd about 80 nM" (cited source is a Ca-indicator review with no such number) and "k_on = 1e6 central estimate" (a modelling assumption, not a measurement).
- `docs/DATA_DEPENDENCY_MATRIX.md` added.
- Phillips dCp source resolved to Cortajarena and Regan 2011 (DOI 10.1002/pro.564, Table I). Added `delta_Cp` (kcal mol-1 K-1, no uncertainty printed) to the Phillips DSC rows for n = 2, 3, 4, 6, 8, 10; none for n = 5. Buffer differs from Phillips (150 mM NaCl, pH 6.8 vs 50 mM phosphate, pH 7). Calculator dG(10 C) is 0.5 to 5.0 kcal mol-1 above the printed dG; pinned by a test.
- API: `POST /api/lab/plate`, `POST /api/lab/ablation`. UI: `/intake` page (plate import table, ablation table). Browser-tested; typecheck and lint clean.

### Added (software, no biological constants changed)
- `src/gp_model/ablation.py`: grouped leave-one-group-out ablation of physics, physics+GP, physics+GP+XGBoost (RMSE, MAE, 95% coverage, Spearman). CLI: `origami ablation`.
- `origami/lab/plate_reader.py`: long-format plate CSV import with per-batch blank subtraction and SEM; records input SHA-256. CLI: `origami import-plate`.
- `origami/ssdk/plate_pipeline.py`: plate CSV to SSDK learner. CLI: `origami learn-plate`.
- `src/predictions/sensitivity.py`: parameter elasticities, recorded in `origami freeze` output. These are not uncertainty; the +/-30% placeholder band is unchanged.
- `src/experiment_design/cost_aware.py` and `replicate_choice.py`: cost-aware, pending-aware ranking and replicate-versus-new choice, each with a generated reason.
- `origami/acquisition_core.py`: single Expected Improvement used by both acquisition stacks, bit-identical to the previous outputs (tests compare against the old formulas). `origami/gp_protocol.py`: common read interface over both ResidualGP classes; models not merged.
- Removed the unsourced `expressed_n17` lab prep flag.
- Known: `BayesianExperimentSelector.expected_information_gain` uses an unsourced noise = 0.1 and a fantasy loop that returns the same value each pass. Not changed.

### Added (retrieved from papers, 2026-10-02)
- `scripts/derive_payload_radii.py` downloads deposited C-alpha coordinates from RCSB and writes `data/structures/payload_radii.json`. Clash radius = sqrt(5/3) x C-alpha Rg (solid-sphere equivalent). Results: SpyCatcher 4MLI 16.7 A, NanoLuc 5IBO 20.4 A (PROXY for LgBiT; no LgBiT structure found), Ca-CaM compact 1PRW 18.9 A, extended 1CLL 28.3 A, CaM in 2BBM 22.5 A, E. coli OtsA 1GZ5 28.8 A. Side chains ignored; flexible termini inflate Rg; between-copy SD understates uncertainty.
- E. coli OtsB has no PDB entry (RCSB search on UniProt P31678 is empty). PDB 1U02 is Thermoplasma acidophilum and is not used. OtsB gets only an Erickson lower bound from UniProt mass 29175 Da, flagged not usable as a clash radius.
- `POST /api/ssdk/learn` accepts `payload_names` (two keys) as an alternative to `payload_radii_A`; `radius_origin` is `pdb_derived`.
- `erickson_rmin_A`: R_min = 0.066 M^(1/3) nm (Erickson 2009, Eq. 2.2, DOI 10.1007/s12575-009-9008-x, PMC3055910). A lower bound, not a payload radius.
- OtsA k_cat 34 +/- 1 s^-1, K_m(UDP-Glc) 1.7 +/- 0.3 mM, K_m(G6P) 7.3 +/- 0.6 mM; OtsB k_cat 286 +/- 34 s^-1, K_m(T6P) 3.6 +/- 0.8 mM. Source: Khan et al. (2024) Nat Commun, DOI 10.1038/s41467-024-48691-6, Table 1. The OtsA values are taken there from Errey et al. (2010) Angew Chem 49:1234-1237; the Khan 2024 reference list confirms footnote ref. 46 is Errey et al. (2010); Errey's own kcat/Km were not seen in retrieved text and the assay conditions were not retrieved. The OtsB footnote says NMR at 37 C and the Methods mention malachite green; this is unresolved. `calibrated` stays false.
- OtsA recombinant mass about 54.7 kDa (Acta Crystallogr D 58:349-351, 2002 abstract).
- The values removed earlier (k_cat 50 and 120, K_m 0.5, 2.4, 0.15) disagreed with these papers.

### Added
- Reverted: an earlier entry in this release added payload radii and OtsA/OtsB k_cat and K_m values with citations written from model memory and not checked against the papers. They were removed. Payload radii and enzyme constants stay vacant until a human retrieves them from the cited sources.
- Scaffold and lab changes:
  - Reconciled canonical scaffold registers in `origami/physical/registers.py`: `TEAM_ONE_TURN_N = 8`, `TEAM_GEOMETRY_SERIES = (8, 14)`, and `TEAM_CANONICAL_LENGTHS = (3, 8, 14)` with explicit experimental role mappings.
  - `fit_residual_gp: True` in `origami/lab/run.py` to optionally connect wet-lab bridging/luminescence observations directly to the SSDK physics score and discrete active learning recommendations.
  - Stacked ensemble predictive uncertainty propagation in `src/gp_model/stacked_ensemble.py`: Layer 3 (XGBoost) trains on the residual left after Layer 2 (GP) and combines GP variance with XGBoost cross-validation LOO RMSE (\( \sigma_{\text{total}} = \sqrt{\sigma_{\text{gp}}^2 + \text{loo\_rmse}^2} \)).
  - Comprehensive unit tests: `tests/unit_tests/test_payload_priors.py`, `tests/unit_tests/test_scaffold_registers.py`, and `tests/unit_tests/test_lab_gp_wiring.py`.

### Changed
- `origami/lab/schema.py`: scaffold length slot description updated to reflect full canonical series (CTPR-8 and 14 with CTPR-3 baseline).
- `origami/lab/run.py`: `_PREP_FLAGS` includes `expressed_n3`.

## Unreleased — 2026-10-02 (SSDK baseline)

### Added
- `docs/SSDK_ROADMAP.md` records engineering readiness for the four SSDK chassis and for the GP, Bayesian optimization, and XGBoost layers. The percentages are software readiness. They are not calibration.
- `tests/unit_tests/test_xgb_meta.py` fits the XGBoost residual layer on 15 synthetic rows when the package is installed.
- `tests/unit_tests/test_cli_freeze.py` checks `origami freeze` and `origami compare`.

### Changed
- `tests/golden_references/numeric_baseline.json` calcium occupancy now matches `recruitment_occupancy` at `CAM_M13_KD_CA_SAT_M` = 0.19 nM.
  Reason: commit c35a643 changed that constant from 1e-7 M to the Biochemistry 2006 peptide Kd (DOI 10.1021/bi060857u) and left the golden on the old curve. This update does not change the constant again. The intermediate-transfer product series is unchanged.
  Old source of the golden curve: unsourced 1e-7 M Kd previously hardcoded in `src/core/calcium_kinetics.py`.
  New source of the locked curve: Biochemistry 2006, 45(41):12547-12559, DOI 10.1021/bi060857u, already cited on the constant.
  Impact: `test_numeric_baseline_locked` occupancy only.
  Reviewed by: not a human wet-lab review. A passing golden test is not scientific validation.
- `origami freeze` keeps the same ±30% band and labels it `fixed_relative_placeholder_pm_30_percent`. The command no longer attributes `k_lock=0.003 s^-1` to Zakeri et al. 2012. `origami.priors` already records that this rate is not printed in that paper. The ODE value was not changed.
- The `dev` extra now installs FastAPI, HTTPX2, and XGBoost so `pip install -e ".[dev]"` can collect the API tests and run the 15-row tree fit. No biological parameter was added.

## Unreleased — 2026-10-01 (docking and kinetics engine)

### Added
- Docking with both caller radii now returns `local_kinetics`. Spy uses `k_obs = k_on * C_eff` with the Zakeri et al. 2012 apparent rate (DOI 10.1073/pnas.1115485109). The half-life is omitted when the 95% band on `k_obs` reaches zero. NanoBiT occupancy uses the printed Dixon et al. 2016 Kd of 190 μM (DOI 10.1021/acschembio.5b00753). The relaxation rate uses that paper's k_on and k_off. `k_rev` and `k_bond` stay null. A missing radius still omits clash, C_eff, and this block. The 25 Å placeholder is not used.
- `mode = nanobit_complementation` integrates d[complex]/dt = k_on [Lg][Sm] − k_off [complex]. Equilibrium uses k_off / k_on. The printed 190 μM Kd is not substituted. Both starting concentrations are required. `calibrated` stays false. `confidence_tier` is `hypothesis_only`.
  Reviewed by: not a human wet-lab review. A passing test is not scientific validation.

## Unreleased — 2026-10-01 (literature residual training)

### Added
- `literature_training` on `POST /api/ssdk/learn` fits two residual Gaussian processes to the Phillips et al. 2012 CTPRa DSC table already in `data/stability/ctpr_thermal_literature.json` (DOI 10.1002/pro.2018). One track is printed Tm. One track is printed unfolding ΔG at 10 °C. The physics score is the existing length model of that same table. The lab plan has no DSC and no thermal shift, so `lab_will_measure_this` is false and the UCB length is labeled as not a wet-lab instruction. Surrogate luminescence is not mixed into these rows. A missing printed sigma stays omitted. `calibrated` stays false. `confidence_tier` is `hypothesis_only`.
- The `/learn` page shows both tracks beside the surrogate form.
  Reviewed by: not a human wet-lab review. A passing test is not scientific validation. This fit is not a measurement of the Hong Kong team fusion.

## Unreleased — 2026-10-01 (SSDK chassis)

### Added
- `POST /api/ssdk/chassis` evaluates one repeat count across structure, stability, docking, and kinetics. The screw chord is always returned. Clash and Gaussian-chain C_eff run only when both payload radii are supplied; the 25 Å placeholder is not used. A typed lab Tm is compared with the assay temperature and does not refit the Phillips 2012 CTPRa DSC length model. Kinetics runs only from posted concentrations and rates. `calibrated` stays false.
- The wiki page is `/ssdk`.
  Reviewed by: not a human wet-lab review. A passing test is not scientific validation.

## Unreleased — 2026-10-01 (SSDK surrogate learning)

### Added
- `POST /api/ssdk/learn` scores the CTPR library and recommends the next surrogate length. Surrogate rows are caller readouts. With fewer than three distinct lengths, α stays 1 and the Matérn hyperparameters are not optimized; the posterior still shifts by the observed residual. With three or more, `gp_fitted` is true. Structure contour and the Phillips 2012 CTPRa DSC length model are reported beside the recommendation and are not overwritten. Omitted payload radii use the 25 Å placeholder and are named as a placeholder. A missing observation sigma is not stored as zero. `calibrated` stays false.
- The wiki page is `/learn`.
  Reviewed by: not a human wet-lab review. A passing test of this loop is not scientific validation.

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
