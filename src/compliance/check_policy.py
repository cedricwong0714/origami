"""ISEF-oriented policy FLAGS. Advisory only; never halts by itself."""

from __future__ import annotations

_FLAG_HINTS: tuple[tuple[str, str], ...] = (
    ("release", "ISEF: environmental release may require extra review"),
    ("human subject", "ISEF: human-subjects work is restricted"),
    ("animal", "ISEF: vertebrate animal use needs documentation"),
    ("white list", "ISEF: confirm parts are on the white list"),
    ("whitelist", "ISEF: confirm parts are on the white list"),
)


def check_policy(context: dict) -> list[str]:
    """Return advisory ISEF policy flag strings. Does not stop a pipeline.

    Scans string values in ``context`` (and nested simple strings) for
    high-precision hints. Empty list if none match.
    """
    blobs: list[str] = []
    for value in context.values():
        if isinstance(value, str):
            blobs.append(value.lower())
        elif isinstance(value, list):
            blobs.extend(str(item).lower() for item in value)
    joined = " ".join(blobs)
    flags: list[str] = []
    for needle, message in _FLAG_HINTS:
        if needle in joined:
            flags.append(message)
    return flags
