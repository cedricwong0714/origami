---
name: predict-aes
description: Produces AES (or related) predictions only with uncertainty, model version, and confidence tier. Use when scoring designs with the GP/ensemble predictor. Never return a bare number.
disable-model-invocation: true
---

# predict-aes

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/gp_model/predict_aes.py::predict_aes`. Never report a point estimate without the function’s interval and tier.

## When

- Ranking or scoring a design for AES/activity.
- Dashboard or CLI prediction requests.

## Do

1. Call `predict_aes` and return predicted value, 95% interval, units, tier, extrapolation flag, model version, sources, warnings.
2. Pair with `check-ood` when features may leave the training support.

## Do not

- Return a bare number.
- Relabel extrapolated or hypothesis-only as interpolated/validated.
- Claim the model is experimentally validated because tests pass.

## Human

A human decides whether the interval and tier justify a wet-lab choice.
