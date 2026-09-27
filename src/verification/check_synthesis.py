"""Synthesis-feasibility flags from local construct metadata. No vendor calls."""

from __future__ import annotations


def check_synthesis(construct: dict) -> dict:
    """Return ``pass`` or ``flag`` for synthesis screening.

    Flags length greater than 10_000 nt when ``length`` or ``length_nt`` is
    given, or when ``biosecurity_status`` is present and not ``pass``.
    """
    reasons: list[str] = []
    length = construct.get("length")
    if length is None:
        length = construct.get("length_nt")
    if length is not None:
        try:
            if int(length) > 10_000:
                reasons.append("sequence length exceeds 10000 nt")
        except (TypeError, ValueError):
            reasons.append("length is not an integer")

    bio = construct.get("biosecurity_status")
    if bio is not None and str(bio) != "pass":
        reasons.append(f"biosecurity_status is {bio}")

    if reasons:
        return {"status": "flag", "reasons": reasons}
    return {"status": "pass", "reasons": []}
