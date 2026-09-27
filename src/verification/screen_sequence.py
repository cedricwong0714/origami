"""Deterministic sequence alphabet and forbidden-site screening. Never uses an LLM."""

from __future__ import annotations

from typing import Literal

from src.compliance.sequence_integrity import COMMON_FORBIDDEN_SITES, check_forbidden_sites

_DNA_ALPHABET = frozenset("ATCGatcgNn")
_PROTEIN_ALPHABET = frozenset("ACDEFGHIKLMNPQRSTVWYacdefghiklmnpqrstvwyXx*")


def screen_sequence(sequence: str, kind: Literal["dna", "protein"]) -> dict:
    """Screen a DNA or protein string for alphabet validity and DNA forbidden sites.

    Parameters
    ----------
    sequence:
        Caller-supplied sequence. Must not be generated here.
    kind:
        ``dna`` or ``protein``.

    Returns
    -------
    dict
        ``status`` is ``pass``, ``block``, or ``flag``; ``reasons`` is a list of
        strings. Empty or invalid alphabet yields ``block``. DNA forbidden
        restriction motifs (from ``COMMON_FORBIDDEN_SITES``) yield ``flag``.
    """
    reasons: list[str] = []
    if not sequence or not str(sequence).strip():
        return {"status": "block", "reasons": ["empty sequence"]}

    text = str(sequence)
    if kind == "dna":
        invalid = sorted({c for c in text if c not in _DNA_ALPHABET})
        if invalid:
            return {
                "status": "block",
                "reasons": [f"invalid DNA alphabet characters: {invalid}"],
            }
        site_result = check_forbidden_sites(text, forbidden_sites=COMMON_FORBIDDEN_SITES)
        if not site_result.passed:
            names = sorted(site_result.found_sites.keys())
            reasons.append(f"forbidden restriction sites: {names}")
            return {"status": "flag", "reasons": reasons}
        return {"status": "pass", "reasons": []}

    if kind == "protein":
        invalid = sorted({c for c in text if c not in _PROTEIN_ALPHABET and not c.isspace()})
        if invalid:
            return {
                "status": "block",
                "reasons": [f"invalid protein alphabet characters: {invalid}"],
            }
        return {"status": "pass", "reasons": []}

    return {"status": "block", "reasons": [f"unknown sequence kind: {kind}"]}
