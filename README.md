# ORIGAMI

**Hong Kong team by Wong Shun Hei, Cheuk Mivon, and Fong Ming · ISEF 2026 Software**

Mechanism-aware design engine for **CLASP** (*Conditional Localized Assembly of Synthetic Proteins*).

ORIGAMI does not score every payload with one universal “proximity” heuristic. It uses a **shared physical engine** (scaffold geometry, linker reach, steric accessibility, Ca²⁺–CaM–M13 recruitment) connected to **separate functional models** for six mechanism profiles:

| Profile | Mechanism | Reference use |
|---------|-----------|---------------|
| `trehalose_synthesis` | Intermediate transfer | OtsA → OtsB osmoprotectant pathway |
| `target_complementation` | Target-induced complementation | Cell-free / screening-assay split reporter |
| `redox_transfer` | Redox electron transfer | Organized donor–acceptor pairs |
| `covalent_capture` | Covalent lock | SpyTag / SpyCatcher proximity capture |
| `trans_activation` | Trans-autophosphorylation | Proximity-induced kinase signaling (Tier-3 computational baseline) |
| `protease_cleavage` | Protease–substrate cleavage | Proximity-gated cleavage / circuit switch (Tier-3 computational baseline) |

Three operating modes:

1. **Explore** — retrieve evidence; refuse when evidence is insufficient  
2. **Design** — geometry → mechanistic prediction → allowlisted construct checks → Proximity Design Passport  
3. **Learn** — compare prediction with data; recommend the next informative experiment  

### Stream 1 mathematical engines (CLASP Docs)

| Layer | Module | Role |
|-------|--------|------|
| Geometry + uncertainty | `src/core/ctpr_geometry.py` | Screw-matrix CTPR coords, WLC flexibility, first-order σ |
| Assembly ODE | `src/core/clasp_assembly.py` | CaM–M13 recruitment + Spy locking + luminescence |
| Residual GP | `src/gp_model/residual_gp.py` | Matérn(ν=2.5) residual correction (small-data) |
| Stacked ensemble | `src/gp_model/stacked_ensemble.py` | ODE + GP + optional XGBoost (≥15 pts, soft dep) |
| Fisher / fit | `src/calibration/` | FIM, CRLB identifiability, bounded least-squares |
| Active learning | `src/experiment_design/bayesian_selector.py` | EI / EIG next-experiment selection |
| Prospective freeze | `src/predictions/freeze.py` | Timestamped + checksummed predictions vs observation |

CLI: `origami freeze`, `origami compare`. XGBoost is optional (`pip install -e ".[ml]"` from this clone, not from PyPI).

Streamlit Learn also surfaces Fisher/CRLB identifiability on a phenomenological fit and a synthetic Ca²⁺ stacked-ensemble demo; Design supports freeze → compare against frozen predictions.

