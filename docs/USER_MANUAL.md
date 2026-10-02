# ORIGAMI user manual

Hong Kong team ISEF 2026 software. This manual is how to install and use the chassis. It is not a scientific validation. Every prediction stays `calibrated = false` until a human approves a project dataset for that claim.

Policy for AI assistants: [.claude/RESPONSIBLE_AI_USE.md](../.claude/RESPONSIBLE_AI_USE.md). Engineering rules: [AGENTS.md](../AGENTS.md). What still needs lab numbers: [DATA_DEPENDENCY_MATRIX.md](DATA_DEPENDENCY_MATRIX.md).

## 1. What you can do

- Measure a CTPR screw (contour, span) for a repeat count you type (3 to 24).
- Look up literature stability (Phillips 2012 / Cortajarena 2011) and run the Gibbs–Helmholtz calculator.
- Score docking clash and effective concentration when you supply radii (default payload size is CaM–M13 from PDB 2BBM).
- Simulate recruitment, Spy lock, or NanoBiT when you supply concentrations.
- Enter surrogate or plate readouts and get a next-length suggestion plus a luminescence multi-fidelity gate (μ, σ, pass/fail, cost-weighted expected improvement).
- Import a plate CSV, run grouped ablation, and post Phase 2–4 lab sections (including Phase 3 quality slots).

You cannot treat a green pass as a wet-lab decision. Thresholds and assay CVs in `data/config/active_learning_config.json` are placeholders until you mark them `measured`.

## 2. Two ways the software is served

| Surface | What it runs | How |
|---|---|---|
| GitLab Pages | Static HTML only (landing + CTPR optimizer demo) | Deploy → Pages on `main` |
| Full chassis | Python API + Next.js wiki, or Streamlit | Your laptop or a host you own |

Pages does not execute `run_design`, the Gaussian process, or the lab intake.

## 3. Install

```bash
git clone https://gitlab.ISEF.org/2026/software/hong-kong-team/origami.git
cd origami
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Optional Streamlit UI: `pip install -e ".[ui]"`.

Python 3.10+ (3.12 in CI). The package is not on PyPI. Do not `pip install origami`.

## 4. Wiki UI (recommended for the team)

Terminal A:

```bash
python host_sa.py
```

API listens on port **41287**. OpenAPI: http://127.0.0.1:41287/docs

Terminal B:

```bash
cd web/structural
npm install
npm run dev -- --port 3000
```

Open http://127.0.0.1:3000 . The dev server rewrites `/api` to port 41287.

| Page | Use |
|---|---|
| `/` | Structural run for one n |
| `/present` | Saved presentation tables |
| `/stability` | Literature Tm check |
| `/stability/calculator` | ΔG(T) from enthalpy and ΔCp |
| `/kinetics` | Kinetics forms |
| `/ssdk` | Four chassis for one n, plus luminescence gates |
| `/lab` | Lab sections (prep, calcium, lock, bridging) |
| `/intake` | Plate CSV and ablation JSON |
| `/learn` | Surrogate rows and next length |
| `/guide` | Dependency list and placeholder config |

### 4.1 SSDK luminescence gates

On `/ssdk`, scroll to **Predictions & gates**. Set `n_min` and `n_max`. Observations are JSON:

```json
[
  {"n_repeats": 8, "y": 0.4, "fidelity": 1, "source": "surrogate"},
  {"n_repeats": 10, "y": 0.8, "sigma": 0.05, "fidelity": 1, "source": "plate"}
]
```

- `fidelity` 1 = wet readout (`y`). Omitted means 1.
- `fidelity` 0 = dry. The learner also fills dry physics scores for lengths you did not measure.
- Pass means μ − 1.96σ is at least the luminescence threshold in the config file. The threshold is still `unmeasured` and is in “× background RLU”, so a surrogate `y` on another scale will not pass honestly. Read the note on the page.

`/learn` does the same learn call from a table. It also shows the older residual Gaussian process (`next_n`) and the Phillips literature tracks. Those literature tracks are not a request to run a melt.

### 4.2 Data intake

`/intake` posts CSV text to `POST /api/lab/plate` and a feature matrix to `POST /api/lab/ablation`. CSV columns: `well`, `construct`, `n_repeats`, `batch`, `role`, `rlu`. `role=blank` is subtracted per batch. The response includes a SHA-256 of the file text.

### 4.3 Lab chassis

`/lab` posts JSON to `POST /api/lab/run`. Empty sections stay “not submitted”. Optional `quality` object (Phase 3):

```json
{
  "quality": {
    "inter_day_rlu": [100, 108, 92, 101],
    "competitor_fold": 20,
    "complex_fraction_after_h": 0
  }
}
```

Inter-day values return a coefficient of variation and a suggested observation σ (`mean × CV`). That does not edit the config file. You copy a measured CV in by hand and set `status` to `measured`.

Slot names: `GET /api/lab/schema`.

## 5. Streamlit (second UI)

```bash
pip install -e ".[ui]"
streamlit run sandbox/app.py --server.port 48621
```

Design sandbox calls the math chassis. `streamlit run app.py` is the older Explore / Design / Learn dashboard. `host_app.py` is the entry named in [HOSTING.md](../HOSTING.md) for a long-lived host.

## 6. Command line

From the repo root, with the venv active, the `origami` command includes:

| Command | Role |
|---|---|
| `origami validate-learn CSV META.json` | Check a Learn time-series package |
| `origami optimize --radius-a 45 --radius-b 25 --interaction Metabolic` | Rank CTPR spacing (computational) |
| `origami freeze ...` | Write a frozen prediction file (see `--help`) |
| `origami compare ...` | Compare a later run to a frozen file |
| `origami import-plate PATH` | Parse a plate CSV |
| `origami learn-plate PATH` | Plate → SSDK learner |
| `origami ablation` | Grouped ablation (see `--help`) |
| `origami pipeline` | Demo verification path (not the wiki) |

`origami freeze` still labels a ±30% band as a placeholder. Parameter elasticities in that output are sensitivity, not a confidence interval.

## 7. HTTP API (short)

All JSON. Errors are HTTP 400 with `detail`.

| Method | Path | Body |
|---|---|---|
| GET | `/health` | — |
| GET | `/api/sa/scaffold/{n}` | n = repeats |
| POST | `/api/ssdk/chassis` | `{"n_repeats": 8}` plus optional radii, indices, `kinetics` |
| POST | `/api/ssdk/learn` | `n_min`, `n_max`, `observations`, optional `acquisition` (`ucb`, `ei`, `entropy`) |
| GET | `/api/lab/schema` | — |
| POST | `/api/lab/run` | prep, assay_window, calcium, lock, bridging, quality |
| POST | `/api/lab/plate` | `csv_text`, `source` |
| POST | `/api/lab/ablation` | matrix the ablation endpoint documents |
| GET | `/api/stability/panel` | literature lookup |
| GET | `/api/stability/thermo/prefill?n=` | ΔH, ΔCp where the table has them |
| POST | `/api/stability/thermo` | calculator inputs |
| GET | `/api/kinetics/schema` | — |
| POST | `/api/kinetics/simulate` | mode and concentrations |
| GET | `/api/meta/dependencies` | handoff lists |
| GET | `/api/meta/active-learning-config` | thresholds, CVs, costs |

Example learn call:

```bash
curl -s http://127.0.0.1:41287/api/ssdk/learn \
  -H 'Content-Type: application/json' \
  -d '{"n_min":8,"n_max":14,"observations":[{"n_repeats":8,"y":0.4,"fidelity":1,"source":"surrogate"}]}'
