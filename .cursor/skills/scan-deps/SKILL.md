---
name: scan-deps
description: Scans project dependencies for policy and integrity issues via the compliance scanner. Use before adding packages or when auditing the lockfile.
disable-model-invocation: true
---

# scan-deps

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/compliance/scan_deps.py::scan_deps`. Do not declare the tree clean from memory.

## When

- Considering a new dependency (still requires human approval to add).
- Auditing existing pins.

## Do

1. Run `scan_deps` and report findings as returned.
2. Do not add dependencies from this skill; only report.

## Do not

- Quietly edit environment or CI config.
- Ignore scanner hits because a package is “common.”

## Human

A human approves any new dependency and any exception to scanner findings.
