---
name: extract-params
description: Extracts biological parameters only when a cited source is present. Use when pulling constants, ranges, or units from evidence into code or models.
disable-model-invocation: true
---

# extract-params

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/compliance/extract_params.py::extract_params`. Unsourced values must not be silently used.

## When

- Adding or updating a biological constant.
- Filling model parameters from literature.

## Do

1. Run `extract_params` on the candidate records.
2. Keep name, value, units, bounds, source, system, method, notes as the function returns them.
3. If source is missing, follow the function’s warn-and-None path. Do not invent a number.

## Do not

- Change units or normalization without an explicit, reviewed conversion.
- Treat an LLM-recalled constant as extracted.

## Human

A human must approve any new or changed biological parameter before production use.
