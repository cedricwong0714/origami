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
