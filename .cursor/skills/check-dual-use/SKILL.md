---
name: check-dual-use
description: Checks parts and designs against biosecurity allowlists and blocklists. Use before processing, compiling, or exporting any construct. Allowlist/blocklist code is final, not the LLM.
disable-model-invocation: true
---

# check-dual-use

SAFETY-CRITICAL. Implement/call the pure Python function; NEVER use an LLM as final authority for this check. The allowlist/blocklist in code is final, not the model.

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/verification/check_dual_use.py::check_dual_use`. Failed biosecurity must halt export.

## When

- Design includes part ids, sequences, or chassis.
- Before compiler/export.

## Do

1. Run `check_dual_use` on the design spec and library.
2. Treat `blocks_export` / failed checks as hard stops.
3. Do not add parts to the allowlist from this skill.

## Do not

- Bypass, weaken, or “interpret away” a blocklist hit.
- Use LLM judgment to declare a part dual-use or safe.

## Human

A human reviews any fail. Only humans may change allowlists/blocklists.
