# stage1_ingestion/

Stage-1 characterization packages (solubility, SpyTag kinetics metadata, NanoBiT luminescence plate maps, Learn Mode product time series).

Put one folder or JSON record per assay batch. Validate against the matching schema before Learn Mode ingestion.

## Learn Mode product time series

| Path | Role |
|------|------|
| `schema_learn_timeseries.json` | Sidecar schema (checklist D) |
| `templates/learn_product_timeseries.csv` | Blank CSV (`time`, `product`) |
| `templates/learn_product_timeseries.metadata.json` | Blank sidecar — fill before Tier-1 |
| `examples/learn_product_timeseries/` | Synthetic fixture for CI / demos |

Load with:

```python
from src.data_ingestion import load_learn_timeseries_package

pkg = load_learn_timeseries_package("path/to.csv", "path/to.metadata.json")
# pkg.time, pkg.product, pkg.metadata.mechanism_type, pkg.warnings
```

**Honesty:** `examples/` and any `data_class: synthetic_fixture` file are not lab measurements. Set `tier1_experimental` only with operator, real `created_utc`, and blank/negative controls recorded.
