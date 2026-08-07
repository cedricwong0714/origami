# data/

Experimental records and metadata for CLASP → ORIGAMI.

| Path | Contents |
|------|----------|
| `stage1_ingestion/` | Early characterization: MW/yield notes, Spy kinetics metadata, NanoBiT plate metadata |
| `stage2_baselines/` | Intracellular / CTPR library baselines once SCALE M1+ exists |
| `raw_metadata/` | Assay condition templates (T, buffer, instrument) |

**Honesty rule:** files under `examples/` are **synthetic fixtures for schema/CI** unless `data_class` says otherwise. Real measurements must set `data_class` to `tier1_experimental` and include operator + date.

Large raw instrument exports → Zenodo (link DOIs here when available).
