# ORIGAMI / CLASP — COMPLETE HANDOFF (code + math)

Save this file and, in a new folder, extract every `===== FILE:` block into that path.
Prompt for the next agent: read docs/MODEL_AUDIT.md, keep tests green, do not invent k_on, k_cat, or K_m.

Recruitment ODE: origami/physical/recruitment.py
Damköhler ODE: origami/mechanisms/intermediate_transfer.py


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


## FULL SOURCE

===== FILE: pyproject.toml =====
```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "origami-clasp"
version = "0.1.0"
description = "ORIGAMI: mechanism-aware design engine for CLASP protein proximity"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "numpy>=1.26",
  "scipy>=1.12",
  "pydantic>=2.6",
  "streamlit>=1.32",
  "plotly>=5.20",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.setuptools.packages.find]
include = ["origami*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

===== FILE: .gitignore =====
```text
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
build/
.streamlit/
.coverage
htmlcov/
```

===== FILE: README.md =====
```markdown
# ORIGAMI / CLASP

Mechanism-aware design engine for programmable protein proximity (ISEF software).

This repository is **not** a calibrated wet-lab model. Geometry and steric
numbers are literature-informed engineering priors. The learning engine is a
**residual Gaussian process** plus **discrete Bayesian optimization** over CTPR
repeat counts. Lab measurements can be added later without rewriting the math.

## What it does

1. **CTPR geometry** — docking sites from SE(3) helical repeats (rotation + rise), not a straight ruler. Positional uncertainty from a Jacobian of the helical parameters.
2. **Steric hindrance probability** — P(payload spheres overlap) with Gaussian coordinate covariance (delta method; Monte Carlo in tests). This is the clustered-enzyme failure mode.
3. **Gaussian-chain C_eff** — polymer local concentration vs separation. Not a GP.
4. **Residual GP** — Matérn-5/2 kernel, Cholesky posterior  
   \(y = \alpha S_{\text{physics}}(n) + \beta + r(n) + \varepsilon\), \(r \sim \mathcal{GP}(0,k)\).
5. **Active learning** — discrete UCB / entropy / expected improvement over the allowed CTPR library. Recommends the **next assay**, not a validated construct.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
streamlit run app.py --server.port 48651 --server.address 0.0.0.0
```

## Honest claims

- Agriculture / diagnostic / hydrogen mechanism ODEs are **not** in this slice.
- Priors are **not** this team's measurements. Replace them when assays exist.
- User-entered points in the UI are not wet-lab records unless you mark them as such.

See **`ORIGAMI_COMPLETE_HANDOFF.md`** (full code + math, for emailing another computer), plus `HANDOFF.md`, `docs/MATH.md`, and `docs/STATUS.md`.
```

===== FILE: HANDOFF.md =====
```markdown
# HANDOFF — continue ORIGAMI / CLASP in another Cursor agent

**If you need to email progress:** use **`ORIGAMI_COMPLETE_HANDOFF.md`** (full math + every source file, ~120 KB). This short file is only an index.

**Read first on the other computer:** `ORIGAMI_COMPLETE_HANDOFF.md`, then `AGENTS.md`, then `docs/MATH.md`.


---

## What this project is

**CLASP** = modular molecular hardware for *conditional protein organization* (CTPR scaffold + recruited payloads).  
**ORIGAMI** = software that turns a biological objective into geometry, a mechanism-specific model, uncertainty, a construct, and a next experiment.

It is **not** “optimize sequential enzymes only.” Shared physics first, then a mechanism profile (intermediate transfer, complementation, redox, covalent capture).

Central rule: **do not be fast at the wrong thing.** Do not invent \(k_{\mathrm{cat}}\), \(K_d\), citations, or lab results. Every biological number needs provenance.

---

## What is already implemented (this repo)

Runnable Python package + Streamlit demo. **15 pytest tests**, all passing at last handoff.

| Piece | Path | What it actually does |
|---|---|---|
| CTPR geometry | `origami/physical/geometry.py` | SE(3) helical repeats (rotation + rise). **Not a straight ruler.** Jacobian → positional covariance |
| Steric probability | `origami/physical/steric.py` | \(P(\)payload spheres overlap\()\) via delta method; MC in tests. Payloads sit **outward** of the fusion point |
| Gaussian-chain \(C_{\mathrm{eff}}\) | `origami/physical/linkers.py` | Polymer \(C_{\mathrm{eff}}(r)\). **This is not a GP** |
| Physics score | `origami/physical/score.py` | \((1-P_{\mathrm{instability}})\log_{10}(1+C_{\mathrm{eff}}/C_{\mathrm{ref}})\) |
| Residual GP | `origami/design_engine/gp.py` | Matérn-5/2, Cholesky, optional LML hyperfit. \(y=\alpha S+\beta+r(x)+\varepsilon\) |
| Discrete BO | `origami/design_engine/active_learning.py` | UCB / entropy / EI over integer CTPR \(n\). Output = **next assay** |
| Orchestrator | `origami/engine.py` | `ClaspDesignEngine` + `Observation` |
| Priors | `origami/priors.py` | All constants tagged `literature_placeholder`, `calibrated=False` |
| Schemas | `origami/schemas/design.py` | `DesignSpec` / `PayloadSpec` (typed; profiles not fully wired) |
| UI | `app.py` | Streamlit: 3D helix, clash table, GP band, add observations, priors tab |
| Agent rules | `AGENTS.md` | Mandatory behaviour for any coding agent |

**Default demo:** two payloads at repeats `0` and `n-1` (end-to-end enzyme pair). Candidate library is discrete \(n \in [3,24]\).

---

## What is *not* implemented yet

Do not tell the user these exist.

- Recruitment **ODE** (CaM–M13 occupancy, locking)
- Intermediate-transfer **ODE + Damköhler** (diffusion reduced to \(C_{\mathrm{eff}}\), not a 3D PDE solver)
- Covalent-capture kinetics, complementation, redox/Marcus ranking
- Wet-lab data import (`Observation(source="wet_lab")` exists as a field; no assay tables)
- Design Passport, compiler, verification layers, evidence retrieval
- Four-profile Streamlit walking skeleton
- Structure-fitted CTPR rise/twist (current values are **engineering priors** informed by Kajander et al. 2007 / PDB 2AVP, 2HYZ, 2FO7 — **not refit from coordinates**)

---

## Math the next agent must not confuse

| Name | Role | Status |
|---|---|---|
| Gaussian **chain** | linker reach / \(C_{\mathrm{eff}}\) | implemented |
| Gaussian **process** | residual after physics, with 95% interval | implemented |
| ODE | occupancy and catalysis vs time | **next science slice** |
| PDE | only as Damköhler + \(C_{\mathrm{eff}}\) in MVP; no 3D solver | not started |
| Bayesian optimization | discrete next-experiment on the GP posterior | implemented |

Order that must not reverse: geometry → steric/\(C_{\mathrm{eff}}\) → (later) ODEs → GP residual → BO.  
Physics without GP is valid. GP without physics is forbidden. BO without a GP has nothing Bayesian to optimize.

---

## Honest scientific state

- **No project laboratory measurements are in the model.**
- UI points are `source="user_entered"` until someone imports assays as `wet_lab`.
- Do not claim ORIGAMI is calibrated, or that enzyme geometry validates hydrogen/diagnostics.
- Evidence level today: `literature_supported` with no observations; `computationally_evaluated` after user-entered points.

---

## How to run (other computer)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
streamlit run app.py --server.port 48651 --server.address 0.0.0.0
```

Requires Python ≥ 3.11, numpy, scipy, pydantic, streamlit, plotly, pytest.

---

## Call order of the engine

1. `build_ctpr(n)` → docking frames + covariance  
2. `steric_report` + `gaussian_chain_ceff` → physics score \(S(n)\)  
3. If observations exist: `ResidualGP.fit(X, y, S)` then `predict`  
4. `recommend(...)` → integer \(n\) for the next assay  

Entry point: `ClaspDesignEngine.run()` in `origami/engine.py`.

---

## What to implement next (in order)

### 1. Recruitment ODE (shared physical engine)

Signal-dependent association / dissociation / occupancy for CaM–M13. Steady-state is acceptable first; time course after. **Do not invent \(k_{\mathrm{on}}\), \(k_{\mathrm{off}}\).** Add literature priors in `origami/priors.py` with sources, or leave parameters required-but-missing and refuse to numerically pretend.

### 2. Damköhler-reduced intermediate transfer

Use existing \(C_{\mathrm{eff}}\) and occupancy. Capture vs escape as \(Da\), then ODEs — **not** a PDE solver.

### 3. Wet-lab observation schema

CSV/Parquet import into `Observation(n_repeats, y, source="wet_lab", units=...)`. Keep user-entered and wet-lab separate. Recalibrate only after a recorded prediction freeze (see CLASP plan §9.1).

### 4. Replace helical priors

Fit rise/twist from CTPR structures or lab, store as `provenance="wet_lab"` or `structure_derived`, `calibrated=True`.

### 5. Walking skeleton for four mechanism profiles

Same `MechanismProfile` interface (`origami/mechanisms/base.py`). Placeholder `predict()` returning one result envelope + Passport shell.

**Do not start:** microservices, live structure prediction, full MD, Fisher-information design, COPASI, claiming clinical diagnostics.

---

## Files another agent should open

1. This file — `HANDOFF.md`  
2. `AGENTS.md` — hard rules (no fabricated science, ask before extra deps, etc.)  
3. `docs/MATH.md` — why each model exists  
4. `docs/STATUS.md` — short status table  
5. `origami/engine.py` — wiring  
6. `origami/priors.py` — every number’s provenance  
7. `tests/` — expected invariants  

If the user still has **CLASP Docs.md** (ORIGAMI twelve-week plan), that is the product spec for profiles, Passport, and evidence-maturity. It is not in this repo unless they re-attach it.

---

## Suggested first prompt on the other computer

> Read HANDOFF.md and AGENTS.md. Continue ORIGAMI from the current engine. Next slice: recruitment ODE + Damköhler-reduced intermediate transfer, with literature-tagged parameters only (no invented constants). Keep the residual GP and discrete BO. Do not add a new UI framework.

---

## Product claims you may / may not make

**May:** ORIGAMI separates shared CLASP recruitment physics from mechanism-specific models; geometry and steric uncertainty are explicit; a residual GP + discrete BO recommend the next assay; current numbers are literature priors.

**May not:** ORIGAMI proves an unbuilt application; enzyme data validate hydrogen or diagnostics; the GP is trained on this team’s wet lab; the system is synthesis-ready or universally validated.
```

===== FILE: docs/MATH.md =====
```markdown
# ORIGAMI math: why, where, what we implement

ORIGAMI is not “optimize an enzyme.” It is:

**CLASP hardware** (conditional protein organization) → **shared physics** → **mechanism-specific function** → **uncertainty** → **next experiment**.

Wet lab is slow. Models exist so we can (1) reject impossible designs, (2) rank feasible ones, (3) say how unsure we are, (4) pick the next measurement that reduces that uncertainty.

Do not confuse two different “Gaussians”:

| Name | What it is | Role here |
|---|---|---|
| **Gaussian chain** | Polymer model for a flexible linker | Shared physical engine: linker reach / \(C_{\mathrm{eff}}\) |
| **Gaussian process (GP)** | Bayesian regressor with uncertainty | Design engine: correct physics residuals after wet-lab data |

---

## Folder map (inferred from the plan)

The CLASP plan is a modular monolith, not a folder dump. Code should live here:

```text
origami/
  schemas/              # DesignSpec, PayloadSpec, MechanismProfile interface
  physical/             # shared CLASP hardware (all profiles use this first)
    geometry/           # CTPR coordinates, docking sites, orientations
    linkers/            # Gaussian-chain reach, C_eff  (not a GP)
    steric/             # sphere/ellipsoid clash checks
    recruitment/        # ODEs: occupancy, CaM–M13, locking
  mechanisms/           # one package per profile, same interface
    intermediate_transfer/   # reference: ODE + Damköhler (PDE-lite)
    complementation/
    redox/
    covalent_capture/        # kinetic ODE
  design_engine/
    gp/                 # GP residual correction          ← code next
    active_learning/    # Bayesian optimization          ← code next
  evidence/             # retrieval, citations, maturity
  compiler/             # parts → construct
  verification/         # sequence, biology, safety
  passport/             # Design Passport assembly
  data/                 # parts, parameters, experiments (no invented numbers)
```

Call order for every run:

1. `schemas` validate the request
2. `physical` asks: can this assembly exist?
3. `mechanisms/<profile>` asks: if it exists, what function?
4. `design_engine/gp` corrects that prediction if calibration data exist
5. `design_engine/active_learning` proposes the next experiment
6. `verification` + `passport` wrap the result

---

## The four math tools

### 1. ODEs — time and occupancy

**Why.** CLASP is kinetic: payloads bind, unbind, lock, and catalyze. Function is a rate, not a static pose.

**Where.**

| Location | What the ODE is for |
|---|---|
| `physical/recruitment` | Signal on/off, association/dissociation, site occupancy, competition, optional covalent lock |
| `mechanisms/intermediate_transfer` | Michaelis–Menten production, capture, product |
| `mechanisms/covalent_capture` | SpyTag–SpyCatcher conversion vs time |
| phosphorylation / trans-activation (later) | \(k_{\mathrm{cat,trans}}\) vs basal, dephosphorylation flux |

**What we need.** Systems of the form \(\dot{x} = f(x, \theta)\). Outputs: occupancy, conversion, product vs time. Always intervals, never a single exact number.

**What we do not need yet.** Stochastic simulation or COPASI (stretch).

---

### 2. PDEs — space, then reduce

**Why.** Intermediate-transfer fails when the product **diffuses away** before the next enzyme captures it. That is reaction–diffusion. The Damköhler number is exactly “reaction vs escape.”

**Where.** `mechanisms/intermediate_transfer` only (reference profile). Linker \(C_{\mathrm{eff}}(r,\sigma^2)\) in `physical/linkers` is the spatial input those rates see.

**What we need in the MVP.** Not a 3D PDE solver.

Reduce space to:

- Gaussian-chain \(C_{\mathrm{eff}}\) from scaffold distance \(r\)
- Damköhler \(Da = k_{\mathrm{capture}} / k_{\mathrm{escape}}\)
- ODEs whose rates depend on \(C_{\mathrm{eff}}\) and \(Da\)

**Full PDE** (concentration field \(c(\mathbf{x},t)\)) is later, if the reduced model is not enough.

---

### 3. Gaussian processes — residual + uncertainty

**Why.** The physics model will be wrong in a structured way. After a few wet-lab points we must (a) correct it and (b) know where we are interpolating vs extrapolating. A GP is the smallest model that does both.

**Where.** `design_engine/gp`, owned by Person B. Wired only to the **intermediate-transfer** (production) profile at first.

**What we need.**

\[
y_{\mathrm{obs}}(x) = y_{\mathrm{physics}}(x) + r(x) + \varepsilon
\]

\(r(x) \sim \mathcal{GP}(0, k_\theta)\) learns the residual. \(x\) is a design vector (scaffold length, linker, enzyme ratio, …).

Use the GP for:

- median + 95% interval on the **corrected** prediction
- “interpolated vs extrapolated”
- sensitivity of the residual, not replacement of physics

**What we do not need.** Using a GP as the whole predictor. No physics → no GP.

---

### 4. Bayesian optimization — next experiment

**Why.** Many scaffold/linker/ratio choices; few assays. ORIGAMI must recommend **the next experiment that reduces uncertainty most** (or most improves expected function). That is active learning / BO, not a grid search.

**Where.** `design_engine/active_learning`. Consumes the GP posterior. Feeds the Design Passport “recommended next experiment.” Weeks 7–10 in the plan.

