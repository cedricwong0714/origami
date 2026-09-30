# Stage-1 scaffold kinetics workflow

## Purpose

Expose recruitment and SpyTag locking kinetics for dry-lab planning without inventing wet-lab rate constants. The structural-analysis API serves a schema (`GET /api/kinetics/schema`) and a simulate endpoint (`POST /api/kinetics/simulate`). The wiki UI lives at `/kinetics`.

## Scientific basis

- **CaM–M13 recruitment** uses the published peptide dissociation constant at saturating Ca²⁺ (`origami.priors.CAM_M13_KD_M`, Biochemistry 2006, DOI 10.1021/bi060857u). Steady-state occupancy is Langmuir: θ = C_free / (C_free + K_d). Optional time courses require an explicit association rate `k_on`; it is not filled in by the server.
- **SpyTag / SpyCatcher locking** follows a reversible capture step plus an irreversible lock step (mass action). Association, off-rate, and lock-rate slots are **vacant** until stage-1 ingestion records them. The server does **not** read `models/kinetic_models/covalent_capture.defaults.json` for this workflow.

## Inputs

| Field | Mode | Notes |
|-------|------|--------|
| `c_free_M` | recruitment_steady | Free signal concentration (M) |
| `kon_per_M_s` | recruitment_steady | Optional; enables ODE time course |
| `spy_k_on_per_M_s`, `spy_k_rev_per_s`, `spy_k_bond_per_s` | covalent_timecourse | Required in the POST body; schema slots stay vacant until lab data |
| `tag0_M`, `catcher0_M` | covalent_timecourse | Initial concentrations (default 1.0 M relative units) |

## Outputs

- Schema: rate slot status (`literature`, `vacant`, or `user_supplied` on simulate), computed formulas, and mode list.
- Simulate: `calibrated: false`, `confidence_tier: hypothesis_only`, `human_review_required: true`, plus recruitment or concentration time series.

## Assumptions

- Well-mixed mass action; no spatial PDE.
- Free ligand is not depleted by binding in recruitment steady state.
- User-supplied SpyTag rates are hypothesis inputs, not validated chassis parameters.

## Known limitations

- No stage-1 SpyTag package is wired yet; three rate slots remain vacant.
- Covalent simulate rejects requests that omit explicit SpyTag rates.
- Passing pytest or TypeScript build is not scientific validation.

## Parameter sources

- `cam_m13_kd_M`: `origami.priors.CAM_M13_KD_M` (literature peptide Kd).
- SpyTag rates: none in production until `data/stage1_ingestion/` packages exist.

## Tests

```bash
PYTHONPATH=/workspace python -m pytest tests/math_chassis/test_kinetics.py -q
```

## Owner

Dry-lab / math chassis maintainers.
