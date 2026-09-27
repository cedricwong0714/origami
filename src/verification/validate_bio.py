"""Biological construct field checks. Does not invent sequences or constants."""

from __future__ import annotations

_KNOWN_CHASSIS = frozenset({"e_coli", "yeast", "cell_free", "in_vitro"})


def validate_bio(construct: dict) -> list[str]:
    """Return validation errors for chassis, payloads, and allowlisted parts.

    Expects optional keys: ``chassis``, ``payloads`` (list), ``parts`` (list of
    dicts with ``allowlisted`` boolean). Unknown chassis, missing payloads, or
    a part not marked ``allowlisted`` True produces an error string.
    """
    errors: list[str] = []
    chassis = construct.get("chassis")
    if chassis is None or str(chassis).strip() == "":
        errors.append("chassis missing")
    elif str(chassis) not in _KNOWN_CHASSIS:
        errors.append(f"chassis unknown: {chassis}")

    payloads = construct.get("payloads")
    if payloads is None or payloads == [] or payloads == ():
        errors.append("payloads missing")

    parts = construct.get("parts")
    if parts is None:
        errors.append("parts missing")
    else:
        for index, part in enumerate(parts):
            if not isinstance(part, dict):
                errors.append(f"part[{index}] is not a mapping")
                continue
            if part.get("allowlisted") is not True:
                part_id = part.get("part_id", index)
                errors.append(f"part not allowlisted: {part_id}")
    return errors
