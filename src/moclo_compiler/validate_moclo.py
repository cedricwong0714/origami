"""MoClo field validation. Does not generate or concatenate sequences."""

from __future__ import annotations


def validate_moclo(construct: dict) -> list[str]:
    """Return errors for missing parts or overhangs that are not 4 bp.

    Expects ``part_ids`` (non-empty list) and ``overhang_5`` / ``overhang_3``
    strings of length 4. Does not invent DNA.
    """
    errors: list[str] = []
    part_ids = construct.get("part_ids")
    if not part_ids:
        errors.append("missing parts")
    overhang_5 = construct.get("overhang_5")
    overhang_3 = construct.get("overhang_3")
    if overhang_5 is None:
        errors.append("overhang_5 missing")
    elif len(str(overhang_5)) != 4:
        errors.append("overhang_5 length != 4")
    if overhang_3 is None:
        errors.append("overhang_3 missing")
    elif len(str(overhang_3)) != 4:
        errors.append("overhang_3 length != 4")
    return errors
