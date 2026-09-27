---
name: log-audit
description: Writes or verifies audit log records for design, prediction, and verification events. Use when an action must be attributable and replayable.
disable-model-invocation: true
---

# log-audit

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/compliance/log_audit.py::log_audit`. The log record is the function’s output, not chat history.

## When

- After verification, prediction, export, or halt.
- Reconstructing who approved what.

## Do

1. Pass event type, actor, artifact ids, checksums, model/dataset versions into `log_audit`.
2. Do not overwrite prior audit files; follow the function’s append/version rules.

## Do not

- Fabricate timestamps or approvers.
- Delete audit records.

## Human

A human confirms the audit trail before treating an export as released.
