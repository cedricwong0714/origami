---
name: check-structure
description: Checks structural/geometric constraints of scaffold and domain layouts. Use when steric clash, linker geometry, or domain placement may invalidate a design.
disable-model-invocation: true
---

# check-structure

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/verification/check_structure.py::check_structure`. Geometric pass/fail is not an LLM opinion.

## When

- Scaffold repeat count, linker length, or domain order changes.
- Before claiming a layout is physically plausible.

## Do

1. Run `check_structure` on the geometric/design payload.
2. Surface clashes, bound violations, and assumptions from the function.
3. Mark out-of-range geometry as extrapolation, not “OK.”

## Do not

- Invent clash distances or fold scores from memory.
- Silently change units (Å vs nm).

## Human

A human approves designs that fail or sit at the edge of calibrated geometry.
