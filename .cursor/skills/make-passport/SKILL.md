---
name: make-passport
description: Builds a design/prediction passport from recorded inputs, verification, and model metadata. Use when exporting a reproducible summary for humans, never as a substitute for verification.
disable-model-invocation: true
---

# make-passport

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/ui/make_passport.py::make_passport`. Passport fields must come from recorded function outputs.

## When

- Packaging a design for review.
- After verification and prediction have run.

## Do

1. Feed already-computed verification, prediction, checksums, and versions into `make_passport`.
2. Include uncertainty, tier, sources, and halt flags as provided.

## Do not

- Fill empty fields with LLM prose presented as recorded fact.
- Generate sequences or citations inside the passport.

## Human

A human signs the passport. Unsigned passports are not release documents.
