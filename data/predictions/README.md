# data/predictions/

Prospective-prediction workflow storage (CLASP Docs §1.6). This is what makes
ORIGAMI a genuine design tool rather than a post-hoc analysis tool.

## Layout

```
data/predictions/
├── frozen/        # Predictions frozen BEFORE the wet lab runs (timestamped + checksummed)
└── comparisons/   # Observed-vs-frozen comparisons written AFTER results return
```

## Rules (AGENTS.md)

- Every frozen prediction records: `prediction_id`, `frozen_timestamp`,
  `model_version`, `dataset_version`, `design_spec`, `predictions` (each with
  `predicted_value`, `uncertainty_95_lower`, `uncertainty_95_upper`,
  `confidence_tier`), `parameter_sources`, `assumptions`, and a `file_checksum`.
- Frozen predictions are **immutable** once written. Corrections are written as
  a new versioned file, never by overwriting (see `src/compliance/data_integrity.py`).
- Comparison files reference the frozen prediction they compare against by
  `prediction_id` and `file_checksum` so the link is auditable.

These artifacts are software provenance records, not claims of wet-lab success.
