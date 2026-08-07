# compliance/

Code implementations of **[AGENTS.md](../../AGENTS.md)** engineering discipline for ORIGAMI.

## Purpose

Operationalizes uncertainty, provenance, sequence integrity, layered verification,
and honest refusal — the minimum bar for trustworthy synbio software assistance.

## Modules

| Module | AGENTS.md section |
|--------|-------------------|
| `biological_parameters.py` | §4 sourced constants + `get_parameter_or_warn` |
| `sequence_integrity.py` | §5 checksums, reading frame, forbidden sites |
| `prediction_result.py` | §6 `PredictionResult` + profile adapter |
| `structured_answer.py` | §7.3 Explore answer separation |
| `units.py` | §8.3 explicit unit conversion |
| `data_integrity.py` | §8.1–8.2 immutable raw data writes |
| `fallback.py` | §13 degradation hierarchy |

Five verification layers live under `src/verification/layers/` and are orchestrated
by `src/verification/engine.py`.

## Tests

```bash
pytest tests/unit_tests/test_compliance.py tests/unit_tests/test_verification.py
```

## Owner

Hong Kong team dry lab — see repository README.
