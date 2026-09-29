# Structural analysis UI

## Purpose

Wiki-ready frontend for CTPR backbone predictions. It calls the FastAPI
chassis in `origami.api.structural` and falls back to `public/sa-snapshot.json`
when the API is offline.

## Scientific basis

Same screw as `origami.physical.backbone`. No new biological constants.

## Run

From the repository root:

```bash
pip install -e ".[ui]"
python host_sa.py
```

In another terminal:

```bash
cd web/structural
npm install
python ../../scripts/export_sa_snapshot.py
npm run dev -- --port 41733 --hostname 0.0.0.0
```

Open the Next.js URL. **Run** is the prediction form. **Present** (`/present`)
is the data board for n = 3, 8, and 14: comparison chart, table, readings,
CSV, and a wiki caption. `calibrated` stays false.

3D coordinates for PyMOL or ChimeraX come from the same screw. No API key
and no language model:

```bash
python scripts/export_ctpr_3d.py --n 3,8,14 --out data/exports/ctpr_3d
```

Chain A is Cα. Chain B is the docking-site marker. The file is not a crystal
of the fusion.

## Wiki figure

Use **Wiki figure**, then print or screenshot. Caption is in the Caption tab.
Do not label the helix as a crystal of the fusion.

## Owner

Hong Kong team ORIGAMI software.
