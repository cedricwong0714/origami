---
name: run-tests
description: Runs the project’s automated test suites via the compliance runner. Use when verifying code after a change; passing tests are not scientific validation.
disable-model-invocation: true
---

# run-tests

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/compliance/run_tests.py::run_tests` (or report exactly what that runner invokes). Do not invent pass/fail.

## When

- After implementation in an assigned module.
- Before claiming the suite is green.

## Do

1. Execute `run_tests` and return its recorded outcomes by category (unit, scientific, golden, integration, adversarial) if provided.
2. State clearly: tests check code execution and coded invariants, not wet-lab truth.

## Do not

- Skip failing tests or rewrite golden files without documenting why the output changed.
- Equate pytest green with a validated biological model.

## Human

A human interprets scientific-invariant failures and golden diffs.
