# Temporary dry-lab checkpoint

Not a final release. Not a wet-lab dataset. `calibrated` is false.

Generated after `171` pytest files in the math chassis / sandbox / related suites passed, then one `run_sandbox` call at `n_repeats = 8` with the default thermal prior.

| File | Contents |
|---|---|
| `checkpoint-n8.json` | Full sandbox bundle: report, confirmation table, dry-lab measurements, stability panel, Cα scene |
| `confirmation-n3-24.csv` | Screw, clash, physics score, Phillips 2012 CTPRa DSC gate, printed ΔG for n = 3..24 |
| `stability-panel.csv` | Four Tm series, unmixed, every library n |

`next_n` and `next_delta_i` in the JSON are the next coordinates to measure. They are not use-case optima.

To regenerate:

```bash
python -c "from sandbox.service import run_sandbox; import json; print(json.dumps(run_sandbox({'design_id':'checkpoint-n8','n_repeats':8})))"
```
