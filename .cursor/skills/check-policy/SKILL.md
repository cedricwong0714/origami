---
name: check-policy
description: Advises on project policy and responsible-AI rules by calling the policy checker. Use when an action may conflict with AGENTS.md or compliance policy. Advisor only; does not grant permission.
disable-model-invocation: true
---

# check-policy

Advisor only. AI advises. The Python function enforces listing of applicable rules. Humans approve.

This skill does not authorize edits, exports, allowlist changes, or bypasses.

## Authority

Call `src/compliance/check_policy.py::check_policy`. Treat the return as guidance plus coded constraints, not a waiver.

## When

- Agent is about to change signatures, constants, filters, CI, or sequences.
- User asks whether an action is allowed.

## Do

1. Run `check_policy` with the proposed action.
2. If the function says ask-first or never-do, stop and surface that.
3. Remind: humans approve; this skill is not approval.

## Do not

- Use a “policy OK” chat summary to skip verification or biosecurity.
- Modify biosecurity filters or verification layers.

## Human

Only a human can approve policy exceptions. The agent cannot.
