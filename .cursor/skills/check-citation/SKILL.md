---
name: check-citation
description: Verifies that claimed citations match retrieved source records. Use when an answer cites papers, DOIs, or passages that must be programmatically checked.
disable-model-invocation: true
---

# check-citation

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/evidence_engine/check_citation.py::check_citation`. The function decides whether a citation is attached to a real retrieved record.

## When

- An answer includes authors, year, DOI, or quoted passages.
- Exporting a structured biological answer.

## Do

1. Pass claimed citations and retrieval records into `check_citation`.
2. Drop or flag any citation the function does not confirm.
3. Keep `all_citations_from_retrieval` honest.

## Do not

- Write citations from training memory.
- Repair a failed check by inventing a “close enough” paper.

## Human

A human approves remaining citations before they appear in a report or passport.
