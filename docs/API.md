# API cheat sheet

Base URL on a laptop: `http://127.0.0.1:41287`. Interactive schema: `/docs`. The Next.js dev server proxies `/api` to that port. A static export does not.

All responses that are predictions include `calibrated: false` unless a future, explicit wet-lab flag is added. Do not treat HTTP 200 as validation.

## Health and metadata

| Method | Path | Body |
|---|---|---|
| GET | `/health` | — |
| GET | `/api/meta/dependencies` | — |
| GET | `/api/meta/active-learning-config` | — |

## Structure

| Method | Path | Notes |
|---|---|---|
| GET | `/api/sa/meta` | Model notes |
| GET | `/api/sa/scaffold/{n_repeats}` | One screw. n from 3 to 24 |
| GET | `/api/sa/library` | Payload-free backbones |
| GET | `/api/sa/predict` | Query-parameter prediction |

## SSDK

`POST /api/ssdk/chassis`

```json
{"n_repeats": 8}
```

Optional: `indices`, `radii_A` (two Å values), `lab_tm_C`, `kinetics`.

`POST /api/ssdk/learn`

```json
{
  "n_min": 8,
  "n_max": 14,
  "acquisition": "ei",
  "observations": [
    {"n_repeats": 8, "y": 0.4, "sigma": 0.05, "fidelity": 1, "source": "surrogate"}
  ]
}
```

`acquisition` is `ucb`, `ei`, or `entropy`. `learner` is `sklearn` (default) or `design_engine`. `fidelity` is 0 (dry) or 1 (wet); omitted means 1. `output` is one of `luminescence`, `locking_fraction`, `expression`, `solubility`, `purity` (default luminescence). Optional `sequence` uses composition unless `sequence_encoding` is `onehot` or `esm2`. `batch_size` is 1 to 12.

Read `learner_family` and `next_n` for the recommendation that was actually used. `design_engine_next_n` is always the older residual GP. `multioutput.overall_status` is PASS, FAIL, or NOT_GATED. `batch.selected` is the plate of lengths. `canonical.heteroscedastic.replaces_assay_cv` is false.

CLI: `origami learn-ssdk --json-body '{"n_min":8,"n_max":12,"observations":[]}'`

## Stability

| Method | Path |
|---|---|
| GET | `/api/stability/panel` |
| GET | `/api/stability/confirm` |
| GET | `/api/stability/thermo/prefill` |
| POST | `/api/stability/thermo` |
| POST | `/api/stability/thermo/curves` |
| POST | `/api/stability/thermo/effective` |

## Kinetics

| Method | Path |
|---|---|
| GET | `/api/kinetics/schema` |
| POST | `/api/kinetics/simulate` |

Modes include `recruitment_steady`, `covalent_timecourse`, and `nanobit_complementation`. Concentrations are in molar.

## Lab

| Method | Path | Body |
|---|---|---|
| GET | `/api/lab/schema` | Slot list. Values start null |
| POST | `/api/lab/run` | `prep`, `assay_window`, `calcium`, `lock`, `bridging`, `quality` |
| POST | `/api/lab/plate` | `csv_text`, `source` |
| POST | `/api/lab/ablation` | Feature matrix for grouped ablation |

Quality example:

```json
{"quality": {"inter_day_rlu": [100, 108, 92, 101]}}
```

Plate columns: `well`, `construct`, `n_repeats`, `batch`, `role`, `rlu`. `role=blank` is subtracted inside each batch.

## Errors

HTTP 400 with `detail` means the body was rejected (non-integer n, sigma ≤ 0, fidelity not 0 or 1, non-finite number). The server does not fill the missing field from a prior.
