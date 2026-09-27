"""String-matching dual-use screen. Never uses an LLM."""

from __future__ import annotations

# High-precision block phrases. Matching is case-insensitive substring search.
DUAL_USE_BLOCK_KEYWORDS: tuple[str, ...] = (
    "weaponize",
    "weaponise",
    "virulence enhancement",
    "enhance virulence",
    "evade detection",
    "bypass biosecurity",
    "gain of function pathogen",
)


def check_dual_use(request_text: str, allowlist: frozenset[str] | None = None) -> dict:
    """Allow or refuse a request using frozen keyword matching only.

    Default allowlist is empty. If the request contains an allowlist token
    (exact case-insensitive token presence as a substring) and no block
    keywords, status is ``allow``. Block keywords always produce ``refuse``.
    """
    allowed = allowlist if allowlist is not None else frozenset()
    text = request_text.lower()
    for phrase in DUAL_USE_BLOCK_KEYWORDS:
        if phrase.lower() in text:
            return {"status": "refuse", "reasons": [f"blocked keyword: {phrase}"]}
    if allowed:
        for token in allowed:
            if token.lower() in text:
                return {"status": "allow", "reasons": ["allowlist token matched"]}
        return {"status": "refuse", "reasons": ["not on allowlist"]}
    return {"status": "allow", "reasons": ["no dual-use keywords"]}
