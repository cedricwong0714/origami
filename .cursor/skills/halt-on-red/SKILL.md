---
name: halt-on-red
description: Halts downstream processing when verification or biosecurity is red. Use whenever a coded check has failed and export, synthesis, or prediction shipping is requested.
disable-model-invocation: true
---

# halt-on-red

SAFETY-CRITICAL. Implement/call the pure Python function; NEVER use an LLM as final authority for this check.

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/verification/halt_on_red.py::halt_on_red`. If the function says halt, stop. No narrative override.

## When

- Any verification layer, dual-use, sequence screen, or MoClo validate failed.
- User asks to export anyway.

## Do

1. Pass aggregated check results into `halt_on_red`.
2. If halt: do not export sequence, order files, or “clean” passports.
3. Return the function’s halt reason unchanged.

## Do not

- Continue “just this once.”
- Soften a red result in the UI copy.

## Human

Only a human can decide to redesign or, under separate process, change gates. The agent must remain halted.
