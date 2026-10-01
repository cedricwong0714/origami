# Stage-1 scaffold kinetics workflow

## Purpose

Expose recruitment and SpyTag locking kinetics for dry-lab planning. Literature priors let the ODE **run and be tested**. They are an emulation of a fusion path, not Hong Kong team measurements. Lab fields stay empty until stage-1 data (~2 weeks).

The structural-analysis API serves `GET /api/kinetics/schema` and `POST /api/kinetics/simulate`. The wiki UI is `/kinetics`.

## Emulation vs lab replacement

| Slot | Now | In ~2 weeks |
|------|-----|-------------|
| `cam_m13_kd_M` | Literature peptide Kd (keep; do not replace with a fusion Kd until measured) | Optional lab override if the fusion Kd is measured |
| `spy_k_on_per_M_s` | Zakeri 2012 apparent second-order rate | Replace with SDS-PAGE / fluorescence fit on the CLASP fusions |
| `spy_k_rev_per_s` | Vacant | Fill from a reversible-complex assay if the 3-step scheme is used |
| `spy_k_bond_per_s` | Vacant | Fill from lock kinetics; switches simulate from lumped to 3-step |
| NanoBiT Kd / k_on / k_off | Dixon 2016. `nanobit_complementation` integrates k_on and k_off. The printed Kd is reported beside k_off/k_on and is not substituted. | Lab concentrations `lg0_M` and `sm0_M` replace the request concentrations. Rates stay the Dixon priors until a lab pair is posted. |

`calibrated` stays false. `confidence_tier` is `hypothesis_only`. Passing pytest is not scientific validation.

Default `POST` with `mode=covalent_timecourse` and no rates uses the lumped irreversible bimolecular path (`d[adduct]/dt = k_on [Tag][Catcher]`) at 10 μM starting concentrations (the Zakeri mixing condition). That is not a 3-parameter fit.

`use_literature_priors: false` without lab rates returns HTTP 400.

`mode=nanobit_complementation` requires `lg0_M` and `sm0_M`. It does not default those concentrations. The ODE parameter is k_off / k_on. The printed Kd stays a reported number.

## Scientific basis

- **CaM–M13 recruitment** uses the published peptide dissociation constant at saturating Ca²⁺ (`origami.priors.CAM_M13_KD_M`, Biochemistry 2006, DOI 10.1021/bi060857u). Steady-state occupancy is Langmuir: θ = C_free / (C_free + K_d). Optional time courses require an explicit association rate `k_on`; it is not filled in from Kd.
- **SpyTag / SpyCatcher**: Zakeri et al. (2012) PNAS, DOI 10.1073/pnas.1115485109, report 1.4 × 10³ ± 43 M⁻¹ s⁻¹ (SD, n = 3) for SpyTag-MBP + SpyCatcher at 10 μM, 25 °C, phosphate-citrate, SDS-PAGE. That number is the canonical `spy_k_on`. Keeble 2017 1.7 ± 0.4 × 10³ M⁻¹ s⁻¹ is a later parental re-measure and is not used. Keeble 2019 SpyTag003 k_on/k_off is a different pair and is not mixed in. Repo `covalent_capture.defaults.json` relative rates are not used.

## Inputs

| Field | Mode | Notes |
|-------|------|--------|
| `c_free_M` | recruitment_steady | Free signal concentration (M) |
| `kon_per_M_s` | recruitment_steady | Optional; enables ODE time course |
| `spy_k_on_per_M_s` | covalent_timecourse | Optional; defaults to Zakeri literature prior |
| `spy_k_rev_per_s`, `spy_k_bond_per_s` | covalent_timecourse | Optional lab pair; both required to use the 3-step ODE |
| `tag0_M`, `catcher0_M` | covalent_timecourse | Default 10 μM |
| `use_literature_priors` | both | Default true |

## Outputs

- Schema: `origin` is `literature_prior` or `lab_measurement`. `lab_value` is always null on GET.
- Simulate: `calibrated: false`, `confidence_tier: hypothesis_only`, `human_review_required: true`.

## Assumptions

- Well-mixed mass action; no spatial PDE.
- Free ligand is not depleted by binding in recruitment steady state.
- Lumped Spy path treats covalent product as irreversible bimolecular.

## Known limitations

- `k_rev` and `k_bond` for the parental pair are not in Zakeri 2012.
- NanoBiT complementation is the untethered Dixon mass-action law. It is not a fusion measurement. k_on is approximate and has no printed standard error.
- Residual GP is unfitted. No assay y was invented.

## Parameter sources

- `cam_m13_kd_M`: `origami.priors.CAM_M13_KD_M`
- `spy_k_on_per_M_s`: `origami.priors.SPY_K_ON_PER_M_S`
- NanoBiT: `NANOBIT_KD_M`, `NANOBIT_K_ON_PER_M_S`, `NANOBIT_K_OFF_PER_S` (Dixon 2016, DOI 10.1021/acschembio.5b00753)

## Tests

```bash
PYTHONPATH=/workspace python -m pytest tests/math_chassis/test_kinetics.py tests/math_chassis/test_docking_kinetics_engine.py -q
```

## Owner

Dry-lab / math chassis maintainers.