**What we need.**

1. A cheap surrogate: the GP on residuals (or on a scalar score derived from the physics+GP).
2. An acquisition function, e.g. expected improvement **or** (preferred here) **uncertainty / information gain** — the product is “which measurement helps,” not “which clickbait optimum.”
3. A discrete candidate set (allowed CTPR lengths, linkers, ratios) so we never optimize off the parts list.

**Stretch, not now.** Formal Fisher-information design.

---

## Dependency order (code this, not the reverse)

```text
geometry + Gaussian-chain C_eff
        → recruitment ODEs
        → mechanism ODEs (Damköhler-reduced diffusion)
        → GP residual  ← next coding step
        → BO / next-experiment  ← next coding step
```

Physics without GP: still a valid ranked prediction with parameter intervals.  
GP without physics: forbidden.  
BO without GP: nothing to be Bayesian about.

---

## MVP vs later

| Tool | MVP | Strong | Stretch |
|---|---|---|---|
| ODE recruitment + MM | yes | — | stochastic / COPASI |
| PDE | **reduced** (C_eff + Da) | same | spatial field |
| GP residual | — | yes, reference profile | more profiles |
| BO / next experiment | — | yes | Fisher information |

Next implementation: math scaffold only for **GP** and **BO** in `origami/design_engine/`, with fake-data unit tests and **no invented biological constants**.
```

===== FILE: docs/STATUS.md =====
```markdown
# ORIGAMI status and next build

## What is in place now

Runnable Python engine (not a calibrated biological predictor).

| Asset | Status |
|---|---|
| `AGENTS.md` | agent behaviour rules |
| `docs/MATH.md` | why ODEs / PDEs / GPs / BO |
| `origami/physical/geometry.py` | SE(3) CTPR superhelix + Jacobian covariance |
| `origami/physical/steric.py` | P(clash) for clustered payloads |
| `origami/physical/recruitment.py` | Langmuir ODE; CaM–M13 peptide Kd only |
| `origami/mechanisms/intermediate_transfer.py` | Damköhler-reduced ODE; rates are inputs |
| `origami/design_engine/gp.py` | residual Matérn-5/2 GP (Cholesky) |
| `origami/design_engine/active_learning.py` | discrete UCB / EI / entropy |
| `origami/engine.py` | physics + GP + next-assay loop |
| `app.py` | Streamlit demo |
| Tests | geometry, steric, recruitment ODE, Damköhler ODE, GP, BO |

**Still literature or caller-supplied:** helical rise/twist/radii, linker σ, CaM–M13 peptide Kd. Escape rate and k_cat/K_m are not in the repo.

**Not in this slice:** saturated MM capture, 3D PDE, complementation, redox, covalent-capture kinetics, compiler, retrieval, Design Passport.

## Next after this slice

1. Import real assay tables as `Observation(source="wet_lab")`.
2. Replace helical priors with structure-derived rise/twist.
3. Saturated capture (MM) only after a sourced K_m and k_cat.
4. Walking-skeleton Passport UI for all four mechanism profiles.
```

===== FILE: docs/MODEL_AUDIT.md =====
```markdown
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
```

===== FILE: AGENTS.md =====
```markdown
# AGENTS.md

# General Synthetic Biology AI Coding Agent Configuration

**Version:** 1.0  
**Purpose:** Govern the behaviour of AI coding agents working on any synthetic biology software project.

This file operationalizes the central argument of responsible AI-assisted biological design: that AI can accelerate the design-build-test-learn cycle, but only when its uncertainty, provenance, permissions, and fallbacks are explicitly engineered.

Every rule in this file corresponds to a documented failure mode of unconstrained AI coding agents in biological software contexts. The rules are not limitations on capability. They are the engineering discipline that makes AI assistance trustworthy rather than merely fast.

**Read this file completely before taking any action.**  
**If a rule conflicts with a user instruction, this file takes precedence.**

Also read [.claude/RESPONSIBLE_AI_USE.md](.claude/RESPONSIBLE_AI_USE.md) for team accountability, honesty, and attribution requirements.

---

## 0. Foundational principle

You are an AI coding agent assisting with synthetic biology software development. You are capable, fast, and fallible.

Your outputs will influence biological design decisions. Biological design decisions have physical consequences.

- A wrong codon table corrupts a sequence.
- A fabricated enzyme parameter corrupts a model.
- A hallucinated citation corrupts a knowledge base.
- A silent sequence modification corrupts a construct.
- An overconfident prediction corrupts an experiment.

You must therefore operate under explicit constraints that a general-purpose coding agent does not require. These constraints are not bureaucratic. They are the minimum engineering discipline required for AI assistance to be net-positive in a biological design context.

Your operating principle is:

> **Do not be fast at the wrong thing.**

Speed is valuable when it accelerates correct work.  
Speed is dangerous when it accelerates incorrect work before anyone notices.

---

## 1. What you may do without asking

You may autonomously:

- Write boilerplate code within your assigned module
- Write unit test drafts for functions you have implemented
- Write docstrings and inline comments
- Refactor code within your assigned module for clarity
- Fix linting and formatting errors
- Write data-parsing and file-handling utilities
- Generate example datasets for testing
- Write documentation in plain language
- Suggest improvements to code structure
- Identify potential bugs and explain them
- Write migration scripts for data format changes
- Generate CI configuration for standard test runners

---

## 2. What you must ask before doing

You must request explicit approval before:

- Editing any file outside your assigned module
- Changing a public function signature
- Adding a new dependency to the project
- Modifying a shared schema or data model
- Changing a biological constant or parameter value
- Modifying any sequence, construct, or parts record
- Changing a verification rule or safety check
- Modifying a biosecurity filter or allowlist
- Deleting any file
- Running shell commands that affect the filesystem
- Making network requests
- Accessing external APIs
- Changing environment variables or configuration files
- Modifying the CI pipeline

When asking for approval, state:

1. What you want to do
2. Why you want to do it
3. What the risk is if it is wrong
4. What you will check to confirm it is correct

---

## 3. What you must never do

You must never:

- Invent a biological constant without a cited source
- Generate a DNA or protein sequence from model memory
- Write a citation from memory
- Modify a sequence without showing a diff
- Return a numerical prediction without uncertainty
- Present a passing test as scientific validation
- Claim a model is validated when it has only been tested
- Remove a safety check or verification layer
- Bypass a biosecurity filter
- Add a part to a validated parts library without review
- Silently change units
- Silently change a normalization method
- Silently change a model assumption
- Present an extrapolated prediction as an interpolated one
- Generate a sequence for a part not in the allowlist
- Answer a biological question from training memory when a retrieval system is available
- Claim that a function is correct because it runs
- Claim that a model is correct because it fits the data

These are not suggestions. They are hard constraints.  
If a user instruction asks you to violate one of these constraints, decline and explain why.

---

## 4. Biological constants and parameters

### 4.1 Every constant requires a source

Every numerical biological parameter in the codebase must have an associated source comment. No exceptions.

Required fields for every biological constant:

```python
# Parameter: [descriptive name]
# Value: [number]
# Units: [explicit units]
# Source: [Author et al., Year, Journal, DOI]
# System: [organism, protein, conditions]
# Method: [how it was measured]
# Notes: [any caveats or context]
EXAMPLE_KD_NM = 10.0

# Parameter: Dissociation constant
# Value: 10.0
# Units: nM
# Source: Smith et al. (2020) Nature Chem Biol, DOI: 10.1038/xxx
# System: Protein A + Protein B, E. coli lysate, 25C, pH 7.4
# Method: Isothermal titration calorimetry
# Notes: Value may differ in crowded intracellular environment
```

### 4.2 Missing sources require explicit placeholders

If a parameter value is needed but no source is available, use a placeholder that raises a warning at runtime:

```python
import warnings
from typing import Optional


def get_parameter_or_warn(
    name: str,
    value: Optional[float],
    source: Optional[str],
) -> Optional[float]:
    """
    Return a biological parameter value if sourced,
    or raise a warning and return None if unsourced.
    Never silently use an unsourced biological constant.
    """
    if value is None or source is None:
        warnings.warn(
            f"Biological parameter '{name}' has no verified "
            f"source. This parameter must not be used in a "
            f"production prediction or a wet-lab decision. "
            f"Find a peer-reviewed source before proceeding.",
            UserWarning,
            stacklevel=2,
        )
        return None
    return value
```

### 4.3 Parameter ranges are preferred over point estimates

Where possible, represent biological parameters as ranges rather than single values. This reflects the reality that biological measurements vary across conditions, organisms, and experimental methods.

```python
from dataclasses import dataclass
from typing import Optional
import warnings


@dataclass
class BiologicalParameter:
    name: str
    value: float
    units: str
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    source: str
    system: str
    confidence: str  # "high", "medium", "low"
    notes: str

    def is_within_range(self, test_value: float) -> bool:
        if self.lower_bound is None or self.upper_bound is None:
            return True
        return self.lower_bound <= test_value <= self.upper_bound

    def warn_if_extrapolating(self, test_value: float) -> None:
        if not self.is_within_range(test_value):
            warnings.warn(
                f"Value {test_value} {self.units} is outside "
                f"the validated range [{self.lower_bound}, "
                f"{self.upper_bound}] {self.units} for "
                f"parameter '{self.name}'. Predictions using "
                f"this value are extrapolations.",
                UserWarning,
                stacklevel=2,
            )
```

---

## 5. Sequence handling rules

### 5.1 All sequence operations must be deterministic

Sequence assembly, modification, and export must produce identical outputs for identical inputs every time. No randomness. No model-generated sequences. No silent modifications.

```python
import hashlib
from Bio.Seq import Seq


def compute_sequence_checksum(sequence: str) -> str:
    """
    Compute a SHA-256 checksum of a biological sequence.
    Use this to verify that sequences have not been
    silently modified between operations.
    Always normalize to uppercase before checksumming.
    """
    normalized = sequence.upper().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def verify_sequence_unchanged(
    original: str,
    modified: str,
    operation_name: str,
) -> None:
    """
    Verify that a sequence operation did not unintentionally
    change the sequence. Raise an error if checksums differ
    and the change was not explicitly declared.
    """
    original_checksum = compute_sequence_checksum(original)
    modified_checksum = compute_sequence_checksum(modified)
    if original_checksum != modified_checksum:
        diff = compute_sequence_diff(original, modified)
        raise UnexpectedSequenceModificationError(
            f"Operation '{operation_name}' changed the sequence "
            f"without explicit declaration. "
            f"Original checksum: {original_checksum}. "
            f"Modified checksum: {modified_checksum}. "
            f"Diff: {diff}. "
            f"If this change was intentional, declare it "
            f"explicitly in the function call."
        )
```

### 5.2 Reading frames must be verified after every modification

```python
def verify_reading_frame(
    sequence: str,
    expected_protein: str,
    sequence_id: str,
) -> ReadingFrameResult:
    """
    Verify that a coding sequence translates to the expected
    protein. Check for internal stop codons, frame shifts,
    and unexpected amino acid changes.

    This must be called after every sequence modification,
    codon optimization, or assembly operation.
    """
    seq = Seq(sequence)
    if len(seq) % 3 != 0:
        return ReadingFrameResult(
            valid=False,
            error=(
                f"Sequence '{sequence_id}' length {len(seq)} "
                f"is not divisible by 3. Frame shift detected."
            ),
        )

    translated = str(seq.translate())
    internal_stops = translated[:-1].count("*")
    if internal_stops > 0:
        stop_positions = [
            i for i, aa in enumerate(translated[:-1]) if aa == "*"
        ]
        return ReadingFrameResult(
            valid=False,
            error=(
                f"Sequence '{sequence_id}' contains "
                f"{internal_stops} internal stop codon(s) "
                f"at positions: {stop_positions}."
            ),
        )

    if expected_protein and translated[:-1] != expected_protein:
        return ReadingFrameResult(
            valid=False,
            error=(
                f"Sequence '{sequence_id}' translates to an "
                f"unexpected protein. "
                f"Expected: {expected_protein[:20]}... "
                f"Got: {translated[:20]}..."
            ),
        )

    return ReadingFrameResult(valid=True, protein=translated)
```

### 5.3 Forbidden restriction sites must be checked

```python
COMMON_FORBIDDEN_SITES = {
    "BsaI": "GGTCTC",
    "BsmBI": "CGTCTC",
    "BbsI": "GAAGAC",
    "EcoRI": "GAATTC",
    "SpeI": "ACTAGT",
    "XbaI": "TCTAGA",
    "PstI": "CTGCAG",
    "NotI": "GCGGCCGC",
}


def check_forbidden_sites(
    sequence: str,
    forbidden_sites: dict[str, str] | None = None,
    sequence_id: str = "unknown",
) -> ForbiddenSiteResult:
    """
    Check a sequence for the presence of forbidden
    restriction sites. Returns all found sites with
    their positions.
    """
    if forbidden_sites is None:
        forbidden_sites = COMMON_FORBIDDEN_SITES

    seq_upper = sequence.upper()
    found = {}

    for site_name, recognition_seq in forbidden_sites.items():
        positions = []
        start = 0
        while True:
            pos = seq_upper.find(recognition_seq, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1

        rev_comp = str(Seq(recognition_seq).reverse_complement())
        start = 0
        while True:
            pos = seq_upper.find(rev_comp, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1

        if positions:
            found[site_name] = {
                "recognition_sequence": recognition_seq,
                "positions": sorted(positions),
            }

    return ForbiddenSiteResult(
        sequence_id=sequence_id,
        found_sites=found,
        passed=len(found) == 0,
    )
```

---

## 6. Prediction and modelling rules

### 6.1 Every prediction must carry uncertainty

```python
from pydantic import BaseModel
from typing import Literal


class PredictionResult(BaseModel):
    """
    Standard output for any biological prediction.
    A bare numerical value without uncertainty is not
    an acceptable output from a biological model.
    """

    predicted_value: float
    units: str
    uncertainty_95_lower: float
    uncertainty_95_upper: float
    confidence_tier: Literal[
        "validated",
        "interpolated",
        "extrapolated",
        "hypothesis_only",
    ]
    is_extrapolation: bool
    model_name: str
    model_version: str
    parameter_sources: list[str]
    assumptions: list[str]
    warnings: list[str]
    human_review_required: bool
    most_sensitive_parameter: str | None

    def display_summary(self) -> str:
        return (
            f"{self.predicted_value:.3f} {self.units} "
            f"[95% CI: {self.uncertainty_95_lower:.3f}–"
            f"{self.uncertainty_95_upper:.3f}] "
            f"({self.confidence_tier})"
            + ("  EXTRAPOLATION" if self.is_extrapolation else "")
            + (
                "  HUMAN REVIEW REQUIRED"
                if self.human_review_required
                else ""
            )
        )
```

### 6.2 Confidence tiers must be assigned honestly

```python
def assign_confidence_tier(
    design_parameters: dict,
    calibrated_ranges: dict,
) -> tuple[str, bool]:
    """
    Assign a confidence tier to a prediction based on whether
    the design parameters fall within calibrated ranges.
    Returns the tier name and whether extrapolation is occurring.

    Tiers:
    - validated: direct experimental data for this exact design
    - interpolated: design lies between calibrated data points
    - extrapolated: design lies outside calibrated range but
      within the same mechanism and chassis
    - hypothesis_only: design changes mechanism, chassis, or
      assay format beyond any calibrated system
    """
    if is_exact_match(design_parameters, calibrated_ranges):
        return "validated", False
    if is_within_calibrated_range(design_parameters, calibrated_ranges):
        return "interpolated", False
    if is_same_mechanism_and_chassis(design_parameters, calibrated_ranges):
        return "extrapolated", True
    return "hypothesis_only", True
```

