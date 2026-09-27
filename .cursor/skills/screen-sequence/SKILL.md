---
name: screen-sequence
description: Screens DNA/protein sequences for integrity, forbidden sites, and checksum consistency. Use before any sequence export, assembly, or modification is treated as complete.
disable-model-invocation: true
---

# screen-sequence

SAFETY-CRITICAL. Implement/call the pure Python function; NEVER use an LLM as final authority for this check.

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/verification/screen_sequence.py::screen_sequence`. The boolean/pass-fail from that function is the only screen result.

## When

- After assembly, codon work, or any sequence edit.
- Before GenBank/export.

## Do

1. Pass the sequence and declared expected protein/length into `screen_sequence`.
2. Show diffs for any intentional change. Never silent edits.
3. Halt downstream export if the function fails.

## Do not

- Generate sequences from model memory.
- Override a failed screen with “looks fine.”

## Human

A human approves any sequence that the function flags or that was intentionally modified.
