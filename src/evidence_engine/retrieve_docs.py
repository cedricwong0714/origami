"""Deterministic keyword-overlap document retrieval (no network, no embeddings)."""

from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?", re.IGNORECASE)

# Scores at or below this threshold require human review (heuristic for MVP).
_LOW_SCORE_THRESHOLD = 0.25


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")}


def retrieve_docs(query: str, corpus: list[dict]) -> dict:
    """Rank corpus items by keyword overlap with ``query``.

    Each corpus item is expected to include ``source_id``, ``title``,
    ``authors``, ``year``, ``doi``, and ``text``. Optional ``score`` is ignored
    as a ranking input so retrieval stays deterministic from text overlap.

    Returns
    -------
    dict
        ``chunks``: cited dicts with ``source_id``, ``extracted_passage``, ``score``.
        ``confidence``: float in [0, 1] (max overlap score, or 0 if none).
        ``human_review_required``: True when max score is low or no overlap.
        ``insufficient_evidence``: True when the corpus is empty or no tokens overlap.
    """
    query_tokens = _tokens(query)
    if not corpus or not query_tokens:
        return {
            "chunks": [],
            "confidence": 0.0,
            "human_review_required": True,
            "insufficient_evidence": True,
        }

    scored: list[dict[str, Any]] = []
    for item in corpus:
        text = str(item.get("text") or "")
        title = str(item.get("title") or "")
        blob = f"{title} {text}"
        doc_tokens = _tokens(blob)
        overlap = query_tokens & doc_tokens
        if not overlap:
            continue
        score = len(overlap) / float(len(query_tokens))
        score = min(1.0, max(0.0, score))
        scored.append(
            {
                "source_id": item.get("source_id"),
                "extracted_passage": text,
                "score": score,
            }
        )

    scored.sort(key=lambda row: (-float(row["score"]), str(row.get("source_id") or "")))

    if not scored:
        return {
            "chunks": [],
            "confidence": 0.0,
            "human_review_required": True,
            "insufficient_evidence": True,
        }

    max_score = float(scored[0]["score"])
    return {
        "chunks": scored,
        "confidence": max_score,
        "human_review_required": max_score <= _LOW_SCORE_THRESHOLD,
        "insufficient_evidence": False,
    }