### 6.3 Scientific invariants must be tested

Write tests that verify physical and biological constraints, not just code execution. These are the most important tests in a biological software project.

Template for a scientific invariant test:

```python
def test_[invariant_name]():
    """
    [State the physical or biological law being tested.]
    Scientific basis: [cite the principle or paper].
    Failure mode: [what it means if this test fails].
    """
    # Arrange
    # [set up the test conditions]

    # Act
    result = ...  # call the function

    # Assert
    assert condition, (
        f"[Describe what went wrong in biological terms]. "
        f"Expected [X], got [Y]. "
        f"This violates [the physical or biological principle]. "
        f"Check [the most likely cause of failure]."
    )
```

### 6.4 Model fitting must report identifiability

```python
def fit_model_with_identifiability_check(
    model_func,
    parameters: list[str],
    data: dict,
    bounds: dict,
) -> FittingResult:
    """
    Fit a model to experimental data and check whether
    all parameters are identifiable from the available data.

    A parameter is non-identifiable if its value cannot be
    uniquely determined from the data — for example, if two
    parameters always appear as a product and cannot be
    separated.

    Non-identifiable parameters must be reported explicitly.
    They must not be presented as fitted values.
    """
    fitted_values, covariance = fit(model_func, data, bounds)
    parameter_uncertainties = extract_uncertainties(covariance)
    non_identifiable = [
        param
        for param, uncertainty in zip(parameters, parameter_uncertainties)
        if uncertainty > IDENTIFIABILITY_THRESHOLD or not is_finite(uncertainty)
    ]
    if non_identifiable:
        warnings.warn(
            f"The following parameters cannot be uniquely "
            f"determined from the available data: "
            f"{non_identifiable}. "
            f"These parameters should be fixed at literature "
            f"values or their uncertainty should be reported "
            f"as 'not identifiable from current data'.",
            UserWarning,
            stacklevel=2,
        )
    return FittingResult(
        fitted_values=fitted_values,
        uncertainties=parameter_uncertainties,
        non_identifiable_parameters=non_identifiable,
        data_points_used=len(data),
        degrees_of_freedom=len(data) - len(parameters),
    )
```

---

## 7. Evidence and retrieval rules

### 7.1 Never answer a biological question from training memory

When a retrieval system is available, always use it. Do not use training-data knowledge to answer biological questions, even if you are confident in the answer. Training-data knowledge cannot be cited, audited, or updated.

```python
def answer_biological_question(
    query: str,
    retrieval_system,
    allow_memory_fallback: bool = False,
) -> AnswerResult:
    """
    Answer a biological question using the retrieval system.
    Never use model training memory as the primary source.

    Parameters
    ----------
    allow_memory_fallback : bool
        If True, the model may use training memory when
        retrieval confidence is very low, but must clearly
        label the answer as coming from model memory and
        require human verification.
        Default is False. Only set to True for non-critical
        background context questions.
    """
    retrieved = retrieval_system.retrieve(query)
    confidence = retrieval_system.compute_confidence(retrieved)

    if confidence < MINIMUM_RETRIEVAL_CONFIDENCE:
        if allow_memory_fallback:
            return AnswerResult(
                answer=generate_from_memory(query),
                source="model_training_memory",
                confidence=confidence,
                human_review_required=True,
                warning=(
                    "This answer was generated from model "
                    "training memory because retrieval "
                    "confidence was insufficient. It has not "
                    "been verified against primary sources. "
                    "Do not use this answer to make a wet-lab "
                    "decision without human verification."
                ),
            )
        return AnswerResult(
            answer=(
                "Insufficient evidence in the retrieval corpus "
                "to answer this question reliably. "
                "Human literature review is required."
            ),
            source="none",
            confidence=confidence,
            human_review_required=True,
        )

    return generate_from_retrieved_context(query, retrieved)
```

### 7.2 Citations must be attached programmatically

```python
def attach_citations(
    answer_text: str,
    retrieved_passages: list[dict],
) -> CitedAnswer:
    """
    Attach citations to an answer programmatically from
    retrieved source records.
    The language model must not write citations.
    Citations are facts about sources, not generated text.
    A hallucinated citation is worse than no citation because
    it creates false confidence in an unsupported claim.
    """
    citations = []
    for passage in retrieved_passages:
        citations.append(
            {
                "source_id": passage["source_id"],
                "title": passage["title"],
                "authors": passage["authors"],
                "year": passage["year"],
                "doi": passage.get("doi"),
                "source_type": passage["source_type"],
                "peer_reviewed": passage["peer_reviewed"],
                "extracted_passage": passage["text"],
                "relevance_score": passage["score"],
            }
        )
    return CitedAnswer(
        text=answer_text,
        citations=citations,
        all_citations_from_retrieval=True,
        no_memory_citations=True,
    )
```

### 7.3 Separate evidence types in every answer

Every answer to a biological question must explicitly separate:

```python
class StructuredBiologicalAnswer(BaseModel):
    direct_evidence: str
    # What the retrieved sources explicitly state.
    # Must be directly traceable to a citation.

    model_inference: str
    # What can be reasonably inferred from the sources.
    # Must be clearly labelled as inference, not fact.

    engineering_recommendation: str
    # What a designer might consider based on the evidence.
    # Must be clearly labelled as a recommendation.

    unknown: str
    # What cannot be answered from the current corpus.
    # Must explicitly state what information is missing.

    citations: list[dict]
    confidence: str
    human_review_required: bool
    human_review_reason: str | None
```

---

## 8. Data integrity rules

### 8.1 Raw data must never be overwritten

```python
import shutil
from pathlib import Path
from datetime import datetime


def safe_write_experimental_data(
    data: dict,
    filepath: Path,
    overwrite: bool = False,
) -> Path:
    """
    Write experimental data safely.
    Raw experimental data is immutable once recorded.
    If a file already exists, create a versioned backup
    before writing. Never silently overwrite.
    """
    if filepath.exists() and not overwrite:
        raise DataOverwriteError(
            f"File '{filepath}' already exists. "
            f"Raw experimental data must not be overwritten. "
            f"If you need to correct an error, create a new "
            f"versioned file and document the correction."
        )

    if filepath.exists() and overwrite:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath.with_suffix(
            f".backup_{timestamp}{filepath.suffix}"
        )
        shutil.copy2(filepath, backup_path)
        print(
            f"Backup created at '{backup_path}' before "
            f"overwriting '{filepath}'."
        )

    write_with_checksum(data, filepath)
    return filepath
```

### 8.2 Every dataset must carry metadata

```python
from pydantic import BaseModel
from typing import Any


class ExperimentalDataset(BaseModel):
    dataset_id: str
    version: str
    created_date: str
    operator: str
    construct_ids: list[str]
    chassis: str
    experimental_conditions: dict[str, Any]
    instrument: str
    instrument_settings: dict[str, Any]
    normalization_method: str
    blank_correction_applied: bool
    negative_controls: list[str]
    positive_controls: list[str]
    replicates: int
    raw_data_checksum: str
    approved_for_model_training: bool
    approved_by: str | None
    approval_date: str | None
    known_issues: list[str]
    notes: str
```

### 8.3 Units must be explicit and consistent

```python
from enum import Enum


class ConcentrationUnit(Enum):
    MOLAR = "M"
    MILLIMOLAR = "mM"
    MICROMOLAR = "uM"
    NANOMOLAR = "nM"
    PICOMOLAR = "pM"


class TimeUnit(Enum):
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"


class LengthUnit(Enum):
    METERS = "m"
    NANOMETERS = "nm"
    ANGSTROMS = "A"


class SignalUnit(Enum):
    RLU = "RLU"
    FMOL_LUCIFERASE = "fmol_luciferase"
    NORMALIZED_RLU = "nRLU"
    ARBITRARY_UNITS = "AU"


def convert_concentration(
    value: float,
    from_unit: ConcentrationUnit,
    to_unit: ConcentrationUnit,
) -> float:
    """
    Convert between concentration units explicitly.
    Never perform unit conversion silently.
    Always log the conversion in the calling function.

    Conversion factors relative to Molar:
    M = 1, mM = 1e-3, uM = 1e-6, nM = 1e-9, pM = 1e-12
    """
    to_molar = {
        ConcentrationUnit.MOLAR: 1.0,
        ConcentrationUnit.MILLIMOLAR: 1e-3,
        ConcentrationUnit.MICROMOLAR: 1e-6,
        ConcentrationUnit.NANOMOLAR: 1e-9,
        ConcentrationUnit.PICOMOLAR: 1e-12,
    }
    value_in_molar = value * to_molar[from_unit]
    return value_in_molar / to_molar[to_unit]


def assert_units_match(
    value_a: float,
    unit_a: str,
    value_b: float,
    unit_b: str,
    operation: str,
) -> None:
    """
    Assert that two values have compatible units before
    performing an arithmetic operation.
    Unit mismatches are one of the most common and most
    dangerous silent errors in biological software.
    """
    if unit_a != unit_b:
        raise UnitMismatchError(
            f"Cannot perform '{operation}' on values with "
            f"different units: {unit_a} and {unit_b}. "
            f"Convert to a common unit before proceeding. "
            f"Values: {value_a} {unit_a} and {value_b} {unit_b}."
        )
```

---

## 9. Verification layer templates

Every biological software project should implement layered verification before any design output is acted upon. Adapt the specific checks to your project's biology.

### 9.1 Layer 1: Sequence integrity

```python
def verify_sequence_integrity(
    sequence: str,
    sequence_id: str,
    expected_length: int | None = None,
    expected_protein: str | None = None,
) -> VerificationLayerResult:
    """
    Layer 1: Verify that a sequence is internally consistent.

    Checks:
    - Valid nucleotide alphabet
    - Length consistency
    - No internal stop codons
    - Correct reading frame
    - Translation matches expected protein
    - Sequence checksum
    """
    checks = []
    valid_bases = set("ATCGatcgNn")
    invalid = [c for c in sequence if c not in valid_bases]
    checks.append(
        Check(
            name="valid_alphabet",
            passed=len(invalid) == 0,
            message=(
                f"Invalid characters found: {set(invalid)}"
                if invalid
                else "Valid nucleotide alphabet."
            ),
        )
    )

    if expected_length:
        checks.append(
            Check(
                name="length_check",
                passed=len(sequence) == expected_length,
                message=(
                    f"Length {len(sequence)} does not match "
                    f"expected {expected_length}."
                    if len(sequence) != expected_length
                    else f"Length {len(sequence)} correct."
                ),
            )
        )

    frame_result = verify_reading_frame(
        sequence, expected_protein, sequence_id
    )
    checks.append(
        Check(
            name="reading_frame",
            passed=frame_result.valid,
            message=frame_result.error or "Reading frame valid.",
        )
    )

    site_result = check_forbidden_sites(sequence, sequence_id=sequence_id)
    checks.append(
        Check(
            name="forbidden_sites",
            passed=site_result.passed,
            message=(
                f"Forbidden sites found: {site_result.found_sites}"
                if not site_result.passed
                else "No forbidden sites detected."
            ),
        )
    )

    return VerificationLayerResult(
        layer=1,
        layer_name="sequence_integrity",
        checks=checks,
        passed=all(c.passed for c in checks),
        checksum=compute_sequence_checksum(sequence),
    )
```

### 9.2 Layer 2: Biological plausibility

```python
def verify_biological_plausibility(
    design_spec: dict,
    parameter_library: dict,
) -> VerificationLayerResult:
    """
    Layer 2: Verify that the design is biologically plausible.

    Checks:
    - All parameters have cited sources
    - Parameter values are within known biological ranges
    - No contradictory design elements
    - Chassis compatibility
    - Expression context consistency

    These are warnings, not hard failures.
    A biologically implausible design may still be worth
    testing, but the implausibility must be visible.
    """
    checks = []
    for param_name, param_value in design_spec.items():
        if param_name in parameter_library:
            param_def = parameter_library[param_name]
            in_range = param_def.is_within_range(param_value)
            checks.append(
                Check(
                    name=f"range_check_{param_name}",
                    passed=in_range,
                    severity="warning" if not in_range else "pass",
                    message=(
                        f"{param_name}={param_value} "
                        f"{param_def.units} is outside the "
                        f"validated range "
                        f"[{param_def.lower_bound}, "
                        f"{param_def.upper_bound}]. "
                        f"This is an extrapolation."
                        if not in_range
                        else f"{param_name} within validated range."
                    ),
                )
            )

    return VerificationLayerResult(
        layer=2,
        layer_name="biological_plausibility",
        checks=checks,
        passed=not any(c.severity == "error" for c in checks),
    )
```

### 9.3 Layer 3: Model consistency

```python
def verify_model_consistency(
    prediction: PredictionResult,
    design_spec: dict,
) -> VerificationLayerResult:
    """
    Layer 3: Verify that the model output is internally
    consistent and physically meaningful.

    Checks:
    - Predicted values are physically possible
    - Units are consistent throughout
    - Uncertainty interval is non-negative
    - Confidence tier matches extrapolation status
    - All required parameters were available
    - Model version is recorded
    """
    checks = []
    checks.append(
        Check(
            name="positive_prediction",
            passed=prediction.predicted_value >= 0,
            message=(
                f"Predicted value {prediction.predicted_value} "
                f"is negative. Physical quantities cannot be "
                f"negative. Check model equations."
                if prediction.predicted_value < 0
                else "Predicted value is non-negative."
            ),
        )
    )

    interval_width = (
        prediction.uncertainty_95_upper - prediction.uncertainty_95_lower
    )
    checks.append(
        Check(
            name="valid_uncertainty_interval",
            passed=interval_width >= 0,
            message=(
                f"Uncertainty interval is inverted: "
                f"[{prediction.uncertainty_95_lower}, "
                f"{prediction.uncertainty_95_upper}]. "
                f"Lower bound must be less than upper bound."
                if interval_width < 0
                else "Uncertainty interval is valid."
            ),
        )
    )

    tier_extrapolation_consistent = (
        prediction.confidence_tier in ["extrapolated", "hypothesis_only"]
    ) == prediction.is_extrapolation
    checks.append(
        Check(
            name="tier_extrapolation_consistency",
            passed=tier_extrapolation_consistent,
            message=(
                "Confidence tier and extrapolation flag are "
                "inconsistent. A prediction cannot be labelled "
                "'interpolated' while also flagged as an "
                "extrapolation."
                if not tier_extrapolation_consistent
                else "Confidence tier and extrapolation flag consistent."
            ),
        )
    )

    checks.append(
        Check(
            name="model_version_recorded",
            passed=bool(prediction.model_version),
            message=(
                "Model version is not recorded. Every prediction "
                "must be traceable to a specific model version."
                if not prediction.model_version
                else f"Model version: {prediction.model_version}."
            ),
        )
    )

    return VerificationLayerResult(
        layer=3,
        layer_name="model_consistency",
        checks=checks,
        passed=all(c.passed for c in checks),
    )
```

### 9.4 Layer 4: Safety and biosecurity