Repository (judging artifact): [github.com/cedricwong0714/origami](https://github.com/cedricwong0714/origami)

> **Using an AI assistant?** Read [.claude/RESPONSIBLE_AI_USE.md](.claude/RESPONSIBLE_AI_USE.md) and [AGENTS.md](AGENTS.md). You remain responsible for every claim and every commit.

## Requirements

- Python **3.10+** (3.12 recommended)
- `pip` / venv

## Installation

```bash
git clone https://github.com/cedricwong0714/origami.git
cd origami
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -e ".[dev]"
```

Core dependencies are declared in [`pyproject.toml`](pyproject.toml). Optional UI extras (`streamlit`, etc.) live under `[project.optional-dependencies].ui` and [`copilot/requirements.txt`](copilot/requirements.txt).

## Quick start

### Design sandbox (input → `run_design` → result data)

```bash
pip install -e ".[ui]"
streamlit run sandbox/app.py --server.port 48621 --server.address 0.0.0.0
```

This form calls the math chassis. It does not invent sequences or mark the report calibrated.

### Structural analysis (wiki UI)

```bash
pip install -e ".[ui]"
python host_sa.py
# then, in another terminal:
cd web/structural && npm install && npm run dev -- --port 41733 --hostname 0.0.0.0
```

Scaffold-only predictions for n = 3, 8, 14. `calibrated` stays false. Use **Wiki figure** for a caption-ready screenshot.

Teammates: a **temporary** static checkpoint (saved n=8 tables, not a live host) is in [`web/checkpoint/`](web/checkpoint/). How to deploy that snapshot and how to run the real models is in [`TEAMMATES.md`](TEAMMATES.md). Vercel cannot execute the Python chassis.

### Streamlit UI (Explore / Design / Learn)

```bash
pip install -e ".[ui]"
streamlit run app.py
```

**Windows sandbox (venv + Streamlit + static demos):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_sandbox.ps1
```

See [`scripts/SANDBOX.md`](scripts/SANDBOX.md). Default URLs: http://localhost:8501 (UI) and http://localhost:8080/ (static demos).

Opens a local dashboard with four modes:

1. **Explore evidence** — retrieve parameters or refuse honestly  
2. **Design a CLASP system** — geometry, prediction, passport, allowlist checks  
3. **Optimize CTPR spacing** — rank docking Δi (Tier-3 computational ranking)  
4. **Learn from data** — ODE vs observations + next-experiment suggestions  

Synthetic Learn curves are labeled fixtures — not Tier-1 lab data.

Standalone HTML demo (same palette / corrected ORIGAMI CTPR priors):

```bash
# open locally
web/ctpr_scaffold_optimizer.html
```

The HTML files in `web/` are static demos only: the landing page and the CTPR optimizer. GitHub does not publish them as a Pages site. Open `web/index.html` and `web/ctpr_scaffold_optimizer.html` in a browser. The full chassis (SSDK learn, lab quality, multi-fidelity gates) needs `host_sa.py` plus `npm run dev` in `web/structural`, or Streamlit as above.

Wiki UI includes **Dependencies** (`/guide`), **Wizard** (`/wizard`), **SSDK** luminescence gates, **Data intake**, and **Active learning** with multi-fidelity output when the API is running.

**User manual:** [docs/USER_MANUAL.md](docs/USER_MANUAL.md). **Judges:** [docs/JUDGE.md](docs/JUDGE.md). **Model cards:** [docs/MODEL_CARDS.md](docs/MODEL_CARDS.md). **API:** [docs/API.md](docs/API.md). **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Export a team protein (n = 3, 8, or 14) without inventing DNA:

```bash
origami export-genbank --n-repeats 8
origami export-sbol --n-repeats 8
origami export-sbml --json-body '{"mode":"recruitment_steady","c_free_M":1e-6}'
origami passport --json-body '{"n_repeats":8}'
origami benchmark
```

### Validate a Learn Mode data package

```bash
origami validate-learn path/to.csv path/to.metadata.json
```

Uses templates in `data/stage1_ingestion/templates/`. Synthetic example:

```bash
origami validate-learn \
  data/stage1_ingestion/examples/learn_product_timeseries/SYN_LEARN_001.csv \
  data/stage1_ingestion/examples/learn_product_timeseries/SYN_LEARN_001.metadata.json

### Rank CTPR docking spacings (CLI)

```bash
origami optimize --radius-a 45 --radius-b 25 --interaction Metabolic
origami optimize --radius-a 30 --radius-b 30 --interaction Binding --json
```
```

### CLI pipeline (verification → MoClo → ODE → optional GP)

```bash
python -m src.ui.cli --design-id DEMO_001 --chassis E_coli
```

### Explore / Design / Learn (Python API)

```python
from src.core.schema import DesignSpec, ScaffoldSpec, MechanismType, MoCloPart
from src.compiler.expression_vector import ExpressionPlan
from src.ui.explore_mode import explore
from src.ui.design_mode import design
from src.ui.learn_mode import learn
import numpy as np

# Explore — evidence or honest refusal
print(explore("k_cat_OtsA"))

spec = DesignSpec(
    design_id="DEMO_001",
    chassis="E_coli",
    mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
    scaffold=ScaffoldSpec(
        scaffold_id="CTPR5",
        repeat_count=5,
        docking_positions=[1, 3],
    ),
    payload_ids=["OtsA", "OtsB"],
    operating_mode="reversible",
)
parts = [
    MoCloPart(
        part_id="Promoter_J23100",
        overhang_5prime="GGAG",
        overhang_3prime="AATG",
        sequence="TTGACAGCTAGCTCAGTCCTAGGTATAATACTAGT",
    ),
    MoCloPart(
        part_id="RBS_B0034",
        overhang_5prime="AATG",
        overhang_3prime="CGCT",
        sequence="AAAGAGGAGAAA",
    ),
]
plan = ExpressionPlan(
    scaffold_vector_id="vector_pETDuet",
    payload_vector_ids=["vector_dual_plasmid_set"],
    coexpression_strategy="dual_cassette",
)

result = design(spec, parts, expression_plan=plan)
print(result["status"], result["passport"]["mechanism_profile"])

t = np.linspace(0, 100, 40)
exp = 0.8 * (1.0 - np.exp(-0.04 * t))
print(learn(spec, experimental_product=exp)["next_experiment_recommendations"][:1])
```

## Tests

```bash
pytest
```

Run that command on your machine. This GitHub repository has no Actions workflow. [`.gitlab-ci.yml`](.gitlab-ci.yml) is not executed here.

## Repository layout

```
src/
  core/            Shared physical engine (CTPR, Ca²⁺, linkers, NanoBiT, sterics)
  profiles/        Mechanism Profile Standard packages
  ode_model/       Mechanism-specific kinetic solvers
  evidence_engine/ Curated parameter store + retrieval
  compiler/        Approved-parts allowlist + coexpression rules
  moclo_compiler/  Level-1 assembly + GenBank draft
  verification/    Multi-layer design checks
  ui/              Explore / Design / Optimize / Learn + CLI
  scaffold_optimizer/  CTPR Δi spacing ranking
  data_ingestion/  Learn timeseries package loaders
  compliance/      AGENTS.md discipline layer
web/               Standalone HTML demos (CTPR optimizer)
models/
  kinetic_models/        Tracked JSON rate priors (loaded by profiles)
  structure_predictions/ AF/ESM summaries (PDBs gitignored → Zenodo)
  benchmarks/            Held-out evaluation index
data/
  stage1_ingestion/      Assay metadata + Learn CSV templates/schema
  stage2_baselines/      Geometry / intracellular baselines + schema
  raw_metadata/          Assay-condition templates
tests/
  unit_tests/
  physical_invariants/
  golden_references/     Regression fixtures for Design Mode
docs/
  SSDK_ROADMAP.md             Engineering-readiness plan for SSDK, GP, BO, XGBoost
  ORIGAMI_UI_UX_Guide.md
  Verification_Checklists.md
  DEMO.md                 5-minute judge walkthrough
```

Full platform specification: [`CLASP Docs.md`](CLASP%20Docs.md)  
Dry-lab / SCALE checklist: [`ISEF 2026 Dry Lab Megadoc.md`](ISEF%202026%20Dry%20Lab%20Megadoc.md)

## 7. APIs and technicalities

# API and technical details

Base URL on a laptop: `http://127.0.0.1:41287`, started by `python host_sa.py`. Interactive schema: `/docs`. The Next.js dev server proxies `/api` to that port. Prediction responses include `calibrated: false` unless `assemble_report` was called with `evidence_source` equal to `wet_lab`. The studio does not do that. HTTP 200 is not validation.

Concentrations in the kinetics body are molar. 0.19 nM is `1.9e-10` M. The server does not convert a number that was typed in the wrong unit. Repeat counts are integers. n outside 3–24 is rejected on the chassis paths.

## Health and metadata

| Method | Path | What it returns |
|---|---|---|
| GET | `/health` | Process is up |
| GET | `/api/meta/dependencies` | Library versions the service imported |
| GET | `/api/meta/active-learning-config` | Acquisition names and the default κ |
| GET | `/api/sa/meta` | Structural model notes |

## Structure

| Method | Path | What it returns |
|---|---|---|
| GET | `/api/sa/scaffold/{n_repeats}` | One screw for that n: rise, twist, contour, rigid-screw flag, chords |
| GET | `/api/sa/library` | Payload-free backbone rows for n = 3 through 24. No clash, no \(C_\mathrm{eff}\) |
| GET | `/api/sa/predict` | Query-parameter structural prediction |

The library notes state that `rigid_screw` is true when contour is at most the 15 nm cutoff, and that the cutoff is not a retrieved persistence length. Contour for n = 8 is about 6.733 nm.

## Stability

| Method | Path | What it returns |
|---|---|---|
| GET | `/api/stability/panel` | Raw multi-series lookup |
| GET | `/api/stability/confirm` | Phillips 2012 CTPRa DSC only, at the lengths the confirmation screen shows |
| GET | `/api/stability/curve` | One-series length curve |
| GET | `/api/stability/predict` | Prediction at one n |
| GET | `/api/stability/thermo/prefill` | Cited cell when one row exists. Missing n inside the span is omitted. Outside the span, status is extrapolated and the temperature is empty. `interpolated` is false |
| POST | `/api/stability/thermo` | Caller-supplied Gibbs–Helmholtz inputs. Does not invent ΔH or ΔCp |
| POST | `/api/stability/thermo/curves` | Curve panel |
| POST | `/api/stability/thermo/effective` | Effective enthalpy under a ΔCp = 0 assumption. Not the Phillips calorimetric ΔH. `calibrated` false, `is_extrapolation` true |

For n = 8 the default length-model melting temperature is about 73.46 °C. n = 14 on the default series is extrapolated. A lab melting temperature typed into the chassis is compared with the assay temperature. It does not refit the Phillips curve.

## Docking

| Method | Path | Body |
|---|---|---|
| POST | `/api/docking/affinity` | n, affinity (`kd` or `ka`), value, unit. Optional radii |
| POST | `/api/docking/sweep` | Same tightness across n = 3–24 |
| GET | `/api/docking/geometry` | Chord, and clash plus \(C_\mathrm{eff}\) only when radii exist |

Affinity equation: \(\theta = C_\mathrm{eff}/(C_\mathrm{eff}+K_d)\). The ends are called held when \(\theta \ge 1/2\), which is \(K_d \le C_\mathrm{eff}\). That half is the definition of a dissociation constant. It is not a cutoff from a paper. NanoBiT occupancy at the printed 190 μM, and Spy \(k_\mathrm{obs} = k_\mathrm{on} C_\mathrm{eff}\), are reported on this response. The note in the payload says those payload numbers are claimed only when the association holds. Without radii, `evaluate_docking` returns `clash_computable: false` and `local_kinetics.computable: false`.

## Kinetics

| Method | Path | Body |
|---|---|---|
| GET | `/api/kinetics/schema` | Literature slots versus vacant slots, and the three simulate modes |
| GET | `/api/kinetics/scaffold` | Occupancy and tethered half-life at every n from 3 to 24. Screw chord, then Gaussian-chain \(C_\mathrm{eff}\). Cam θ uses the peptide Kd. Spy t½ = ln 2 / (k \(C_\mathrm{eff}\)) is returned twice: Zakeri \(1.4\times 10^3\) and the team fit 249.4 M⁻¹ s⁻¹. NanoBiT θ is returned twice: \(k_\mathrm{off}/k_\mathrm{on}\) and the printed 190 μM. `calibrated` is false |
| POST | `/api/kinetics/simulate` | `mode` plus the fields below |

Modes:

- `recruitment_steady`. Required: `c_free_M`. Optional: `kon_per_M_s`, `t_end_s`, `signal_on`. Default \(K_d\) is the peptide value. No on-rate means steady state only. `signal_on: false` forces \(\theta = 0\).
- `covalent_timecourse`. Optional: `tag0_M`, `catcher0_M` (default \(10\,\mu\mathrm{M}\) each), `spy_k_on_per_M_s`, `spy_k_rev_per_s`, `spy_k_bond_per_s`, `t_end_s`, `num_points`. Default path uses Zakeri \(1.4\times 10^3\,\mathrm{M}^{-1}\mathrm{s}^{-1}\) and the one-step adduct law. Both reverse and bond rates, or neither. One of them alone is HTTP 400. The studio does not send the reverse or bond rate, because they have not been measured.
- `nanobit_complementation`. Required: `lg0_M`, `sm0_M`. Optional: `nanobit_k_on_per_M_s`, `nanobit_k_off_per_s`, `t_end_s`, `num_points`. ODE uses the Dixon rates. Printed 190 μM is reported beside \(k_\mathrm{off}/k_\mathrm{on}\) and is not substituted.

`use_literature_priors: false` clears the literature slots that the caller did not replace. A vacant required rate is HTTP 400. Unknown `mode` is HTTP 400. The schema note states that literature priors emulate a fusion path so the ODE can run. They are not Hong Kong team measurements. `confidence_tier` is `hypothesis_only`.

## Combined chassis and Learn

`POST /api/ssdk/chassis`

```json
{"n_repeats": 8}
```

Optional: `indices`, `radii_A` (two values in Å), `lab_tm_C`, `kinetics`. The response has separate blocks: `structure`, `stability`, `docking`, `kinetics`. `calibrated` is false. Kinetics in this call follow the kinetics body when `kinetics.mode` is set.

`POST /api/ssdk/learn`

```json
{
  "n_min": 3,
  "n_max": 24,
  "acquisition": "ucb",
  "observations": [
    {"n_repeats": 8, "y": 0.4, "sigma": 0.05, "fidelity": 1, "source": "surrogate"}
  ]
}
```

`acquisition` is `ucb` (default, κ = 1.8), `ei`, or `entropy`. `learner` is `sklearn` (default) or `design_engine`. `fidelity` is 0 (dry) or 1 (wet). Omitted fidelity means wet. `output` is `luminescence` (default), `locking_fraction`, `expression`, `solubility`, or `purity`. Optional `sequence` is composition unless `sequence_encoding` is `onehot` or `esm2`. `batch_size` is 1 to 12. `quantify_luminescence: true` with `standard_curve` (`amount` and `rlu` lists) and `amount_units` converts luminescence rows before the learner sees them. Other outputs are not converted.

Read `next_n` for the length the page treats as primary. `recommendation.next_n`, `recommendation.design_engine_next_n`, `recommendation.multifidelity_luminescence_n`, and `recommendation.batch_n` are the other listings. They are not required to agree and they are not averaged. `gp_fitted` and `hyperparameters_optimized` are true only when at least three distinct lengths were supplied and the fit ran. `chassis_at_next_n` scores that primary length with the same chassis as `POST /api/ssdk/chassis`. With fewer than three distinct lengths, `alpha_fixed_at_one` is true. The studio hides the multi-fidelity luminescence gate while its cutoff status is `unmeasured`.

CLI: `origami ssdk chassis`, `origami ssdk learn`, `origami learn-ssdk --json-body '...'`.

## Lab

| Method | Path | Body |
|---|---|---|
| GET | `/api/lab/schema` | Slot list. Values start null |
| POST | `/api/lab/run` | `prep`, `assay_window`, `calcium`, `lock`, `bridging`, `quality` |
| POST | `/api/lab/plate` | `csv_text`, `source` |
| POST | `/api/lab/plate-vs-frozen` | Same body. Scores wells against the frozen n = 3, 8, and 14 scaffolds when `calcium_uM` is present |
| POST | `/api/lab/ablation` | Feature matrix for grouped ablation |

Plate columns: `well`, `construct`, `n_repeats`, `batch`, `role`, `rlu`. Optional `calcium_uM`, `output`, `fidelity`. `role=blank` is subtracted inside each batch. The frozen luminescence band used in plate-versus-frozen is a ±30% placeholder (`hypothesis_only`, `calibrated: false`). It is not a propagated interval from sourced ODE standard deviations. Those standard deviations were not printed.

Quality example:

```json
{"quality": {"inter_day_rlu": [100, 108, 92, 101]}}
```

## Export, literature lookup, benchmark

| Method | Path | What it returns |
|---|---|---|
| GET | `/api/export/tooltips` | Short field help |
| GET | `/api/export/genbank/{n}` | Protein GenBank for team n = 3, 8, or 14. Amino acids. Not DNA |
| GET | `/api/export/sbol/{n}` | SBOL 3 XML of the same string. Not a SynBioHub push |
| POST | `/api/export/sbml` | SBML for one shipped mode. A new ODE is rejected |
| POST | `/api/export/passport` | Chassis snapshot JSON plus sequence checksum. Not a validation certificate |
| POST | `/api/export/batch` | `{csv_text}` with an `n_repeats` column |
| POST | `/api/export/pdb` | `{pdb_text}`. Cα radius of gyration. Does not replace the CTPR screw |
| POST | `/api/export/profile` | Accepts only the three shipped mode names, and only when required fields are present |
| GET | `/api/export/benchmark` | File and exporter self-test. `calibrated: false`. Note: does not validate biology |
| POST | `/api/export/synthetic` | Labelled dry fixtures. y is chord/100 plus noise, and the payload says so |
| POST | `/api/export/plate-report` | Markdown residuals against frozen scaffolds |
| POST | `/api/literature/doi` | `{doi}`. Crossref metadata, and a Europe PMC abstract when one is present. This does not install a new prior |
| POST | `/api/literature/search` | `{query}`. Titles only. `usable_as_prior: false` |

CLI mirrors: `origami export-genbank --n-repeats 8`, `origami export-sbol`, `origami export-sbml --json-body`, `origami passport`, `origami benchmark`.

## Errors

HTTP 400 with a string `detail` means the body was rejected: non-integer n, n outside 3–24, negative concentration, non-finite number, sigma that is not a real number where a sigma is required, fidelity other than 0 or 1, one of `spy_k_rev_per_s` and `spy_k_bond_per_s` without the other, a mode name that is not one of the three, or a literature prior cleared without a replacement. The server does not fill the missing field.

## Report assembler

`origami/report.py` packages numbers the caller already computed. It does not evaluate geometry, clash, \(C_\mathrm{eff}\), occupancy, Damköhler, or the residual GP. `calibrated: true` raises unless `evidence_source` is `wet_lab`. Default `evidence_source` is `none`. If `da` is null, `p_capture` must be null, and the omitted list must name `k_escape` or `k_capture`. There is no synthetic occupancy time course. A missing series is the absence of a series.

## Repository map

- `origami/physical/` screw, Cα cloud, Gaussian-chain \(C_\mathrm{eff}\), steric overlap, recruitment isotherm.
- `origami/stability/` Phillips series, length curve, thermo prefill.
- `origami/docking/` chord, affinity, local Spy and NanoBiT scalars, length sweep.
- `origami/kinetics/` schema, recruitment call, Spy ODE, NanoBiT ODE, scaffold-length sweep (`scaffold_sweep.py`).
- `origami/mechanisms/intermediate_transfer.py` Damköhler reduction. Caller rates only. No studio screen.
- `origami/design_engine/` Matérn-5/2 residual GP and UCB / EI / entropy.
- `origami/ssdk/` chassis, learn, batch, multi-fidelity luminescence, plate quantify.
- `origami/lab/` plate reader, freeze comparison, quality.
- `origami/export/` GenBank, SBOL, SBML, passport, benchmark.
- `origami/priors.py` every biological number the chassis is allowed to use, with its source string.
- `origami/api/` HTTP routers included by `origami/api/structural.py`.
- `web/structural/` Next.js studio.
- `sandbox/app.py` Streamlit.
- `src/` earlier stack. Do not treat it as the studio chassis.
- `tests/math_chassis/` equation locks. `tests/unit_tests/` API and prior locks. `tests/physical_invariants/` physical constraints.
- `data/stability/ctpr_thermal_literature.json` cited thermal rows.
- `data/predictions/frozen/` frozen n = 3, 8, 14.
- `data/structures/payload_radii.json` deposited size scales.

## Install and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ui]"
python -m pytest tests/math_chassis tests/unit_tests -q
python host_sa.py
```

In another shell, from `web/structural`: `npm install` and `npm run dev`. The studio talks to port 41287 through the `/api` rewrite. Optional `bio` adds Biopython. Optional `ml` adds the heavier learners. The chassis does not need them.

Hosted deployments that only upload the Next app, with `/api` still pointed at localhost, cannot run these calculations. The API process has to be the same deploy’s Python service, or `STRUCTURAL_API_URL` has to point at a running API. `GET /api/meta/dependencies` returning JSON is the check that the calculators are actually attached.

## Papers cited by the implementation

What each paper is allowed to support is recorded in `docs/MODEL_AUDIT.md`. This repository does not contain `docs/wiki/01-math-rationales.md`. The short set a caller meets on the API:

- Kajander et al. (2007) DOI 10.1107/S0907444907024353. Screw.
- van Rosmalen, Krom, and Merkx (2017) DOI 10.1021/acs.biochem.7b00902. Tether width.
- Biochemistry (2006) DOI 10.1021/bi060857u. Peptide \(K_d\).
- Zakeri et al. (2012) DOI 10.1073/pnas.1115485109. Spy on-rate.
- Dixon et al. (2016) DOI 10.1021/acschembio.5b00753. NanoBiT rates and printed \(K_d\).
- Phillips et al. (2012) DOI 10.1002/pro.2018. Default stability series.
- Cortajarena and Regan (2011) DOI 10.1002/pro.564. Heat capacity where a cell exists.
- Nagai et al. (2014) DOI 10.3389/fnmol.2014.00090 and Porumb et al. (1994) DOI 10.1093/protein/7.1.109. Stored calcium figures that the Langmuir path does not use.

## Biosecurity constraints (software)

- Parts must appear on [`src/compiler/approved_parts.json`](src/compiler/approved_parts.json)
- Large ORFs are allowlisted by **ID + provenance** until checksummed DNA is deposited — ORIGAMI will not invent gene sequences
- Solo **pET28a+** hosting of scaffold + payload is rejected
- Explore Mode refuses answers when evidence confidence is insufficient
- Do not present screening-assay models as clinical diagnostics

## Data and large files

Keep this repository for **source code**. Datasets, model weights, and heavy media belong on [Zenodo](https://zenodo.org) with DOIs linked from this README once uploaded.

## Authors

**ISEF 2026 · Hong Kong team by Wong Shun Hei, Cheuk Mivon, and Fong Ming** — CLASP / ORIGAMI software track.

## License

[Apache License 2.0](LICENSE)
