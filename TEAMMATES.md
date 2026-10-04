# Temporary teammate access (not final)

This is a checkpoint so others can see saved numbers and run the models locally without the Cursor agent. It is not a production host and not a wet-lab dataset. `calibrated` stays false.

Live hosting that survives the Cursor agent is documented in [`HOSTING.md`](HOSTING.md). Start **`host_app.py`**. Do not `pip install origami` from PyPI.

## What Vercel can do

Vercel cannot run Streamlit, numpy, or `sandbox/modelling.py`.

It **can** serve a saved snapshot of those models:

```bash
python scripts/write_modelling_static.py
npx vercel --cwd web/modelling-static --yes
```

Project root: `web/modelling-static`. Bound fraction in the browser is the Langmuir formula with the saved peptide Kd. Clash, melt, and Spy lock are lookup tables written by the Python chassis.

The older n = 8 checkpoint is still `web/checkpoint/`.

## What actually runs the models

On a laptop (Python 3.10+):

```bash
git clone <this-repo>
cd <this-repo>
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[ui]"
streamlit run sandbox/app.py --server.port 48621 --server.address 0.0.0.0
```

Open http://127.0.0.1:48621 and press **Run design**. That is the live chassis.

Python, same venv:

```python
from origami.engine import run_design
from sandbox.service import run_sandbox

report = run_design("probe", 8)
bundle = run_sandbox({"design_id": "probe", "n_repeats": 8, "thermal_prior": True})
```

Older `src/` ODEs and the Explore/Design Streamlit (`streamlit run app.py`) are a second stack. They are not the sandbox button.

## Saved data already in the repo

After tests passed (171 in the chassis/sandbox-related suites), these files were written:

- `data/checkpoint/checkpoint-n8.json`
- `data/checkpoint/confirmation-n3-24.csv`
- `data/checkpoint/stability-panel.csv`
- copies under `web/checkpoint/` for the static page

Regenerate after you change models. Do not treat this snapshot as the live engine.
