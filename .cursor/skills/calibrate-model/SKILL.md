---
name: calibrate-model
description: Fits calibration models and reports identifiability, not just point estimates. Use when fitting kinetics or GP calibration to experimental datasets.
disable-model-invocation: true
---

# calibrate-model

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/calibration/calibrate_model.py::calibrate_model`. Non-identifiable parameters must be reported as such.

## When

- Fitting to an approved experimental dataset.
- Updating residual or dose-response calibration.

## Do

1. Call `calibrate_model` with data version, bounds, and parameter names.
2. Surface uncertainties, non-identifiable names, DoF, and dataset version.
3. Use only datasets marked approved for model training in metadata.

## Do not

- Present non-identifiable values as fitted truth.
- Overwrite raw experimental files.
- Claim fit quality equals biological validation.

## Human

A human approves which parameters are fixed vs free and whether the fit may ship.
