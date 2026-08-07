"""Graceful degradation when components fail (AGENTS.md §13)."""

from __future__ import annotations


class FallbackHierarchy:
    """
    Prefer honest failure over confident wrong answers.
    Levels 1–5 documented in AGENTS.md §13.
    """

    @staticmethod
    def handle_llm_failure(query: str, retrieved_passages: list[dict]) -> dict:
        if retrieved_passages:
            return {
                "answer": (
                    "The language model is currently unavailable. "
                    "Here are the most relevant retrieved passages:"
                ),
                "passages": retrieved_passages,
                "fallback_level": 2,
                "human_review_required": True,
            }
        return {
            "answer": (
                "Both the language model and retrieval system are unavailable. "
                "Please consult the documentation directly or perform a manual "
                "literature search."
            ),
            "fallback_level": 5,
            "human_review_required": True,
        }
