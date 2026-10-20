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
git clone https://github.com/cedricwong0714/origami.git
cd origami
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev,ui]"
pytest -q
python host_sa.py
```

Python 3.10 or newer. The package is not on PyPI. Streamlit is the `ui` extra: `streamlit run sandbox/app.py` is the design sandbox, and `streamlit run app.py` is the older Explore / Design / Learn dashboard. The studio is `cd web/structural && npm install && npm run dev` while `host_sa.py` is on port 41287. Full steps are in `docs/USER_MANUAL.md`.

---

## Call order of the engine

1. `build_ctpr(n)` → docking frames + covariance  
2. `steric_report` + `gaussian_chain_ceff` → physics score \(S(n)\)  
3. If observations exist: `ResidualGP.fit(X, y, S)` then `predict`  
4. `recommend(...)` → integer \(n\) for the next assay  

Entry point: `ClaspDesignEngine.run()` in `origami/engine.py`.

---

## What to implement next (in order)

### 1. Recruitment ODE — done in `origami/physical/recruitment.py`

Steady state uses the published CaM–M13 peptide Kd (DOI 10.1021/bi060857u). Time course only if the caller supplies `kon`. Do not invent `kon`.

### 2. Damköhler-reduced transfer — done in `origami/mechanisms/intermediate_transfer.py`

`Da = k_capture / k_escape`, `P = Da/(1+Da)`. `k_escape` and `k_cat/K_m` are inputs. Audit: `docs/MODEL_AUDIT.md`.

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
