# ORIGAMI / CLASP — handoff context for new agents and chats

**Team:** Hong Kong team by Wong Shun Hei, Cheuk Mivon, and Fong Ming, ISEF 2026  
**Repository:** https://github.com/cedricwong0714/origami  
**Working branch (math chassis):** `cursor/ssdk-baseline-plan-5511`  
**Preferred PR base:** `cursor/origami-math-engine-9d85`  
**Draft PR (Origin):** https://cursor.com/codebase/origami-pchk/origami/pull/1  
**Public branch:** GitHub `main` at https://github.com/cedricwong0714/origami  
**Software freeze target (team):** 21 October — lab continues after; do not predeclare which assays will be missed.

Read **`AGENTS.md`** before changing biology, sequences, priors, or safety checks. **`calibrated: false`** everywhere until the team approves a dataset for a claim. A green pytest run is not wet-lab validation.

---

## What we are building

**ORIGAMI** is the mechanism-aware **math chassis** for **CLASP**: a calcium-triggered CTPR scaffold that recruits a **CaM–M13** payload (only payload in the wet plan). SpyTag/SpyCatcher and LgBiT/SmBiT are **core modules**, not payloads. **OtsA/OtsB** are literature-only and out of the design engine and wet scope.

The running stack has two layers:

1. **Deterministic chassis** (structure, stability lookup, docking, kinetics) — does not change when surrogate luminescence is posted.
2. **SSDK active learning** (Gaussian processes on wet/dry readouts) — recommends the next repeat count `n` and optional batch; does not edit the screw or Phillips curves.

**UI:** Next.js studio at `web/structural`. `npm run dev` defaults to port 3000 and proxies `/api` only while the dev server is running. API: `python host_sa.py` on port **41287**. Files in `web/` are static HTML. GitHub does not run the Python chassis.

---

## Locked product decisions (do not revert without user)

| Topic | Decision |
|--------|-----------|
| Payload | CaM–M13 only |
| Core modules | SpyTag/SpyCatcher, LgBiT/SmBiT — not clash payloads |
| Enzymes | OtsA/OtsB literature-only, not in wet plan |
| Repeat counts | Any **n = 3–24** computable; **planned series n = 3, 8, 14**; **n = 17** not a calibrated design point |
| Side-chain exclusion | Optional `ca_exclusion_A`, default **0** — no sourced vdw convention yet |
| Stability | Phillips 2012 CTPRa DSC length models + separate Gibbs–Helmholtz calculator; **ΔG gap 0.5–5.0 kcal/mol at 10 °C pinned, unexplained** |
| Enthalpy | Calculator uses Cortajarena & Regan 2011 Table I ΔCp where applicable |
| Default learner | **sklearn** Matérn-2.5 residual on wet luminescence; `design_engine` flag for older GP |
| Multi-fidelity luminescence | Dry = physics score (fidelity 0), wet = caller `y` (fidelity 1); dry noise **0.1** fixed |
| Pass rule | μ − 1.96σ ≥ threshold; thresholds/CVs in `data/config/active_learning_config.json` are **`unmeasured`** until replaced |
| Costs | Prior table in arbitrary units (dry_docking 0.01 … wet_full_panel 10) unless team replaces |
| Fusion CaM–M13 Kd 80 nM | Secondhand (Nagai 2014 → Porumb 1994), not free-peptide Kd |
| Spy k_on | Zakeri 2012 lumped **1.4×10³ M⁻¹ s⁻¹**; no numeric k_rev (“no reversal observed”) |
| Recruitment k_on | **1×10⁶ M⁻¹ s⁻¹** assumption — warns every call |
| Luminescence ODE vs n | **`predict_luminescence` does not take n_repeats** — calcium curve identical across scaffold freezes |
| Freeze luminescence band | **×0.7 / ×1.3** placeholder; **parameter_error_propagated: false** (eight ODE params have no sourced σ) |
| Two GP families | sklearn additive Matérn + white noise **≠** design_engine Cholesky Matérn-5/2 — not interchangeable |
| Feature matrix | **One** `geometry_feature_matrix` per learn request; shared `feature_matrix_sha256` on sklearn, multioutput, MF luminescence |
| ESM-2 | Optional; falls back to one-hot; not a CI dependency |
| application_group | Metadata only — **not** in kernel |

