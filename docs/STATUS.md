# ORIGAMI status and next build

Planning status after 2026-10-02 lives in [SSDK_ROADMAP.md](SSDK_ROADMAP.md). The table below is the earlier slice note.

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
