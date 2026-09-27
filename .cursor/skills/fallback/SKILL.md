---
name: fallback
description: Selects the next honest fallback when retrieval, models, or LLM synthesis fail. Use instead of inventing a confident wrong answer.
disable-model-invocation: true
---

# fallback

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/compliance/fallback_path.py::fallback`. Fallback level and payload come from that function.

## When

- Retriever, predictor, solver, or synthesis is unavailable or low-confidence.
- Prefer known-good reference over a bogus prediction.

## Do

1. Call `fallback` with failure type and available artifacts.
2. Return retrieved passages, static docs pointers, or closest known-good design as the function specifies.
3. Set human_review_required as returned. Do not label fallback as a prediction for the requested design.

## Do not

- Fill gaps from training memory without the function’s memory-fallback path (default: off).
- Produce a confident number when the model failed.

## Human

A human chooses the next experiment or literature search after a fallback.
