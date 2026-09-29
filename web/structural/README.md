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

Open the Next.js URL. `calibrated` stays false.

## Wiki figure

Use **Wiki figure**, then print or screenshot. Caption is in the Caption tab.
Do not label the helix as a crystal of the fusion.

## Owner

Hong Kong team ORIGAMI software.