```python
def verify_safety_and_biosecurity(
    design_spec: dict,
    parts_library: dict,
    biosecurity_blocklist: set,
) -> VerificationLayerResult:
    """
    Layer 4: Verify that the design does not contain
    biosecurity-sensitive components and that all parts
    are from the validated allowlist.

    This layer must never be bypassed.
    A failed biosecurity check must halt all downstream
    processing including sequence export.
    """
    checks = []
    for part_id in design_spec.get("part_ids", []):
        in_allowlist = part_id in parts_library
        checks.append(
            Check(
                name=f"allowlist_check_{part_id}",
                passed=in_allowlist,
                severity="error" if not in_allowlist else "pass",
                message=(
                    f"Part '{part_id}' is not in the validated "
                    f"parts library. Designs containing unvalidated "
                    f"parts cannot be exported."
                    if not in_allowlist
                    else f"Part '{part_id}' is validated."
                ),
            )
        )

        on_blocklist = part_id in biosecurity_blocklist
        checks.append(
            Check(
                name=f"blocklist_check_{part_id}",
                passed=not on_blocklist,
                severity="error" if on_blocklist else "pass",
                message=(
                    f"Part '{part_id}' is on the biosecurity "
                    f"blocklist. This design cannot be processed."
                    if on_blocklist
                    else f"Part '{part_id}' not on blocklist."
                ),
            )
        )

    return VerificationLayerResult(
        layer=4,
        layer_name="safety_and_biosecurity",
        checks=checks,
        passed=not any(c.severity == "error" for c in checks),
        blocks_export=any(c.severity == "error" for c in checks),
    )
```

### 9.5 Layer 5: Reproducibility

```python
def verify_reproducibility(
    design_spec: dict,
    prediction: PredictionResult,
    dataset: ExperimentalDataset | None,
) -> VerificationLayerResult:
    """
    Layer 5: Verify that the design and prediction are
    reproducible from the recorded information alone.

    A result is reproducible if a third party could
    regenerate it from the recorded inputs, model version,
    dataset version, and parameter sources without
    contacting the original authors.

    Checks:
    - All inputs are recorded
    - Model version is pinned
    - Dataset version is pinned
    - Parameter sources are cited
    - Random seeds are recorded where applicable
    - No external dependencies that could change
    """
    checks = []
    checks.append(
        Check(
            name="model_version_pinned",
            passed=bool(prediction.model_version),
            message=(
                "Model version is not pinned. Results cannot "
                "be reproduced without knowing which model "
                "version was used."
                if not prediction.model_version
                else f"Model version pinned: {prediction.model_version}."
            ),
        )
    )
    checks.append(
        Check(
            name="parameter_sources_cited",
            passed=len(prediction.parameter_sources) > 0,
            message=(
                "No parameter sources are recorded. Results "
                "cannot be reproduced without knowing which "
                "parameter values were used and where they "
                "came from."
                if not prediction.parameter_sources
                else (
                    f"{len(prediction.parameter_sources)} "
                    f"parameter sources recorded."
                )
            ),
        )
    )

    if dataset:
        checks.append(
            Check(
                name="dataset_version_pinned",
                passed=bool(dataset.version),
                message=(
                    "Dataset version is not pinned."
                    if not dataset.version
                    else f"Dataset version: {dataset.version}."
                ),
            )
        )
        checks.append(
            Check(
                name="dataset_approved_for_use",
                passed=dataset.approved_for_model_training,
                message=(
                    "Dataset has not been approved for model "
                    "training. Only approved datasets may be "
                    "used to calibrate production models."
                    if not dataset.approved_for_model_training
                    else "Dataset approved for use."
                ),
            )
        )

    return VerificationLayerResult(
        layer=5,
        layer_name="reproducibility",
        checks=checks,
        passed=all(c.passed for c in checks),
    )
```

---

## 10. Testing standards

### 10.1 Test categories and their purposes

```text
tests/unit/
  Test individual functions in isolation.
  Every public function must have at least one unit test.
  Unit tests verify execution, not scientific correctness.

tests/scientific/
  Test physical and biological invariants.
  These are the most important tests in the project.
  Scientific tests verify that the code obeys known laws.

tests/golden/
  Test that known inputs produce known outputs exactly.
  Golden tests catch regressions in deterministic functions.
  Every sequence compilation function must have golden tests.

tests/integration/
  Test that modules work together correctly.
  Integration tests verify the interfaces between modules.

tests/adversarial/
  Test that the system handles invalid inputs correctly.
  Adversarial tests verify that safety checks work.
```

### 10.2 Golden test template for sequence functions

```python
import pytest
from pathlib import Path
import json

GOLDEN_OUTPUTS_DIR = Path("tests/golden/outputs")


def test_sequence_compilation_golden(compiler, design_spec_fixture):
    """
    Golden test: verify that sequence compilation produces
    exactly the expected output for a known input.

    If this test fails, either:
    1. The compiler has a bug (fix the compiler)
    2. The design spec has changed (update the golden file
       and document why)
    3. The parts library has changed (update the golden file
       and document why)

    Never update a golden file without understanding why
    the output changed.
    """
    result = compiler.compile(design_spec_fixture)
    golden_path = (
        GOLDEN_OUTPUTS_DIR / f"{design_spec_fixture.design_id}_golden.json"
    )

    if not golden_path.exists():
        golden_path.write_text(json.dumps(result.dict(), indent=2))
        pytest.skip(
            f"Golden file created at {golden_path}. "
            f"Run the test again to verify."
        )

    golden = json.loads(golden_path.read_text())
    assert result.sequence == golden["sequence"], (
        f"Sequence changed. "
        f"Expected checksum: {golden['checksum']}. "
        f"Got checksum: {result.checksum}. "
        f"Diff: {compute_diff(golden['sequence'], result.sequence)}. "
        f"If this change is intentional, update the golden "
        f"file and document the reason in the commit message."
    )
    assert result.checksum == golden["checksum"], (
        "Checksum mismatch. Sequence may have changed silently."
    )
```

### 10.3 Adversarial test template

```python
import pytest


@pytest.mark.parametrize(
    "invalid_input,expected_error",
    [
        (
            {"calcium_uM": -1.0},
            "Calcium concentration cannot be negative",
        ),
        (
            {"repeat_count": 0},
            "Scaffold must have at least one repeat",
        ),
        (
            {"part_id": "UNVALIDATED_PART_XYZ"},
            "not in the validated parts library",
        ),
        (
            {"sequence": "ATCG" * 1000 + "GAATTC"},
            "Forbidden site EcoRI detected",
        ),
        (
            {"chassis": "unknown_organism"},
            "Chassis not supported",
        ),
    ],
)
def test_invalid_inputs_are_rejected(
    system_under_test,
    invalid_input,
    expected_error,
):
    """
    Adversarial test: verify that invalid inputs are
    rejected with informative error messages.

    A system that accepts invalid inputs silently is
    more dangerous than one that crashes loudly.
    """
    with pytest.raises(Exception) as exc_info:
        system_under_test.process(invalid_input)
    assert expected_error.lower() in str(exc_info.value).lower(), (
        f"Expected error message containing '{expected_error}' "
        f"but got: '{exc_info.value}'"
    )
```

---

## 11. Documentation standards

### 11.1 Every module must have a README

Each module directory must contain a `README.md` with:

```markdown
# [Module Name]

## Purpose
[One paragraph describing what this module does and why.]

## Scientific basis
[The biological or physical principles this module implements.
Include citations for key equations or assumptions.]

## Inputs
[What the module accepts. Include types and units.]

## Outputs
[What the module returns. Include types and units.]

## Assumptions
[Explicit list of assumptions the module makes.
These are the conditions under which the module is valid.]

## Known limitations
[What the module cannot do or where it may fail.]

## Parameter sources
[Where the biological constants used in this module
come from. Include DOIs.]

## Tests
[How to run the tests for this module.]

## Owner
[Who is responsible for this module.]
```

### 11.2 Changelog entries for biological changes

Every change to a biological constant, model equation, sequence, or verification rule must have a changelog entry:

```markdown
## [Version] — [Date]

### Changed
- [Parameter name]: changed from [old value][units] to [new value][units].
  Reason: [why the value changed].
  Old source: [citation].
  New source: [citation].
  Impact: [what predictions or outputs this affects].
  Reviewed by: [name].
```

---

## 12. Pull request checklist

Before opening a pull request, confirm all of the following:

### Code quality

- [ ] `ruff format` passes with no changes
- [ ] `ruff check` passes with no warnings
- [ ] `mypy --strict` passes with no errors
- [ ] All new functions have docstrings
- [ ] All new modules have README files

### Tests

- [ ] `pytest tests/unit/` passes
- [ ] `pytest tests/scientific/` passes
- [ ] `pytest tests/golden/` passes
- [ ] `pytest tests/integration/` passes
- [ ] New scientific invariant tests added for new biology
- [ ] New golden tests added for new sequence functions
- [ ] New adversarial tests added for new safety checks

### Biological correctness

- [ ] All new biological constants have cited sources
- [ ] All new sequences have been translated and verified
- [ ] All new sequences have been checked for forbidden sites
- [ ] No sequences were generated by a language model
- [ ] No citations were generated by a language model
- [ ] All predictions return uncertainty intervals
- [ ] All predictions return confidence tiers

### Safety

- [ ] No verification layers were removed or weakened
- [ ] No biosecurity filters were modified without approval
- [ ] No parts were added to the allowlist without review
- [ ] No sequences were silently modified

### Reproducibility

- [ ] Model version is recorded in all prediction outputs
- [ ] Dataset version is recorded where applicable
- [ ] Parameter sources are cited in all new constants
- [ ] Random seeds are recorded where applicable

### Documentation

- [ ] `CHANGELOG.md` updated for biological changes
- [ ] `interfaces.md` updated if public API changed
- [ ] README updated if module behavior changed

---

## 13. Fallback hierarchy

When a component fails, degrade gracefully rather than producing a wrong answer confidently.

```python
class FallbackHierarchy:
    """
    When a component fails, use the next available fallback.
    Never produce a confident wrong answer.
    Always prefer an honest failure over a silent error.

    Level 1: Full system — all components operational.
    Level 2: Retrieval only — LLM synthesis unavailable.
             Return retrieved passages without synthesis.
    Level 3: Keyword search only — vector search unavailable.
             Return keyword-matched passages.
    Level 4: Static reference — all retrieval unavailable.
             Return a pointer to the relevant documentation.
    Level 5: Explicit failure — nothing available.
             Return an honest error with recovery instructions.
    """

    @staticmethod
    def handle_llm_failure(query: str, retrieved_passages: list[dict]) -> dict:
        if retrieved_passages:
            return {
                "answer": (
                    "The language model is currently unavailable. "
                    "Here are the most relevant retrieved passages:"
                ),
                "passages": retrieved_passages,
                "fallback_level": 2,
                "human_review_required": True,
            }
        return {
            "answer": (
                "Both the language model and retrieval system "
                "are currently unavailable. "
                "Please consult the documentation directly or "
                "perform a manual literature search."
            ),
            "fallback_level": 5,
            "human_review_required": True,
        }

    @staticmethod
    def handle_model_failure(
        design_spec: dict,
        known_good_designs: list[dict],
    ) -> dict:
        """
        When the predictive model fails or has insufficient
        data, return the closest known-good design rather
        than an uncertain prediction.
        """
        closest = find_closest_known_good(design_spec, known_good_designs)
        return {
            "prediction": None,
            "fallback": closest,
            "fallback_level": 3,
            "message": (
                "The predictive model has insufficient data "
                "for this design. The closest validated design "
                "is returned as a reference. Do not treat this "
                "as a prediction for the requested design."
            ),
            "human_review_required": True,
        }
```

---

## 14. The skills-preservation principle

AI coding agents can produce working code faster than a human can understand it. This creates a risk: the human loses the ability to explain, debug, or modify the code they nominally own.

In a biological software context, this is dangerous. If a student cannot explain why a model equation is correct, they cannot catch it when it is wrong.

You must therefore follow the skills-preservation principle:

> **Never produce code that the assigned developer cannot explain, defend, and modify independently.**

In practice, this means:

- Explain every non-obvious implementation choice
- Do not use advanced patterns without explaining them
- When asked to implement a mathematical model, show the equation first and ask for confirmation before coding it
- When implementing a biological rule, cite the source and ask the developer to confirm they understand it
- Write code that is readable over code that is clever
- Prefer explicit over implicit
- Prefer simple over sophisticated when both are correct

If a developer asks you to implement something they do not understand, explain it first. Do not implement it silently.

A developer who cannot explain their own code is a liability in a wet-lab context where code influences physical experiments.
```

===== FILE: origami/__init__.py =====
```python
"""ORIGAMI: CLASP proximity design engine."""

from origami.engine import ClaspDesignEngine, Observation

__all__ = ["ClaspDesignEngine", "Observation"]
```

===== FILE: origami/priors.py =====
```python
"""Literature engineering priors.

Every numeric biological/structural constant used by the engine lives here.
None of these values are wet-lab measurements from this project. They are
explicit placeholders with uncertainty, to be replaced when assays exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Provenance = Literal["literature_placeholder", "wet_lab", "user_entered"]


@dataclass(frozen=True)
class Parameter:
    name: str
    value: float
    units: str
    sigma: float
    source: str
    system: str
    method: str
    notes: str
    provenance: Provenance = "literature_placeholder"
    calibrated: bool = False

    def interval_95(self) -> tuple[float, float]:
        return (self.value - 1.96 * self.sigma, self.value + 1.96 * self.sigma)


# Superhelical CTPR geometry is taken as an engineering prior consistent with
# designed CTPR crystal structures (CTPR8/CTPR20 superhelices; PDB 2AVP, 2HYZ,
# 2FO7; Kajander et al., 2007, Acta Cryst. D 63:800–811). Exact rise/rotation
# were not re-fitted from coordinates in this repository; wide sigma reflects that.
CTPR_RISE_A = Parameter(
    name="ctpr_rise_per_repeat",
    value=9.0,
    units="Å",
    sigma=2.0,
    source="Kajander et al. (2007) Acta Cryst. D 63:800–811; PDB 2AVP/2HYZ (engineering prior, not refit)",
    system="Designed consensus TPR (CTPR) superhelix",
    method="Literature-informed rigid superhelix; not measured in this project",
    notes="Replace with a fit to project crystal/MD or lab-calibrated geometry.",
)

CTPR_ROTATION_RAD = Parameter(
    name="ctpr_rotation_per_repeat",
    value=0.42,  # ~24°, typical TPR solenoid twist; 8 repeats is protein length not pitch
    units="rad",
    sigma=0.12,
    source="Engineering prior informed by designed CTPR superhelices (Kajander et al., 2007)",
    system="CTPR solenoid",
    method="Rigid-body helical repeat; not fitted to this project's structures",
    notes="Uncertainty is intentionally large until a structure-derived twist is stored.",
)

CTPR_RADIUS_A = Parameter(
    name="ctpr_docking_radius",
    value=22.0,
    units="Å",
    sigma=5.0,
    source="Engineering prior: TPR concave/convex face offset on the order of a TPR domain radius",
    system="CTPR scaffold docking-site placement",
    method="Spherical offset from superhelical axis; not payload-specific",
    notes="Does not encode a real fusion terminus until payload structures are reviewed.",
)

CTPR_SCAFFOLD_RADIUS_A = Parameter(
    name="ctpr_scaffold_radius",
    value=12.0,
    units="Å",
    sigma=3.0,
    source="Engineering prior for a helical repeat bundle excluded volume",
    system="CTPR scaffold body",
    method="Cylinder approximation",
    notes="MVP steric model uses a cylinder, not molecular surfaces.",
)

# Globular-protein size scale, not a measured OtsA/OtsB radius.
DEFAULT_PAYLOAD_RADIUS_A = Parameter(
    name="default_payload_radius",
    value=25.0,
    units="Å",
    sigma=8.0,
    source="Order-of-magnitude hydrodynamic radius for a ~40–60 kDa globular enzyme",
    system="Unspecified globular payload",
    method="MW scaling heuristic, not scattering or structure of CLASP payloads",
    notes="Per-payload radii should replace this when structures exist.",
)

# Gaussian chain uses σ² = <R²> = N b² (mean-square end-to-end), not the
# per-axis variance Nb²/3. See linkers.py.
LINKER_SIGMA_A = Parameter(
    name="gaussian_chain_linker_sigma",
    value=18.0,
    units="Å",
    sigma=6.0,
    source="Flexible-fusion Gaussian-chain engineering prior (not a measured persistence length)",
    system="Unspecified peptide linker between fusion terminus and functional site",
    method="Gaussian-chain C_eff; worm-like chain not yet used",
    notes="σ is sqrt(<R^2>), RMS end-to-end. Not a measured persistence length.",
)

# Kd only. Association rate is not in this paper; do not invent kon.
CAM_M13_KD_M = Parameter(
    name="cam_m13_kd",
    value=0.19e-9,
    units="M",
    sigma=0.09e-9,
    source=(
        "Biochemistry 2006, 45(41):12547-12559, DOI 10.1021/bi060857u. "
        "WT CaM + WT M13, fluorescence competition, Kd = 0.19 ± 0.09 nM."
    ),
    system="Ca2+-saturated calmodulin and skeletal MLCK M13 peptide, in vitro titration",
    method="Fluorescence competition vs dansyl probe",
    notes=(
        "Peptide Kd, not a CLASP fusion and not this project's assay. "
        "kon is not reported; recruitment time course requires a user-supplied kon."
    ),
)

N_REPEATS_MIN = 3
N_REPEATS_MAX = 24


def all_priors() -> tuple[Parameter, ...]:
    return (
        CTPR_RISE_A,
        CTPR_ROTATION_RAD,
        CTPR_RADIUS_A,
        CTPR_SCAFFOLD_RADIUS_A,
        DEFAULT_PAYLOAD_RADIUS_A,
        LINKER_SIGMA_A,
        CAM_M13_KD_M,
    )
```

===== FILE: origami/engine.py =====
```python
"""Physics-informed design engine: CTPR geometry + steric GP/BO loop."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from origami.design_engine.active_learning import NextExperiment, recommend
from origami.design_engine.gp import GPPosterior, ResidualGP
from origami.physical.score import PhysicsReport, physics_report
from origami.priors import DEFAULT_PAYLOAD_RADIUS_A, N_REPEATS_MAX, N_REPEATS_MIN, all_priors