```

Read `multifidelity_luminescence` for the gate. Read `next_n` for the older residual GP. They can disagree. Both are uncalibrated.

## 8. Numbers you must not treat as measurements

| Item | Status |
|---|---|
| Fusion CaM–M13 Ca²⁺ Kd 80 nM | Secondhand (Nagai 2014 citing Porumb 1994). Not the 0.19 nM free-peptide Kd. |
| Spy rate 1.4×10³ M⁻¹ s⁻¹ | Zakeri 2012, lumped. No numeric reverse rate (no reversal seen). |
| Recruitment k_on 1×10⁶ | Assumption. Code warns on every call. |
| Pass thresholds and assay CVs | `unmeasured` in the config JSON. |
| Costs (dry 0.01 … full panel 10) | Prior choice, arbitrary units. |
| n = 17 | Computable if you type it. Not a calibrated design point. |
| OtsA/OtsB | Literature only. Not in the wet plan. |
| Calculator ΔG vs Phillips printed ΔG | 0.5–5.0 kcal/mol higher at 10 °C. Pinned, unexplained. |

## 9. Tests

```bash
pytest -q
```

A passing test checks code and pinned literature figures. It does not validate a construct.

## 10. If something fails

- UI says the API is down: start `python host_sa.py` and confirm http://127.0.0.1:41287/health .
- Next.js calls 404 on `/api`: you are on `next export` or a static host. Use `npm run dev` with the rewrite, or call port 41287 directly.
- Learn returns 400: `n_repeats` outside `n_min`–`n_max`, sigma ≤ 0, or fidelity not 0 or 1.
- GitLab push 403: the token needs **Code: Push** on the ISEF project.

## 11. Repository

Judging remote: https://gitlab.ISEF.org/2026/software/hong-kong-team/origami

Default branch `main` holds the chassis described here. Static Pages update when the `pages` CI job runs on `main`.
