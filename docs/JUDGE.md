# ORIGAMI for judges

Hong Kong team ISEF 2026. CLASP dry-lab software. This page is a reading guide. It is not a wet-lab claim.

## What it is

ORIGAMI is a stack of transparent calculators for a CTPR scaffold: geometry, literature stability, docking and steric clash, kinetics, lab intake, and an active-learning layer on top. It is not a trained black-box predictor of a fusion, and it does not generate DNA sequences.

A number in the software is one of three things: a literature value with a source, a team assumption that warns at runtime, or a blank waiting for a measurement. Predictions that depend on literature parameters stay `calibrated = false`.

## What a judge can run

GitLab: https://gitlab.ISEF.org/2026/software/hong-kong-team/origami

GitLab Pages (Deploy → Pages on `main`) serves a static landing page and a browser CTPR optimizer. That is not the full model.

Full chassis, on a laptop:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python host_sa.py
```

In a second terminal: `cd web/structural && npm install && npm run dev`. Open http://127.0.0.1:3000 .

| Page | What you see |
|---|---|
| `/` | Screw geometry for a repeat count you type |
| `/stability` and `/stability/calculator` | Literature Tm / ΔG and the Gibbs–Helmholtz calculator |
| `/kinetics` | Recruitment, Spy lock, or NanoBiT when concentrations are supplied |
| `/ssdk` | All four chassis, plus luminescence gates |
| `/lab` and `/intake` | Empty lab slots and plate CSV import |
| `/learn` | Next length to measure; not a validated design |
| `/guide` | What needs lab data versus what is already literature |

Operator detail: [USER_MANUAL.md](USER_MANUAL.md). Equations and limits: [MODEL_CARDS.md](MODEL_CARDS.md). HTTP routes: [API.md](API.md).

## How to read a result

- `calibrated: false` means the team has not approved a project dataset for that claim.
- A pass/fail on luminescence uses μ − 1.96σ against a threshold marked `unmeasured` until a plate-reader CV exists. A pass on placeholder units is not an assay decision.
- Two recommenders can disagree. `next_n` is the older residual Gaussian process on the docking score. The multi-fidelity block recommends a length by expected improvement divided by cost. Both are suggestions for the next well.
- The stability calculator’s ΔG at 10 °C sits 0.5–5.0 kcal/mol above Phillips’ printed ΔG. The gap is reported, not hidden.

## What the team still has to supply

Measured assay CVs and pass thresholds, frozen predictions for the lengths they will actually build, and group labels when real plates exist. Those fields are blank on purpose.

## AI assistance

Coding agents helped build and document this repository. The team remains responsible for every constant, every page, and every decision taken from a screen. See the wiki AI attribution. A passing test is not scientific validation.