@dataclass
class Observation:
    n_repeats: int
    y: float
    source: str = "user_entered"
    units: str = "relative_output"
    notes: str = "Not a wet-lab record unless source='wet_lab'."


@dataclass
class EngineResult:
    candidates: list[int]
    reports: dict[int, PhysicsReport]
    physics_scores: np.ndarray
    p_instability: np.ndarray
    posterior: GPPosterior
    next_experiment: NextExperiment
    observations: list[Observation]
    priors: list[str] = field(default_factory=list)
    evidence_level: str = "literature_supported"


class ClaspDesignEngine:
    """Evaluate a discrete CTPR library with physics, then residual GP + BO."""

    def __init__(
        self,
        payload_radii_A: list[float] | None = None,
        n_min: int = N_REPEATS_MIN,
        n_max: int = N_REPEATS_MAX,
        acquisition: str = "ucb",
    ) -> None:
        self.payload_radii_A = payload_radii_A or [
            DEFAULT_PAYLOAD_RADIUS_A.value,
            DEFAULT_PAYLOAD_RADIUS_A.value,
        ]
        self.n_min = n_min
        self.n_max = n_max
        self.acquisition = acquisition
        self.observations: list[Observation] = []

    def add_observation(self, obs: Observation) -> None:
        if obs.n_repeats < self.n_min or obs.n_repeats > self.n_max:
            raise ValueError("observation n_repeats outside the candidate library")
        self.observations.append(obs)

    def evaluate_one(self, n_repeats: int) -> PhysicsReport:
        indices = [0, n_repeats - 1]
        if len(self.payload_radii_A) != 2:
            # place payloads evenly along the solenoid
            k = len(self.payload_radii_A)
            indices = [int(round(i * (n_repeats - 1) / (k - 1))) for i in range(k)]
        return physics_report(n_repeats, payload_indices=indices, radii_A=self.payload_radii_A)

    def run(self) -> EngineResult:
        candidates = list(range(self.n_min, self.n_max + 1))
        reports = {n: self.evaluate_one(n) for n in candidates}
        S = np.array([reports[n].physics_score for n in candidates])
        p_inst = np.array([reports[n].steric.p_any_instability for n in candidates])
        X_all = np.array(candidates, dtype=float).reshape(-1, 1)

        gp = ResidualGP()
        if self.observations:
            X = np.array([[o.n_repeats] for o in self.observations], dtype=float)
            y = np.array([o.y for o in self.observations], dtype=float)
            S_obs = np.array([reports[o.n_repeats].physics_score for o in self.observations])
            gp.fit(X, y, S_obs, optimize=len(self.observations) >= 3)
        posterior = gp.predict(X_all, S)

        observed = {o.n_repeats for o in self.observations}
        nxt = recommend(
            X_all,
            posterior,
            S,
            p_inst,
            observed=observed,
            acquisition=self.acquisition,
        )
        prior_lines = [
            f"{p.name}={p.value} {p.units} (σ={p.sigma}, {p.provenance}, calibrated={p.calibrated})"
            for p in all_priors()
        ]
        evidence = "literature_supported"
        if any(o.source == "wet_lab" for o in self.observations):
            evidence = "parts_validated" if len(self.observations) >= 3 else "computationally_evaluated"
        elif self.observations:
            evidence = "computationally_evaluated"
        return EngineResult(
            candidates=candidates,
            reports=reports,
            physics_scores=S,
            p_instability=p_inst,
            posterior=posterior,
            next_experiment=nxt,
            observations=list(self.observations),
            priors=prior_lines,
            evidence_level=evidence,
        )
```

===== FILE: origami/schemas/__init__.py =====
```python
from origami.schemas.design import DesignSpec, PayloadSpec, ScaffoldSpec

__all__ = ["DesignSpec", "PayloadSpec", "ScaffoldSpec"]
```

===== FILE: origami/schemas/design.py =====
```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

MechanismId = Literal[
    "intermediate_transfer",
    "target_induced_complementation",
    "redox_transfer",
    "covalent_capture",
]


class PayloadSpec(BaseModel):
    payload_id: str
    role: str
    fusion_terminus: Literal["N", "C"] = "C"
    repeat_index: int = Field(ge=0, description="Docking repeat index on the CTPR scaffold")
    radius_A: float = Field(gt=0, description="Spherical payload radius (Å)")
    linker_id: str = "gs_default"
    functional_site: str | None = None
    structure_id: str | None = None


class ScaffoldSpec(BaseModel):
    n_repeats: int = Field(ge=3, le=24)
    payloads: list[PayloadSpec]


class DesignSpec(BaseModel):
    design_id: str
    mechanism_profile: MechanismId = "intermediate_transfer"
    chassis: Literal["cell_free", "E_coli", "B_subtilis", "other"] = "cell_free"
    sensor_id: str = "CaM-M13"
    scaffold: ScaffoldSpec
    reporter_id: str | None = None
    localization: str = "soluble"
    operating_mode: Literal["reversible", "locking", "target_triggered"] = "reversible"

    @model_validator(mode="after")
    def payload_indices_in_range(self) -> "DesignSpec":
        n = self.scaffold.n_repeats
        for p in self.scaffold.payloads:
            if p.repeat_index >= n:
                raise ValueError(
                    f"payload {p.payload_id} docks at repeat {p.repeat_index}, "
                    f"but scaffold has only {n} repeats"
                )
        return self
```

===== FILE: origami/physical/__init__.py =====
```python
from origami.physical.geometry import CtprGeometry, DockingSite
from origami.physical.linkers import gaussian_chain_ceff
from origami.physical.recruitment import recruitment_occupancy
from origami.physical.score import physics_report
from origami.physical.steric import clash_probability, steric_report

__all__ = [
    "CtprGeometry",
    "DockingSite",
    "gaussian_chain_ceff",
    "recruitment_occupancy",
    "physics_report",
    "clash_probability",
    "steric_report",
]
```

===== FILE: origami/physical/geometry.py =====
```python
"""CTPR scaffold geometry via rigid-body (SE(3)) helical repeats.

Docking-site coordinates are generated by composing a rotation about the
superhelical axis with an axial rise. This is not a linear ruler.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from origami.priors import CTPR_RADIUS_A, CTPR_RISE_A, CTPR_ROTATION_RAD


def _rotation_z(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def se3(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def apply_se3(T: np.ndarray, points: np.ndarray) -> np.ndarray:
    pts = np.atleast_2d(points)
    h = np.concatenate([pts, np.ones((pts.shape[0], 1))], axis=1)
    out = (T @ h.T).T[:, :3]
    return out if points.ndim == 2 else out[0]


@dataclass(frozen=True)
class DockingSite:
    index: int
    xyz_A: np.ndarray
    orientation: np.ndarray  # 3x3 rotation, columns = local axes
    covariance_A2: np.ndarray  # 3x3 positional covariance from parameter sigma


@dataclass
class CtprGeometry:
    n_repeats: int
    sites: list[DockingSite]
    rise_A: float
    rotation_rad: float
    radius_A: float
    axis: np.ndarray
    coord_covariance: np.ndarray  # (3N, 3N), includes site–site correlation
    provenance: str = "literature_placeholder"

    def cross_covariance(self, i: int, j: int) -> np.ndarray:
        """Cov(site i, site j), shape (3, 3)."""
        c = self.coord_covariance
        return c[3 * i : 3 * i + 3, 3 * j : 3 * j + 3]

    @property
    def coordinates(self) -> np.ndarray:
        return np.stack([s.xyz_A for s in self.sites], axis=0)

    def site(self, index: int) -> DockingSite:
        return self.sites[index]

    def end_to_end_A(self, i: int, j: int) -> float:
        return float(np.linalg.norm(self.sites[j].xyz_A - self.sites[i].xyz_A))


def _repeat_transform(rise_A: float, rotation_rad: float) -> np.ndarray:
    R = _rotation_z(rotation_rad)
    t = np.array([0.0, 0.0, rise_A])
    return se3(R, t)


def helical_frames(
    n_repeats: int,
    rise_A: float,
    rotation_rad: float,
    radius_A: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (N,3) docking coordinates and (N,3,3) orientations."""
    T = np.eye(4)
    local = np.array([radius_A, 0.0, 0.0])
    coords = np.zeros((n_repeats, 3))
    orients = np.zeros((n_repeats, 3, 3))
    step = _repeat_transform(rise_A, rotation_rad)
    for i in range(n_repeats):
        coords[i] = apply_se3(T, local)
        orients[i] = T[:3, :3]
        T = T @ step
    return coords, orients


def _jacobian(
    n_repeats: int,
    rise_A: float,
    rotation_rad: float,
    radius_A: float,
    eps: float = 1e-4,
) -> np.ndarray:
    """∂(vec coords) / ∂(rise, rotation, radius). Shape (3N, 3)."""
    theta = np.array([rise_A, rotation_rad, radius_A], dtype=float)
    base, _ = helical_frames(n_repeats, *theta)
    y0 = base.ravel()
    J = np.zeros((y0.size, 3))
    for k in range(3):
        d = np.zeros(3)
        d[k] = eps
        plus, _ = helical_frames(n_repeats, *(theta + d))
        minus, _ = helical_frames(n_repeats, *(theta - d))
        J[:, k] = (plus.ravel() - minus.ravel()) / (2.0 * eps)
    return J


def build_ctpr(
    n_repeats: int,
    rise_A: float | None = None,
    rotation_rad: float | None = None,
    radius_A: float | None = None,
) -> CtprGeometry:
    if n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    rise = CTPR_RISE_A.value if rise_A is None else rise_A
    rot = CTPR_ROTATION_RAD.value if rotation_rad is None else rotation_rad
    rad = CTPR_RADIUS_A.value if radius_A is None else radius_A
    coords, orients = helical_frames(n_repeats, rise, rot, rad)
    J = _jacobian(n_repeats, rise, rot, rad)
    theta_cov = np.diag(
        [
            CTPR_RISE_A.sigma**2,
            CTPR_ROTATION_RAD.sigma**2,
            CTPR_RADIUS_A.sigma**2,
        ]
    )
    coord_cov = J @ theta_cov @ J.T  # 3N x 3N
    sites = []
    for i in range(n_repeats):
        cov_i = coord_cov[3 * i : 3 * i + 3, 3 * i : 3 * i + 3]
        # numerical SPD guard
        cov_i = 0.5 * (cov_i + cov_i.T) + 1e-8 * np.eye(3)
        sites.append(
            DockingSite(
                index=i,
                xyz_A=coords[i],
                orientation=orients[i],
                covariance_A2=cov_i,
            )
        )
    return CtprGeometry(
        n_repeats=n_repeats,
        sites=sites,
        rise_A=rise,
        rotation_rad=rot,
        radius_A=rad,
        axis=np.array([0.0, 0.0, 1.0]),
        coord_covariance=coord_cov,
        provenance="literature_placeholder",
    )
```

===== FILE: origami/physical/steric.py =====
```python
"""Probabilistic steric clashes for spherical payloads on an uncertain scaffold.

P(overlap) uses the delta method on ||x_i - x_j|| given Gaussian positional
covariance from the helical-parameter Jacobian. Optional Monte Carlo check.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from origami.physical.geometry import CtprGeometry, DockingSite
from origami.priors import CTPR_SCAFFOLD_RADIUS_A


def payload_center(site: DockingSite, payload_radius_A: float) -> np.ndarray:
    """Enzyme body sits *outward* of the fusion point, not on top of the solenoid."""
    xy = site.xyz_A[:2]
    nrm = float(np.linalg.norm(xy))
    if nrm < 1e-9:
        direction = np.array([1.0, 0.0, 0.0])
    else:
        direction = np.array([xy[0] / nrm, xy[1] / nrm, 0.0])
    return site.xyz_A + payload_radius_A * direction


def clash_probability(
    a: DockingSite,
    b: DockingSite,
    radius_a_A: float,
    radius_b_A: float,
    cross_covariance: np.ndarray | None = None,
) -> float:
    """P(||X_a - X_b|| < R_a + R_b) under local Gaussian uncertainty.

    If cross_covariance is Cov(X_a, X_b), distance variance uses
    Σ_a + Σ_b − Σ_ab − Σ_abᵀ. Omitting it treats the sites as independent
    and overstates distance noise when they share helical-parameter error.
    """
    ca, cb = payload_center(a, radius_a_A), payload_center(b, radius_b_A)
    delta = ca - cb
    dist = float(np.linalg.norm(delta))
    sigma = a.covariance_A2 + b.covariance_A2
    if cross_covariance is not None:
        cross = np.asarray(cross_covariance, dtype=float)
        sigma = sigma - cross - cross.T
    sigma = 0.5 * (sigma + sigma.T)
    contact = radius_a_A + radius_b_A
    if dist < 1e-9:
        return 1.0
    u = delta / dist
    var_d = float(u @ sigma @ u)
    std = np.sqrt(max(var_d, 1e-12))
    return float(norm.cdf((contact - dist) / std))


def clash_probability_mc(
    a: DockingSite,
    b: DockingSite,
    radius_a_A: float,
    radius_b_A: float,
    n_samples: int = 4000,
    rng: np.random.Generator | None = None,
) -> float:
    rng = rng or np.random.default_rng(0)
    offset_a = payload_center(a, radius_a_A) - a.xyz_A
    offset_b = payload_center(b, radius_b_A) - b.xyz_A
    xa = rng.multivariate_normal(a.xyz_A, a.covariance_A2, size=n_samples) + offset_a
    xb = rng.multivariate_normal(b.xyz_A, b.covariance_A2, size=n_samples) + offset_b
    d = np.linalg.norm(xa - xb, axis=1)
    return float(np.mean(d < (radius_a_A + radius_b_A)))


def scaffold_overlap_probability(
    site: DockingSite,
    payload_radius_A: float,
    scaffold_radius_A: float | None = None,
) -> float:
    """Payload sphere vs cylindrical scaffold (axis = z)."""
    r_scaf = CTPR_SCAFFOLD_RADIUS_A.value if scaffold_radius_A is None else scaffold_radius_A
    centre = payload_center(site, payload_radius_A)
    radial = float(np.linalg.norm(centre[:2]))
    # clash if the sphere reaches the cylinder: radial < r_scaf + payload_radius
    var_xy = float(np.trace(site.covariance_A2[:2, :2]) / 2.0)
    std = np.sqrt(max(var_xy, 1e-12))
    return float(norm.cdf((r_scaf + payload_radius_A - radial) / std))


@dataclass
class PairClash:
    i: int
    j: int
    distance_A: float
    contact_A: float
    p_clash: float


@dataclass
class StericReport:
    pairs: list[PairClash]
    p_any_payload_clash: float
    p_scaffold_clash: list[float]
    p_any_instability: float
    method: str = "delta_method_gaussian"
    provenance: str = "literature_placeholder"


def steric_report(
    geom: CtprGeometry,
    indices: list[int],
    radii_A: list[float],
) -> StericReport:
    if len(indices) != len(radii_A):
        raise ValueError("indices and radii must match")
    sites = [geom.site(i) for i in indices]
    pairs: list[PairClash] = []
    p_survive = 1.0
    for a in range(len(sites)):
        for b in range(a + 1, len(sites)):
            dist = float(
                np.linalg.norm(
                    payload_center(sites[a], radii_A[a]) - payload_center(sites[b], radii_A[b])
                )
            )
            contact = radii_A[a] + radii_A[b]
            p = clash_probability(
                sites[a],
                sites[b],
                radii_A[a],
                radii_A[b],
                cross_covariance=geom.cross_covariance(indices[a], indices[b]),
            )
            pairs.append(
                PairClash(
                    i=indices[a],
                    j=indices[b],
                    distance_A=dist,
                    contact_A=contact,
                    p_clash=p,
                )
            )
            p_survive *= 1.0 - p
    p_scaf = [
        scaffold_overlap_probability(site, radius)
        for site, radius in zip(sites, radii_A)
    ]
    for p in p_scaf:
        p_survive *= 1.0 - p
    p_any_pair = 1.0 - float(np.prod([1.0 - p.p_clash for p in pairs])) if pairs else 0.0
    return StericReport(
        pairs=pairs,
        p_any_payload_clash=p_any_pair,
        p_scaffold_clash=p_scaf,
        p_any_instability=1.0 - p_survive,
    )
```

===== FILE: origami/physical/linkers.py =====
```python
"""Gaussian-chain effective concentration.

