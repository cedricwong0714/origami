---
name: check-synthesis
description: Checks whether a construct is suitable for DNA synthesis ordering (length, complexity flags from code). Use before generating order files or vendor payloads.
disable-model-invocation: true
---

# check-synthesis

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/verification/check_synthesis.py::check_synthesis`. Order-readiness is that function’s result.

## When

- Exporting sequences for a synthesis vendor.
- After compiler output is otherwise valid.

## Do

1. Pass compiled sequence and metadata into `check_synthesis`.
2. Block order files if the function fails.
3. Sequence checksums must match the screened construct.

## Do not

- Generate or “fix” sequence for synthesis from the LLM.
- Skip screening (`screen-sequence`) and dual-use checks.

## Human

A human approves any synthesis order. Failed checks are not overridable by the agent.