---

## Two streams (lab workflow)

**Stream 1 — chassis with empty slots**  
Run structure, stability, docking, kinetics, and SSDK learn while plates are still coming. Missing assays stay **NOT_GATED** / omitted. Do **not** invent wet values. Do **not** pre-fill which experiments will miss the 21 Oct software freeze.

**Stream 2 — literature / dry-lab pathway**  
When an assay will **never** be run wet, mark it literature-only and use papers or team dry calculations. Do **not** predeclare missed experiments at freeze time — flip to stream 2 only when that assay is actually dropped.

**Do not** silently substitute stream-2 numbers for stream-1 slots before the team decides an assay is dropped.

---

## SSDK: four slices + learn layer

### One-shot chassis (`POST /api/ssdk/chassis`, `origami ssdk chassis`)

| Slice | What it models (with real inputs) | Does not |
|--------|-----------------------------------|----------|
| **Structure** | Deposited CTPR screw (2AVP, 2HYZ, 2FO7): contour, axial span, rigid vs 15 nm WLC cutoff, chord between indices | Use payload FASTA |
| **Stability** | Phillips length-curve Tm(n), ΔG(n); optional lab Tm vs assay T; optional Gibbs–Helmholtz if ΔH, ΔCp posted | Refit from luminescence |
| **Docking** | Chord always; clash + C_eff + physics score when **both radii** supplied; optional `ca_exclusion_A` | Treat 25 Å placeholder as measured radius on learn path |
| **Kinetics** | `recruitment_steady`, `covalent_timecourse`, `nanobit_complementation` when mode + concentrations posted | Run without `kinetics.mode` |

### Active learning (`POST /api/ssdk/learn`, `origami ssdk learn`, `origami ssdk learn-plate`)

- **Observations:** `n_repeats`, `y`, optional `sigma`, `fidelity` 0|1, `output` (luminescence | locking_fraction | expression | solubility | purity).
- **Five outputs:** separate two-fidelity GPs; missing outputs omitted.
- **Four “next n” labels (not averaged):** `recommendation.next_n` (primary sklearn when fitted), `design_engine_next_n`, `multifidelity_luminescence_n`, `batch_n`.
- **`chassis_at_next_n`:** same as chassis at primary `next_n`; **`slices` unchanged**.
- **`literature_training`:** residual GPs on Phillips table only — not a wet-lab instruction.
- Optional: `sequence` + `construct` (`linker_residues`, `cam_on_scaffold`, `m13_on_scaffold`), `quantify_luminescence` + standard curve.

### Lab intake

- Plate CSV: `well`, `construct`, `n_repeats`, `batch`, `role`, `rlu`; optional `calcium_uM`, `output`, `fidelity`.
- **`origami compare-plate`** / **`POST /api/lab/plate-vs-frozen`** vs `data/predictions/frozen/scaffold-n{3,8,14}.json` when calcium matches frozen keys.

---

## What is done (engineering, ~90% — not calibration)

- Structure, stability length fit, docking, kinetics priors and simulators  
- SSDK chassis + learn + unified feature matrix + batch EI/cost + heteroscedastic scatter (opt-in)  
- Multi-fidelity luminescence (`mf-lum-v0.2`), five-assay multioutput GPs  
- Plate reader, plate→learn pipeline, ablation hooks, uncertainty budget from replicates  
- Frozen scaffolds n=3,8,14; luminescence interval labeling; CLI `origami ssdk …`  
- Wiki: `/ssdk`, `/learn`, `/intake`, `/guide`; judge/docs/API/model cards updated  
- Tests: SSDK learn, plate, multifidelity, freeze/compare (24+ in recent runs)

**Still open without user/literature data (~10%):** side-chain radius, recruitment kon decision, ODE parameter σ, Phillips ΔG reconciliation, measured thresholds/CVs/groups, written real-plate pass rules.