σ² below is the mean-square end-to-end length <R²> = N b², not Nb²/3.

C_eff(r) = (3 / (2 π σ²))^(3/2) exp(-3 r² / (2 σ²))

This is polymer physics, not a Gaussian process.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from origami.priors import LINKER_SIGMA_A

_AVOGADRO = 6.02214076e23
_M_FROM_PER_A3 = 1e27 / _AVOGADRO


@dataclass(frozen=True)
class EffectiveConcentration:
    r_A: float
    sigma_A: float
    C_eff_per_A3: float
    C_eff_M: float
    provenance: str = "literature_placeholder"


def gaussian_chain_ceff(
    r_A: float,
    sigma_A: float | None = None,
) -> EffectiveConcentration:
    sig = LINKER_SIGMA_A.value if sigma_A is None else sigma_A
    if sig <= 0:
        raise ValueError("linker sigma must be positive")
    pre = (3.0 / (2.0 * np.pi * sig**2)) ** 1.5
    ceff_per_A3 = float(pre * np.exp(-3.0 * r_A**2 / (2.0 * sig**2)))
    return EffectiveConcentration(
        r_A=float(r_A),
        sigma_A=float(sig),
        C_eff_per_A3=ceff_per_A3,
        C_eff_M=ceff_per_A3 * _M_FROM_PER_A3,
    )


def gaussian_chain_ceff_M(r_A: float, sigma_A: float | None = None) -> float:
    return gaussian_chain_ceff(r_A, sigma_A).C_eff_M
```

===== FILE: origami/physical/score.py =====
```python
"""Physics ranking score: local concentration penalized by steric instability.

score = (1 - P_instability) * log10(1 + C_eff / C_ref)

This is still a mechanistic scalar, not a GP. The residual GP sits on top.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from origami.physical.geometry import CtprGeometry, build_ctpr
from origami.physical.linkers import EffectiveConcentration, gaussian_chain_ceff
from origami.physical.steric import StericReport, payload_center, steric_report
from origami.priors import DEFAULT_PAYLOAD_RADIUS_A, N_REPEATS_MAX, N_REPEATS_MIN


_C_REF_M = 1e-3  # 1 mM reference for a dimensionless log term, not a measured Km


@dataclass
class PhysicsReport:
    n_repeats: int
    payload_indices: list[int]
    geometry: CtprGeometry
    steric: StericReport
    pair_distances_A: dict[tuple[int, int], float]
    ceff: dict[tuple[int, int], EffectiveConcentration]
    physics_score: float
    feasible: bool
    warnings: list[str] = field(default_factory=list)
    evidence_level: str = "literature_supported"
    calibrated: bool = False


def physics_report(
    n_repeats: int,
    payload_indices: list[int] | None = None,
    radii_A: list[float] | None = None,
    clash_refuse: float = 0.85,
) -> PhysicsReport:
    if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
        raise ValueError(f"n_repeats must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]")
    if payload_indices is None:
        payload_indices = [0, n_repeats - 1]
    if radii_A is None:
        radii_A = [DEFAULT_PAYLOAD_RADIUS_A.value] * len(payload_indices)
    geom = build_ctpr(n_repeats)
    steric = steric_report(geom, payload_indices, radii_A)
    distances: dict[tuple[int, int], float] = {}
    ceffs: dict[tuple[int, int], EffectiveConcentration] = {}
    warnings: list[str] = []
    ceff_terms: list[float] = []
    for a in range(len(payload_indices)):
        for b in range(a + 1, len(payload_indices)):
            i, j = payload_indices[a], payload_indices[b]
            r = float(
                np.linalg.norm(
                    payload_center(geom.site(i), radii_A[a])
                    - payload_center(geom.site(j), radii_A[b])
                )
            )
            distances[(i, j)] = r
            ce = gaussian_chain_ceff(r)
            ceffs[(i, j)] = ce
            ceff_terms.append(ce.C_eff_M)
    mean_ceff = float(sum(ceff_terms) / max(len(ceff_terms), 1)) if ceff_terms else 0.0
    survive = 1.0 - steric.p_any_instability
    score = survive * float(math.log10(1.0 + mean_ceff / _C_REF_M))
    if n_repeats < 3:
        warnings.append("n_repeats below typical designed CTPR repertoire (Kajander et al., 2007).")
    if steric.p_any_payload_clash > 0.5:
        warnings.append(
            "High payload–payload clash probability: clustered enzymes may occlude functional sites."
        )
    if steric.p_any_instability > clash_refuse:
        warnings.append("Design refused as sterically implausible under current literature priors.")
        feasible = False
    else:
        feasible = True
    warnings.append(
        "All structural/kinetic numbers are literature placeholders, not this project's lab data."
    )
    return PhysicsReport(
        n_repeats=n_repeats,
        payload_indices=list(payload_indices),
        geometry=geom,
        steric=steric,
        pair_distances_A=distances,
        ceff=ceffs,
        physics_score=score,
        feasible=feasible,
        warnings=warnings,
    )
```

===== FILE: origami/physical/recruitment.py =====
```python
"""Signal-gated recruitment occupancy.

Mass-action for one class of sites:

    dθ/dt = k_on * C_free * (1 − θ) − k_off * θ
    k_off = k_on * K_d
    θ_ss = C_free / (C_free + K_d)

K_d default is the published CaM–M13 peptide value. k_on is not in that
paper and is never invented: without k_on the result is steady state only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp

from origami.priors import CAM_M13_KD_M


@dataclass
class OccupancyResult:
    theta_ss: float
    theta_95_lower: float
    theta_95_upper: float
    kd_M: float
    kd_sigma_M: float
    c_free_M: float
    kon_per_M_s: float | None
    time_s: np.ndarray | None
    theta_t: np.ndarray | None
    units: str = "site_occupancy_fraction"
    confidence_tier: str = "literature_supported"
    calibrated: bool = False
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def steady_occupancy(c_free_M: float, kd_M: float) -> float:
    if c_free_M < 0 or kd_M <= 0:
        raise ValueError("C_free must be >= 0 and Kd must be > 0")
    return float(c_free_M / (c_free_M + kd_M))


def _rhs(_t: float, theta: np.ndarray, kon: float, c_free: float, koff: float) -> np.ndarray:
    th = float(theta[0])
    return np.array([kon * c_free * (1.0 - th) - koff * th])


def recruitment_occupancy(
    c_free_M: float,
    kon_per_M_s: float | None = None,
    kd_M: float | None = None,
    kd_sigma_M: float | None = None,
    t_end_s: float | None = None,
    signal_on: bool = True,
) -> OccupancyResult:
    kd = CAM_M13_KD_M.value if kd_M is None else kd_M
    sig = CAM_M13_KD_M.sigma if kd_sigma_M is None else kd_sigma_M
    if not signal_on:
        return OccupancyResult(
            theta_ss=0.0,
            theta_95_lower=0.0,
            theta_95_upper=0.0,
            kd_M=kd,
            kd_sigma_M=sig,
            c_free_M=c_free_M,
            kon_per_M_s=kon_per_M_s,
            time_s=None,
            theta_t=None,
            assumptions=["signal_on=False forces k_on_eff = 0 (binary gate, not a 4-site Ca2+ model)."],
            warnings=["No time course: association is off."],
        )
    theta = steady_occupancy(c_free_M, kd)
    kd_lo = max(kd - 1.96 * sig, kd * 1e-6)
    kd_hi = kd + 1.96 * sig
    # Higher Kd → lower occupancy. Bounds are the Kd interval, not a full posterior.
    theta_hi = steady_occupancy(c_free_M, kd_lo)
    theta_lo = steady_occupancy(c_free_M, kd_hi)
    assumptions = [
        "Langmuir single-site mass action.",
        "Free concentration is not depleted by binding.",
        "Kd interval is the published peptide Kd ± 1.96σ, not a CLASP fusion measurement.",
    ]
    warnings = [
        "Not this project's wet-lab calibration.",
    ]
    time_s = None
    theta_t = None
    if kon_per_M_s is not None:
        if kon_per_M_s <= 0:
            raise ValueError("kon must be > 0 when provided")
        koff = kon_per_M_s * kd
        if t_end_s is None:
            rate = kon_per_M_s * c_free_M + koff
            t_end_s = 20.0 / max(rate, 1e-12)
        sol = solve_ivp(
            _rhs,
            (0.0, float(t_end_s)),
            np.array([0.0]),
            args=(kon_per_M_s, c_free_M, koff),
            dense_output=False,
            rtol=1e-6,
            atol=1e-9,
        )
        if not sol.success:
            raise RuntimeError(f"recruitment ODE failed: {sol.message}")
        time_s = sol.t
        theta_t = sol.y[0]
        assumptions.append("k_off = k_on * Kd. k_on is user-supplied, not from the Kd paper.")
    else:
        warnings.append("No kon supplied, so only steady-state occupancy is returned.")
    return OccupancyResult(
        theta_ss=theta,
        theta_95_lower=theta_lo,
        theta_95_upper=theta_hi,
        kd_M=kd,
        kd_sigma_M=sig,
        c_free_M=c_free_M,
        kon_per_M_s=kon_per_M_s,
        time_s=time_s,
        theta_t=theta_t,
        assumptions=assumptions,
        warnings=warnings,
    )
```

===== FILE: origami/design_engine/__init__.py =====
```python
from origami.design_engine.active_learning import NextExperiment, recommend
from origami.design_engine.gp import GPPosterior, ResidualGP

__all__ = ["NextExperiment", "recommend", "GPPosterior", "ResidualGP"]
```

===== FILE: origami/design_engine/kernels.py =====
```python
"""Stationary kernels. Matrices, not elementwise linear maps."""

from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist


def matern52(X: np.ndarray, Y: np.ndarray, lengthscale: float, variance: float) -> np.ndarray:
    X = np.atleast_2d(np.asarray(X, dtype=float))
    Y = np.atleast_2d(np.asarray(Y, dtype=float))
    if lengthscale <= 0 or variance <= 0:
        raise ValueError("kernel hyperparameters must be positive")
    r = cdist(X / lengthscale, Y / lengthscale, metric="euclidean")
    s = np.sqrt(5.0) * r
    return variance * (1.0 + s + (s**2) / 3.0) * np.exp(-s)
