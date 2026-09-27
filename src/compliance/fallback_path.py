"""Honest fallback pointer when a component fails. No confident substitute model."""

from __future__ import annotations


def fallback(failure: dict) -> dict:
    """Return a fallback path and always require human review.

    If ``known_good_id`` is present, ``fallback_path`` points at that known-good
    design id. Otherwise the path is an explicit failure pointer.
    """
    known = failure.get("known_good_id")
    if known:
        path = f"known-good:{known}"
    else:
        path = "explicit-failure:consult-documentation"
    return {
        "fallback_path": path,
        "human_review_required": True,
        "prediction": None,
    }
