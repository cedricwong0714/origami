# web/

Standalone HTML demos for ORIGAMI / CLASP.

| `structural/` | Structural analysis UI (Next.js). Needs the FastAPI chassis for live n. |
| `index.html` | Landing page. Open the file in a browser. |
| `ctpr_scaffold_optimizer.html` | CTPR docking-spacing optimizer UI (browser-only) |

These files are not published by GitHub Pages. The live studio is `structural/` with `python host_sa.py` and `npm run dev`, as in [docs/USER_MANUAL.md](../docs/USER_MANUAL.md).

Open in a browser, or use the Python-backed **Optimize CTPR spacing** mode in Streamlit (`streamlit run app.py`), which calls `src/scaffold_optimizer/`.

Geometry constants must match `src/core/ctpr_geometry.py` (1.1 nm rise, 45° twist,
cylindrical screw; docking radius = scaffold + loop offset).