---

## What the user will provide

### Dry-lab (team calculations / design metadata — not wet plates)

1. **`construct` block per architecture** (for learn JSON / `learn-plate --json-body`):  
   - `linker_residues` (default **15** = (GGGGS)₃)  
   - `cam_on_scaffold`, `m13_on_scaffold`  
2. **Optional `sequence`** — one amino-acid string **per learn job** (same protein, varying `n` only); encoding composition | onehot | esm2. Plate **`construct` column is a label only**, not FASTA.  
3. **Ablation:** group labels (batch/construct names), planned replicate count per design.  
4. **Optional:** real cost table (hours/wells) to replace arbitrary costs.  
5. **Optional:** sourced **`ca_exclusion_A`** (Å) + method, or approval of a named vdw convention.  
6. **Optional:** external dry score rows (`fidelity: 0`) if not using in-repo physics score.

**Literature list is separate** (next message from user): Kd, rates, radii, ΔCp, etc. — do not invent; cite in code comments per AGENTS.md.

### Wet-lab (plates and JSON intake)

- Measured **thresholds** and **assay CVs** → update `data/config/active_learning_config.json` with `status: measured`.  
- Plates: blank-corrected RLU, optional calcium, optional per-assay `output`/`fidelity`.  
- Phase 3 **quality** slots, lock kinetics, bridging tubes — see `origami/lab/schema.py` and `docs/DATA_DEPENDENCY_MATRIX.md`.  
- Standard curve when using **`quantify_luminescence`**.

### Not required by software for most phases

- Full FASTA for every phase in a single upload — only **SSDK learn** opts into `sequence`.  
- Predeclaring which assays miss the freeze.

---

## Key paths and commands

| Item | Location / command |
|------|---------------------|
| Config placeholders | `data/config/active_learning_config.json` |
| Scaffold freezes | `data/predictions/frozen/scaffold-n{3,8,14}.json` |
| SSDK learn | `origami/ssdk/learn.py`, `origami/ssdk/chassis.py` |
| Plate | `origami/lab/plate_reader.py`, `origami/ssdk/plate_pipeline.py` |
| Docs | `docs/USER_MANUAL.md`, `docs/API.md`, `docs/JUDGE.md`, `docs/DATA_DEPENDENCY_MATRIX.md`, `docs/MODEL_CARDS.md` |
| Tests | `.venv/bin/python -m pytest` (see `tests/math_chassis/test_ssdk_learn.py`, plate, multifidelity, freeze) |
| API | `.venv/bin/python host_sa.py` |
| Web | `cd web/structural && npm run dev -- --port 3000` |

```bash
origami ssdk chassis --json-body '{"n_repeats":8}'
origami ssdk learn-plate PLATE.csv --json-body '{"n_min":8,"n_max":14}'
origami compare-plate PLATE.csv
origami freeze --scaffold --n-repeats 8 --prediction-id scaffold-n8
```

---

## Git

The public repository is https://github.com/cedricwong0714/origami, branch `main`. Clone that URL. Do not put a token in the remote URL. A push that returns 403 needs repository write access on the GitHub token.

---

## Explicitly out of scope (unless user asks)

- BoTorch q-EI, joint five-output ICM, installed ESM weights as default  
- CD, thermal shift, SEC, cryo-EM wet assays  
- Inventing biological constants, sequences, citations, or ODE σ  
- Reconciling Phillips ΔG gap without sourced missing inputs  
- Claiming that GitHub or a static HTML file runs the Python chassis

---

## How to read a learn response (judge-facing)

- **`calibrated: false`** always until team approves data.  
- **PASS** on synthetic y is against **unmeasured** thresholds — demo only.  
- **Primary next n** ≠ design-engine n ≠ MF luminescence n ≠ batch list — normal.  
- **Chassis at primary n** shows screw + Phillips + clash/kinetics flags; luminescence GP does not change Tm(n).

---

*Update this file when scope, branch tip, or stream policy changes.*
