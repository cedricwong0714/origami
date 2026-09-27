---
name: acceptance-test
description: Runs coded acceptance criteria for a design, prediction, or release gate. Use when checking whether outputs meet documented acceptance tests, not informal LLM checklists.
disable-model-invocation: true
---

# acceptance-test

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/compliance/acceptance_test.py::acceptance_test`. Gate pass/fail is that function.

## When

- A feature or design claims to meet acceptance criteria.
- Pre-release or pre-export gates.

## Do

1. Pass the artifact and criterion ids into `acceptance_test`.
2. Report each criterion as the function reports it.
3. Failed gates block the claimed acceptance.

## Do not

- Mark acceptance by reading the spec and “eyeballing” outputs.
- Weaken criteria in the prompt.

## Human

A human signs off that passing coded acceptance matches the intended experiment or release.