```

===== FILE: origami/design_engine/gp.py =====
```python
"""Residual Gaussian process with Cholesky inference.

    y(x) = α S_physics(x) + β + r(x) + ε
    r ~ GP(0, k_θ)

This is not linear regression: posterior variance is state-dependent and the
kernel is Matérn-5/2. Hyperparameters are optionally fit by maximizing the
log marginal likelihood.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

from origami.design_engine.kernels import matern52


_JITTER = 1e-9


@dataclass
class GPHyperparameters:
    lengthscale: float = 2.5
    variance: float = 1.0
    noise: float = 0.05


@dataclass
class GPPosterior:
    X: np.ndarray
    mean: np.ndarray
    variance: np.ndarray
    physics_mean: np.ndarray
    residual_mean: np.ndarray
    alpha: float
    beta: float
    interpolated: np.ndarray
    hyperparameters: GPHyperparameters

    @property
    def std(self) -> np.ndarray:
        return np.sqrt(np.maximum(self.variance, 0.0))

    def interval_95(self) -> tuple[np.ndarray, np.ndarray]:
        half = 1.96 * self.std
        return self.mean - half, self.mean + half


class ResidualGP:
    def __init__(self, hypers: GPHyperparameters | None = None) -> None:
        self.hypers = hypers or GPHyperparameters()
        self.X_train: np.ndarray | None = None
        self.r_train: np.ndarray | None = None
        self.alpha = 1.0
        self.beta = 0.0
        self._factor = None
        self.fitted = False

    def _kernel(self, A: np.ndarray, B: np.ndarray, hypers: GPHyperparameters) -> np.ndarray:
        return matern52(A, B, hypers.lengthscale, hypers.variance)

    def _affine(self, S: np.ndarray, y: np.ndarray) -> tuple[float, float]:
        S = np.asarray(S, dtype=float).ravel()
        y = np.asarray(y, dtype=float).ravel()
        if S.size == 0:
            return 1.0, 0.0
        if S.size == 1:
            return 1.0, float(y[0] - S[0])
        A = np.column_stack([S, np.ones_like(S)])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        return float(coef[0]), float(coef[1])

    def _nll(self, params: np.ndarray, X: np.ndarray, r: np.ndarray) -> float:
        ls, var, noise = np.exp(params)
        hypers = GPHyperparameters(lengthscale=ls, variance=var, noise=noise)
        K = self._kernel(X, X, hypers) + (noise**2 + _JITTER) * np.eye(len(X))
        try:
            factor = cho_factor(K, lower=True, check_finite=False)
        except np.linalg.LinAlgError:
            return 1e12
        alpha = cho_solve(factor, r, check_finite=False)
        logdet = 2.0 * np.sum(np.log(np.diag(factor[0])))
        n = len(r)
        return 0.5 * float(r @ alpha + logdet + n * np.log(2.0 * np.pi))

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        S_physics: np.ndarray,
        optimize: bool = True,
    ) -> "ResidualGP":
        X = np.atleast_2d(np.asarray(X, dtype=float))
        y = np.asarray(y, dtype=float).ravel()
        S = np.asarray(S_physics, dtype=float).ravel()
        if X.shape[0] != y.size or y.size != S.size:
            raise ValueError("X, y, and physics mean must align")
        self.alpha, self.beta = self._affine(S, y)
        r = y - (self.alpha * S + self.beta)
        hypers = self.hypers
        if optimize and X.shape[0] >= 3:
            x0 = np.log(
                [
                    max(self.hypers.lengthscale, 1e-3),
                    max(self.hypers.variance, 1e-3),
                    max(self.hypers.noise, 1e-4),
                ]
            )
            bounds = [(np.log(0.3), np.log(20.0)), (np.log(1e-3), np.log(50.0)), (np.log(1e-4), np.log(2.0))]
            result = minimize(self._nll, x0, args=(X, r), method="L-BFGS-B", bounds=bounds)
            if result.success:
                ls, var, noise = np.exp(result.x)
                hypers = GPHyperparameters(lengthscale=float(ls), variance=float(var), noise=float(noise))
        K = self._kernel(X, X, hypers) + (hypers.noise**2 + _JITTER) * np.eye(len(X))
        self._factor = cho_factor(K, lower=True, check_finite=False)
        self.X_train = X
        self.r_train = r
        self.hypers = hypers
        self.fitted = True
        return self

    def predict(self, X_star: np.ndarray, S_physics_star: np.ndarray) -> GPPosterior:
        X_star = np.atleast_2d(np.asarray(X_star, dtype=float))
        S_star = np.asarray(S_physics_star, dtype=float).ravel()
        physics_mean = self.alpha * S_star + self.beta
        if not self.fitted or self.X_train is None or self.X_train.shape[0] == 0:
            var = np.full(X_star.shape[0], self.hypers.variance + self.hypers.noise**2)
            return GPPosterior(
                X=X_star,
                mean=physics_mean,
                variance=var,
                physics_mean=physics_mean,
                residual_mean=np.zeros_like(physics_mean),
                alpha=self.alpha,
                beta=self.beta,
                interpolated=np.zeros(X_star.shape[0], dtype=bool),
                hyperparameters=self.hypers,
            )
        K_ss = self._kernel(X_star, X_star, self.hypers)
        K_s = self._kernel(self.X_train, X_star, self.hypers)
        residual_mean = cho_solve(self._factor, K_s, check_finite=False).T @ self.r_train
        v = cho_solve(self._factor, K_s, check_finite=False)
        var = np.diag(K_ss) - np.sum(K_s * v, axis=0) + self.hypers.noise**2
        var = np.maximum(var, 1e-12)
        mean = physics_mean + residual_mean
        # interpolated if nearest training input is within one lengthscale
        dmin = np.min(
            np.linalg.norm(X_star[:, None, :] - self.X_train[None, :, :], axis=2),
            axis=1,
        )
        interpolated = dmin <= self.hypers.lengthscale
        return GPPosterior(
            X=X_star,
            mean=mean,
            variance=var,
            physics_mean=physics_mean,
            residual_mean=residual_mean,
            alpha=self.alpha,
            beta=self.beta,
            interpolated=interpolated,
            hyperparameters=self.hypers,
        )
```

===== FILE: origami/design_engine/active_learning.py =====
```python
"""Discrete Bayesian optimization / active learning.

Candidates are a finite parts list (CTPR repeat counts). Acquisition is
computed from the GP posterior — not a grid of linear scores.

Default acquisition: constrained UCB, which both exploits the posterior
mean and explores high-variance (information-rich) designs. Sterically
refused candidates are masked.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from origami.design_engine.gp import GPPosterior


@dataclass
class NextExperiment:
    n_repeats: int
    acquisition: float
    posterior_mean: float
    posterior_std: float
    physics_score: float
    p_instability: float
    interpolated: bool
    reason: str
    acquisition_name: str


def expected_improvement(mean: np.ndarray, std: np.ndarray, best: float) -> np.ndarray:
    """EI for maximization. Uses the Gaussian tail (calculus on the posterior)."""
    from scipy.stats import norm

    std = np.maximum(std, 1e-12)
    z = (mean - best) / std
    return (mean - best) * norm.cdf(z) + std * norm.pdf(z)


def entropy(std: np.ndarray) -> np.ndarray:
    """Differential entropy of a univariate Gaussian posterior, ½ log(2πe σ²)."""
    return 0.5 * np.log(2.0 * np.pi * np.e * np.maximum(std, 1e-12) ** 2)


def recommend(
    candidates: np.ndarray,
    posterior: GPPosterior,
    physics_scores: np.ndarray,
    p_instability: np.ndarray,
    observed: set[int] | None = None,
    kappa: float = 1.8,
    clash_limit: float = 0.85,
    acquisition: str = "ucb",
) -> NextExperiment:
    observed = observed or set()
    n = candidates.astype(int).ravel()
    mean = posterior.mean
    std = posterior.std
    if acquisition == "ucb":
        acq = mean + kappa * std
        name = f"UCB(κ={kappa})"
    elif acquisition == "entropy":
        acq = entropy(std)
        name = "posterior entropy (information gain proxy)"
    elif acquisition == "ei":
        mask_obs = np.array([int(v) in observed for v in n])
        best = float(np.max(mean[mask_obs])) if np.any(mask_obs) else float(np.max(mean))
        acq = expected_improvement(mean, std, best)
        name = "expected improvement"
    else:
        raise ValueError(f"unknown acquisition {acquisition}")

    unused = np.array([int(v) not in observed for v in n])
    legal = (p_instability < clash_limit) & unused
    if not np.any(legal):
        if np.any(unused):
            legal = unused
            acq = -p_instability + 0.05 * std
            name = name + " (all unused designs exceed steric threshold; ranking least-unstable unused)"
        else:
            legal = np.ones(len(n), dtype=bool)
            name = name + " (library exhausted; allowing remeasure)"
    masked = np.where(legal, acq, -np.inf)
    idx = int(np.argmax(masked))
    return NextExperiment(
        n_repeats=int(n[idx]),
        acquisition=float(acq[idx]),
        posterior_mean=float(mean[idx]),
        posterior_std=float(std[idx]),
        physics_score=float(physics_scores[idx]),
        p_instability=float(p_instability[idx]),
        interpolated=bool(posterior.interpolated[idx]),
        reason=(
            f"{name} over discrete CTPR lengths. "
            "This is the next assay to run, not a claim that the design is validated."
        ),
        acquisition_name=name,
    )
```

===== FILE: origami/mechanisms/__init__.py =====
```python
from origami.mechanisms.base import MechanismProfile
from origami.mechanisms.intermediate_transfer import simulate_from_ceff, simulate_transfer

__all__ = ["MechanismProfile", "simulate_from_ceff", "simulate_transfer"]
```

===== FILE: origami/mechanisms/base.py =====
```python
from __future__ import annotations

from typing import Protocol

from origami.schemas.design import DesignSpec


class MechanismProfile(Protocol):
    profile_id: str
    version: str

    def validate_inputs(self, design: DesignSpec) -> None: ...

    def required_parameters(self, design: DesignSpec) -> list[str]: ...

    def predict(self, design: DesignSpec) -> dict: ...
```

===== FILE: origami/mechanisms/intermediate_transfer.py =====
```python
"""Damköhler-reduced intermediate transfer.

Space is not solved as a PDE. Escape and capture are competing first-order
rates inside one local volume:

    dI/dt = v_prod − (k_escape + k_capture) I
    dP/dt = k_capture I

    Da = k_capture / k_escape
    P(capture before escape) = Da / (1 + Da)
    J_product = v_prod * Da / (1 + Da)

Unsaturated downstream enzyme:

    k_capture = (k_cat / K_m) * C_eff

v_prod, k_escape, and k_cat/K_m are required inputs. This module does not
supply enzyme constants.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp


@dataclass
class TransferResult:
    da: float
    p_capture: float
    intermediate_ss_M: float
    product_flux_M_per_s: float
    k_capture_per_s: float
    k_escape_per_s: float
    v_prod_M_per_s: float
    c_eff_M: float | None
    time_s: np.ndarray
    intermediate_M: np.ndarray
    product_M: np.ndarray
    units_flux: str = "M/s"
    confidence_tier: str = "hypothesis_only"
    calibrated: bool = False
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def damkohler(k_capture_per_s: float, k_escape_per_s: float) -> float:
    if k_capture_per_s < 0 or k_escape_per_s <= 0:
        raise ValueError("k_capture must be >= 0 and k_escape must be > 0")
    return float(k_capture_per_s / k_escape_per_s)


def capture_probability(da: float) -> float:
    if da < 0:
        raise ValueError("Damköhler number cannot be negative")
    return float(da / (1.0 + da))


def k_capture_from_specificity(kcat_over_km_per_M_s: float, c_eff_M: float) -> float:
    """First-order capture rate in the unsaturated limit."""
    if kcat_over_km_per_M_s < 0 or c_eff_M < 0:
        raise ValueError("kcat/Km and C_eff must be >= 0")
    return float(kcat_over_km_per_M_s * c_eff_M)


def _rhs(_t: float, y: np.ndarray, v_prod: float, k_esc: float, k_cap: float) -> np.ndarray:
    intermediate = y[0]
    return np.array(
        [
            v_prod - (k_esc + k_cap) * intermediate,
            k_cap * intermediate,
        ]
    )


def simulate_transfer(
    v_prod_M_per_s: float,
    k_escape_per_s: float,
    k_capture_per_s: float,
    c_eff_M: float | None = None,
    t_end_s: float | None = None,
    n_eval: int = 80,
) -> TransferResult:
    if v_prod_M_per_s < 0:
        raise ValueError("v_prod cannot be negative")
    da = damkohler(k_capture_per_s, k_escape_per_s)
    p_cap = capture_probability(da)
    k_tot = k_escape_per_s + k_capture_per_s
    i_ss = float(v_prod_M_per_s / k_tot) if k_tot > 0 else 0.0
    flux = float(v_prod_M_per_s * p_cap)
    if t_end_s is None:
        t_end_s = 20.0 / max(k_tot, 1e-12)
    t_eval = np.linspace(0.0, float(t_end_s), n_eval)
    sol = solve_ivp(
        _rhs,
        (0.0, float(t_end_s)),
        np.array([0.0, 0.0]),
        t_eval=t_eval,
        args=(v_prod_M_per_s, k_escape_per_s, k_capture_per_s),
        rtol=1e-6,
        atol=1e-12,
    )
    if not sol.success:
        raise RuntimeError(f"transfer ODE failed: {sol.message}")
    warnings = [
        "Rates are caller-supplied. This is not a calibrated trehalose or CLASP measurement.",
        "Reduced model: no spatial PDE. Diffusion enters only as k_escape.",
    ]
    assumptions = [
        "Well-mixed local volume.",
        "First-order capture (downstream enzyme unsaturated).",
        "Constant production rate v_prod.",
        "P(capture) = Da/(1+Da) with Da = k_capture/k_escape.",
    ]
    return TransferResult(
        da=da,
        p_capture=p_cap,
        intermediate_ss_M=i_ss,
        product_flux_M_per_s=flux,
        k_capture_per_s=k_capture_per_s,
        k_escape_per_s=k_escape_per_s,
        v_prod_M_per_s=v_prod_M_per_s,
        c_eff_M=c_eff_M,
        time_s=sol.t,
        intermediate_M=sol.y[0],
        product_M=sol.y[1],
        assumptions=assumptions,
        warnings=warnings,
    )


def simulate_from_ceff(
    v_prod_M_per_s: float,
    k_escape_per_s: float,
    kcat_over_km_per_M_s: float,
    c_eff_M: float,
    t_end_s: float | None = None,
) -> TransferResult:
    k_cap = k_capture_from_specificity(kcat_over_km_per_M_s, c_eff_M)
    result = simulate_transfer(
        v_prod_M_per_s,
        k_escape_per_s,
        k_cap,
        c_eff_M=c_eff_M,
        t_end_s=t_end_s,
    )
    result.assumptions.append("k_capture = (k_cat/K_m) * C_eff, unsaturated limit.")
    return result
```

===== FILE: app.py =====
```python
"""ORIGAMI / CLASP design engine — geometry, steric probability, residual GP, BO."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from origami.engine import ClaspDesignEngine, Observation
from origami.mechanisms.intermediate_transfer import simulate_from_ceff
from origami.physical.recruitment import recruitment_occupancy
from origami.physical.steric import payload_center
from origami.priors import CAM_M13_KD_M, all_priors

st.set_page_config(page_title="ORIGAMI CLASP engine", layout="wide")
st.title("ORIGAMI — CLASP proximity design engine")
st.warning(
    "Structural numbers are **literature placeholders**, not this project's wet-lab data. "
    "The Gaussian process only updates from observations you enter. "
    "Those entries are **user-entered** until real assays are imported."
)

if "observations" not in st.session_state:
    st.session_state.observations = []

with st.sidebar:
    st.header("Scaffold library")
    n_min, n_max = st.slider("CTPR repeat range", 3, 24, (4, 18))
    r1 = st.number_input("Payload A radius (Å)", 5.0, 40.0, 22.0, 1.0)
    r2 = st.number_input("Payload B radius (Å)", 5.0, 40.0, 22.0, 1.0)
    n_inspect = st.slider("Inspect this n", n_min, n_max, min(8, n_max))
    acq = st.selectbox("Acquisition", ["ucb", "entropy", "ei"], format_func=lambda x: {
        "ucb": "UCB (exploit + explore)",
        "entropy": "Posterior entropy (information)",
        "ei": "Expected improvement",
    }[x])
    st.header("Add an observation")
    obs_n = st.number_input("Measured n_repeats", n_min, n_max, n_min)
    obs_y = st.number_input("Observed relative output y", 0.0, 10.0, 0.5, 0.05)
    if st.button("Record user-entered observation"):
        st.session_state.observations.append(
            Observation(n_repeats=int(obs_n), y=float(obs_y), source="user_entered")
        )
    if st.button("Clear observations"):
        st.session_state.observations = []

eng = ClaspDesignEngine(payload_radii_A=[float(r1), float(r2)], n_min=int(n_min), n_max=int(n_max), acquisition=acq)
for obs in st.session_state.observations:
    eng.add_observation(obs)
result = eng.run()
rep = result.reports[n_inspect]
nxt = result.next_experiment

c1, c2, c3, c4 = st.columns(4)
c1.metric("Inspect n", n_inspect)
c2.metric("P(any steric instability)", f"{rep.steric.p_any_instability:.3f}")
c3.metric("Physics score", f"{rep.physics_score:.3f}")
c4.metric("Next assay n", nxt.n_repeats)

st.caption(
    f"Evidence level: **{result.evidence_level}**. "
    f"Next experiment via **{nxt.acquisition_name}**. {nxt.reason}"
)

tab_geo, tab_ai, tab_kin, tab_priors = st.tabs(
    ["Geometry & steric", "GP + active learning", "ODE + Damköhler", "Priors"]
)

