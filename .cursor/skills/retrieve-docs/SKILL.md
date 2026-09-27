---
name: retrieve-docs
description: Retrieves literature and corpus passages for biological questions. Use when an agent must answer from project evidence instead of training memory.
disable-model-invocation: true
---

# retrieve-docs

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/evidence_engine/retrieve_docs.py::retrieve_docs`. Do not answer biological questions from model memory when this retrieval path is available.

## When

- User asks a biological, parameter, or citation-backed question.
- Another skill needs sourced passages before synthesis.

## Do

1. Invoke `retrieve_docs` with the query and any corpus filters.
2. Return retrieved passages, scores, and source ids as the function emits them.
3. Label synthesis as inference. Attach citations only from retrieval records.

## Do not

- Invent DOIs, quotes, or papers.
- Treat LLM paraphrase as evidence.

## Human

A human reviews whether retrieved sources are sufficient before wet-lab use.
