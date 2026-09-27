---
name: validate-moclo
description: Validates MoClo assembly graphs, overhangs, and part order. Use when compiling Golden Gate/MoClo constructs or checking assembly feasibility.
disable-model-invocation: true
---

# validate-moclo

SAFETY-CRITICAL. Implement/call the pure Python function; NEVER use an LLM as final authority for this check.

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/moclo_compiler/validate_moclo.py::validate_moclo`. Assembly validity is that return value.

## When

- Compiling a MoClo design.
- Changing part order, overhangs, or vector backbone.

## Do

1. Feed the design into `validate_moclo`.
2. Do not emit assembled sequence if validation fails.
3. Keep compilation deterministic; no random or LLM-generated parts.

## Do not

- Patch overhang conflicts in prose instead of the function.
- Silently rewrite part sequences to make assembly “work.”

## Human

A human approves compiler output and any intended sequence change (show the diff).