with tab_geo:
    coords = rep.geometry.coordinates
    fig = go.Figure()
    fig.add_trace(
        go.Scatter3d(
            x=coords[:, 0],
            y=coords[:, 1],
            z=coords[:, 2],
            mode="lines+markers",
            name="CTPR docking sites",
            marker=dict(size=4),
        )
    )
    payload_xyz = np.stack(
        [
            payload_center(rep.geometry.site(i), r)
            for i, r in zip(rep.payload_indices, [float(r1), float(r2)])
        ],
        axis=0,
    )
    fig.add_trace(
        go.Scatter3d(
            x=payload_xyz[:, 0],
            y=payload_xyz[:, 1],
            z=payload_xyz[:, 2],
            mode="markers",
            name="payload centres",
            marker=dict(size=12, color="crimson"),
        )
    )
    fig.update_layout(
        height=480,
        scene=dict(xaxis_title="x (Å)", yaxis_title="y (Å)", zaxis_title="z (Å)", aspectmode="data"),
        margin=dict(l=0, r=0, t=30, b=0),
        title=f"SE(3) superhelix, n={n_inspect} (not a linear ruler)",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Pairwise clashes")
    if rep.steric.pairs:
        st.dataframe(
            {
                "i": [p.i for p in rep.steric.pairs],
                "j": [p.j for p in rep.steric.pairs],
                "distance_Å": [round(p.distance_A, 2) for p in rep.steric.pairs],
                "contact_Å": [round(p.contact_A, 2) for p in rep.steric.pairs],
                "P(clash)": [round(p.p_clash, 4) for p in rep.steric.pairs],
            },
            use_container_width=True,
        )
    st.write("C_eff (Gaussian chain, molar):")
    st.json(
        {
            f"{i}-{j}": {"r_A": round(ce.r_A, 2), "C_eff_M": ce.C_eff_M, "sigma_A": ce.sigma_A}
            for (i, j), ce in rep.ceff.items()
        }
    )
    for w in rep.warnings:
        st.info(w)

with tab_ai:
    n = np.array(result.candidates)
    lo, hi = result.posterior.interval_95()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=n, y=result.physics_scores, name="physics score S(n)", mode="lines+markers"))
    fig2.add_trace(go.Scatter(x=n, y=result.posterior.mean, name="GP posterior mean", mode="lines"))
    fig2.add_trace(
        go.Scatter(
            x=list(n) + list(n[::-1]),
            y=list(hi) + list(lo[::-1]),
            fill="toself",
            name="95% interval",
            line=dict(width=0),
            opacity=0.25,
        )
    )
    if result.observations:
        fig2.add_trace(
            go.Scatter(
                x=[o.n_repeats for o in result.observations],
                y=[o.y for o in result.observations],
                mode="markers",
                name="observations",
                marker=dict(size=12, color="black", symbol="x"),
            )
        )
    fig2.add_vline(x=nxt.n_repeats, line_dash="dash", annotation_text="next assay")
    fig2.update_layout(
        height=460,
        xaxis_title="CTPR repeats n",
        yaxis_title="relative output / score",
        title="Residual GP (Matérn-5/2, Cholesky) + discrete BO",
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.write(
        f"Affine physics map: y ≈ {result.posterior.alpha:.3f}·S + {result.posterior.beta:.3f} + r(n). "
        f"Kernel lengthscale={result.posterior.hyperparameters.lengthscale:.3f}, "
        f"variance={result.posterior.hyperparameters.variance:.3f}, "
        f"noise={result.posterior.hyperparameters.noise:.3f}."
    )
    if not result.observations:
        st.info("No observations yet: the GP posterior equals the physics mean plus a prior uncertainty band. Add points to start active learning.")

with tab_kin:
    st.caption(
        "Recruitment uses the published CaM–M13 peptide Kd only. "
        "Capture rates are whatever you type. Nothing here is this team's wet lab."
    )
    c_free_nM = st.number_input("Free payload (nM)", 0.0, 1e6, 10.0, 1.0)
    kon = st.number_input("k_on (M⁻¹ s⁻¹), 0 = steady state only", 0.0, 1e9, 0.0, 1e5, format="%.1f")
    k_escape = st.number_input("k_escape (s⁻¹)", 1e-4, 1e4, 1.0, format="%.4f")
    spec = st.number_input("k_cat/K_m (M⁻¹ s⁻¹)", 0.0, 1e9, 1e5, format="%.1f")
    v_prod = st.number_input("v_prod (M/s)", 0.0, 1.0, 1e-6, format="%.2e")
    occ = recruitment_occupancy(
        c_free_M=c_free_nM * 1e-9,
        kon_per_M_s=None if kon == 0 else float(kon),
    )
    pair = next(iter(rep.ceff.values())) if rep.ceff else None
    st.metric(
        "Steady occupancy θ",
        f"{occ.theta_ss:.3f}",
        help=f"95% Kd interval [{occ.theta_95_lower:.3f}, {occ.theta_95_upper:.3f}]",
    )
    st.write(
        f"Kd = {CAM_M13_KD_M.value*1e9:.2f} ± {CAM_M13_KD_M.sigma*1e9:.2f} nM "
        f"(DOI 10.1021/bi060857u). Tier: {occ.confidence_tier}."
    )
    if pair is not None:
        xfer = simulate_from_ceff(float(v_prod), float(k_escape), float(spec), pair.C_eff_M)
        st.write(
            f"C_eff = {pair.C_eff_M:.3e} M. Da = {xfer.da:.3e}. "
            f"P(capture) = {xfer.p_capture:.3f}. "
            f"Product flux = {xfer.product_flux_M_per_s:.3e} M/s. "
            f"Tier: {xfer.confidence_tier}."
        )
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=xfer.time_s, y=xfer.intermediate_M, name="intermediate I(t)"))
        fig3.add_trace(go.Scatter(x=xfer.time_s, y=xfer.product_M, name="product P(t)"))
        fig3.update_layout(height=360, xaxis_title="t (s)", yaxis_title="M", title="Damköhler-reduced ODE")
        st.plotly_chart(fig3, use_container_width=True)
        for w in xfer.warnings:
            st.info(w)
    for w in occ.warnings:
        st.info(w)

with tab_priors:
    st.markdown("Every constant is tagged. **calibrated=False** until lab data replace it.")
    st.table(
        {
            "name": [p.name for p in all_priors()],
            "value": [p.value for p in all_priors()],
            "units": [p.units for p in all_priors()],
            "sigma": [p.sigma for p in all_priors()],
            "provenance": [p.provenance for p in all_priors()],
            "source": [p.source for p in all_priors()],
        }
    )
```

===== FILE: tests/test_geometry.py =====
```python
import numpy as np
import pytest

from origami.physical.geometry import build_ctpr


def test_repeat_count_matches_sites():
    geom = build_ctpr(8)
    assert len(geom.sites) == 8
    assert geom.coordinates.shape == (8, 3)


def test_superhelix_is_not_a_straight_ruler():
    geom = build_ctpr(12)
    xy = geom.coordinates[:, :2]
    radii = np.linalg.norm(xy, axis=1)
    assert np.allclose(radii, geom.radius_A, atol=1e-8)
    # successive xy headings should rotate, not stay collinear with origin only
    dots = []
    for i in range(1, 6):
        v0 = geom.coordinates[i][:2]
        v1 = geom.coordinates[i + 1][:2]
        a = v0 / np.linalg.norm(v0)
        b = v1 / np.linalg.norm(v1)
        dots.append(float(a @ b))
    assert all(d < 0.999 for d in dots)


def test_axial_rise_accumulates():
    geom = build_ctpr(10)
    z = geom.coordinates[:, 2]
    assert np.all(np.diff(z) > 0)
    assert z[-1] == pytest.approx((10 - 1) * geom.rise_A, rel=1e-9)


def test_positional_covariance_is_spd():
    geom = build_ctpr(6)
    for site in geom.sites:
        eig = np.linalg.eigvalsh(site.covariance_A2)
        assert np.all(eig > 0)
```

===== FILE: tests/test_steric.py =====
```python
import numpy as np

from origami.physical.geometry import build_ctpr
from origami.physical.steric import clash_probability, clash_probability_mc, steric_report


def test_adjacent_large_enzymes_clash():
    geom = build_ctpr(6)
    report = steric_report(geom, [0, 1], [25.0, 25.0])
    assert report.pairs[0].p_clash > 0.8
    assert report.p_any_payload_clash > 0.8


def test_distant_small_payloads_rarely_clash():
    geom = build_ctpr(20)
    report = steric_report(geom, [0, 19], [8.0, 8.0])
    assert report.pairs[0].p_clash < 0.05
    assert report.p_any_payload_clash < 0.05


def test_delta_method_tracks_monte_carlo():
    geom = build_ctpr(8)
    a, b = geom.site(0), geom.site(3)
    p_an = clash_probability(a, b, 18.0, 18.0)
    p_mc = clash_probability_mc(a, b, 18.0, 18.0, n_samples=8000, rng=np.random.default_rng(1))
    assert abs(p_an - p_mc) < 0.12
```

===== FILE: tests/test_physics.py =====
```python
import numpy as np

from origami.physical.linkers import gaussian_chain_ceff_M
from origami.physical.score import physics_report


def test_ceff_decreases_with_separation():
    close = gaussian_chain_ceff_M(15.0, sigma_A=18.0)
    far = gaussian_chain_ceff_M(80.0, sigma_A=18.0)
    assert close > far > 0


def test_physics_score_penalizes_clash():
    crowded = physics_report(4, payload_indices=[0, 1], radii_A=[28.0, 28.0])
    spaced = physics_report(16, payload_indices=[0, 15], radii_A=[12.0, 12.0])
    assert crowded.steric.p_any_payload_clash > spaced.steric.p_any_payload_clash
    assert crowded.warnings
    assert crowded.calibrated is False
```

===== FILE: tests/test_gp.py =====
```python
import numpy as np

from origami.design_engine.gp import GPHyperparameters, ResidualGP


def test_variance_shrinks_near_observations():
    rng = np.random.default_rng(0)
    X = np.linspace(4, 12, 7).reshape(-1, 1)
    S = 0.1 * X.ravel()
    y = S + 0.4 * np.sin(X.ravel()) + 0.01 * rng.normal(size=len(X))
    gp = ResidualGP().fit(X, y, S, optimize=True)
    post = gp.predict(np.array([[8.0], [30.0]]), np.array([0.8, 3.0]))
    assert post.std[0] < post.std[1]
    assert post.interpolated[0]
    assert not post.interpolated[1]


def test_residual_is_not_a_straight_line_through_physics():
    X = np.linspace(0.0, 6.0, 9).reshape(-1, 1)
    S = np.zeros(len(X))
    y = np.sin(X.ravel())
    gp = ResidualGP(GPHyperparameters(lengthscale=1.2, variance=1.0, noise=1e-4))
    gp.fit(X, y, S, optimize=False)
    xs = np.linspace(0.0, 6.0, 40).reshape(-1, 1)
    post = gp.predict(xs, np.zeros(len(xs)))
    err = float(np.mean(np.abs(post.mean - np.sin(xs.ravel()))))
    lin = np.polyval(np.polyfit(X.ravel(), y, 1), xs.ravel())
    lin_err = float(np.mean(np.abs(lin - np.sin(xs.ravel()))))
    assert err < 0.12
    assert err < 0.5 * lin_err


def test_empty_gp_returns_physics_mean_with_prior_variance():
    gp = ResidualGP()
    post = gp.predict(np.array([[5.0], [10.0]]), np.array([1.2, 2.4]))
    assert np.allclose(post.mean, [1.2, 2.4])
    assert np.all(post.std > 0)
```

===== FILE: tests/test_active_learning.py =====
```python
import numpy as np

from origami.design_engine.active_learning import recommend
from origami.design_engine.gp import ResidualGP
from origami.engine import ClaspDesignEngine, Observation


def test_bo_does_not_repeat_observed_when_alternatives_exist():
    X = np.arange(4, 13, dtype=float).reshape(-1, 1)
    S = np.exp(-((X.ravel() - 8) ** 2) / 10.0)
    y = S + 0.05
    gp = ResidualGP().fit(np.array([[8.0]]), np.array([y[4]]), np.array([S[4]]), optimize=False)
    post = gp.predict(X, S)
    nxt = recommend(X, post, S, p_instability=np.zeros(len(X)), observed={8}, acquisition="ucb")
    assert nxt.n_repeats != 8


def test_engine_recommends_integer_in_library():
    eng = ClaspDesignEngine(payload_radii_A=[16.0, 16.0], n_min=4, n_max=14)
    eng.add_observation(Observation(n_repeats=6, y=0.4, source="user_entered"))
    eng.add_observation(Observation(n_repeats=10, y=0.7, source="user_entered"))
    result = eng.run()
    assert result.next_experiment.n_repeats in result.candidates
    assert result.next_experiment.n_repeats not in {6, 10}
    assert result.evidence_level == "computationally_evaluated"
    assert all("literature_placeholder" in line or "calibrated=False" in line for line in result.priors)


def test_engine_physics_only_still_runs():
    result = ClaspDesignEngine(n_min=5, n_max=9).run()
    assert result.posterior.mean.shape == (5,)
    assert result.next_experiment.n_repeats in range(5, 10)
    assert result.evidence_level == "literature_supported"
```

===== FILE: tests/test_recruitment.py =====
```python
import numpy as np

from origami.physical.recruitment import recruitment_occupancy, steady_occupancy
from origami.priors import CAM_M13_KD_M


def test_steady_state_is_langmuir():
    c = 1e-9
    kd = CAM_M13_KD_M.value
    assert steady_occupancy(c, kd) == c / (c + kd)


def test_occupancy_bounds_follow_kd_sigma():
    result = recruitment_occupancy(c_free_M=1e-9)
    assert result.theta_95_lower <= result.theta_ss <= result.theta_95_upper
    assert result.calibrated is False
    assert result.time_s is None


def test_ode_relaxes_to_steady_state():
    result = recruitment_occupancy(c_free_M=1e-8, kon_per_M_s=1e6)
    assert result.theta_t is not None
    assert abs(result.theta_t[-1] - result.theta_ss) < 1e-3


def test_signal_off_is_empty():
    result = recruitment_occupancy(c_free_M=1e-6, signal_on=False)
    assert result.theta_ss == 0.0


def test_negative_concentration_rejected():
    try:
        steady_occupancy(-1.0, 1e-9)
    except ValueError as exc:
        assert "C_free" in str(exc)
    else:
        raise AssertionError("expected ValueError")
```

===== FILE: tests/test_intermediate_transfer.py =====
```python
import numpy as np

from origami.mechanisms.intermediate_transfer import (
    capture_probability,
    damkohler,
    k_capture_from_specificity,
    simulate_from_ceff,
    simulate_transfer,
)


def test_capture_probability_is_da_over_one_plus_da():
    assert capture_probability(0.0) == 0.0
    assert abs(capture_probability(1.0) - 0.5) < 1e-12
    assert capture_probability(9.0) == 0.9


def test_higher_ceff_raises_damkohler():
    slow = k_capture_from_specificity(1e5, 1e-6)
    fast = k_capture_from_specificity(1e5, 1e-3)
    assert damkohler(fast, 1.0) > damkohler(slow, 1.0)


def test_ode_matches_analytical_steady_state():
    # Synthetic rates for the invariant. Not biological constants.
    result = simulate_transfer(v_prod_M_per_s=1e-6, k_escape_per_s=2.0, k_capture_per_s=8.0)
    assert abs(result.da - 4.0) < 1e-12
    assert abs(result.p_capture - 0.8) < 1e-12
    assert abs(result.intermediate_M[-1] - result.intermediate_ss_M) < 1e-8
    # late flux dP/dt ≈ k_cap * I
    dt = result.time_s[-1] - result.time_s[-2]
    flux = (result.product_M[-1] - result.product_M[-2]) / dt
    assert abs(flux - result.product_flux_M_per_s) / result.product_flux_M_per_s < 0.02
    assert result.calibrated is False
    assert result.confidence_tier == "hypothesis_only"


def test_ceff_path_uses_specificity():
    ceff = 1e-4
    spec = 2e4
    result = simulate_from_ceff(1e-7, 1.0, spec, ceff)
    assert abs(result.k_capture_per_s - spec * ceff) < 1e-12


def test_negative_escape_rejected():
    try:
        damkohler(1.0, 0.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
```
