# web/

Standalone HTML demos for ORIGAMI / CLASP.

| File | Role |
|------|------|
| `ctpr_scaffold_optimizer.html` | CTPR docking-spacing optimizer UI (browser-only) |

Open in a browser, or use the Python-backed **Optimize CTPR spacing** mode in Streamlit (`streamlit run app.py`), which calls `src/scaffold_optimizer/`.

Geometry constants must match `src/core/ctpr_geometry.py` (1.1 nm rise, 20° twist).
