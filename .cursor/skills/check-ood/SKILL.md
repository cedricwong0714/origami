---
name: check-ood
description: Detects out-of-distribution inputs for the GP/ensemble predictor. Use before or with AES predictions when designs may leave calibrated feature ranges.
disable-model-invocation: true
---

# check-ood

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/gp_model/check_ood.py::check_ood`. OOD status is not an LLM similarity guess.

## When

- Before trusting `predict_aes`.
- Design parameters sit near or outside calibration.

## Do

1. Run `check_ood` on the feature vector / design spec.
2. If OOD, force extrapolated or hypothesis_only per the function; require human review.
3. Do not present OOD predictions as interpolated.

## Do not

- Shrink uncertainty in chat to look confident.
- Ignore OOD flags because the point prediction “looks reasonable.”

## Human

A human must approve any OOD prediction before experimental use.
