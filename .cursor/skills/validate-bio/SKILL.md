---
name: validate-bio
description: Runs layered biological verification (integrity, plausibility, model consistency, safety, reproducibility). Use before treating a design or prediction as ready.
disable-model-invocation: true
---

# validate-bio

SAFETY-CRITICAL. Implement/call the pure Python function; NEVER use an LLM as final authority for this check.

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/verification/validate_bio.py::validate_bio`. Layer pass/fail comes only from that function.

## When

- A design, prediction, or export is about to be acted on.
- After model or sequence changes.

## Do

1. Call `validate_bio` with design, prediction, and libraries.
2. Report each layer as the function reports it.
3. Do not remove or skip layers.

## Do not

- Re-grade a failed layer with narrative confidence.
- Claim tests passing equals scientific validation.

## Human

A human approves any warning-only layer and all failed layers before wet-lab action.
