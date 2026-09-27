"""Parse kinetic parameter tokens from paper text. Never invent values."""

from __future__ import annotations

import re

# Names are taken only when they appear next to a numeric value and a unit token.
# Units are matched as written in the source span; no conversion is performed.
_PARAM_RE = re.compile(
    r"(?P<name>kcat|Km|Kd)\s*[:=]?\s*"
    r"(?:of|was|is|=)?\s*"
    r"(?P<value>[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?)\s*"
    r"(?P<units>"
    r"s\^-1|s\^{{-1}}|1/s|s-1|"
    r"µM|μM|uM|nM|mM|pM|M|"
    r"min\^-1|1/min"
    r")",
    re.IGNORECASE,
)


def extract_params(paper_text: str) -> list[dict]:
    """Extract kcat, Km, and Kd only when a value and units appear in the text.

    Each row is ``name``, ``value``, ``units``, ``source_span``.
    If nothing matches, returns an empty list. No defaults, no LLM.
    """
    if not paper_text:
        return []

    rows: list[dict] = []
    for match in _PARAM_RE.finditer(paper_text):
        raw_name = match.group("name")
        canonical = {"kcat": "kcat", "km": "Km", "kd": "Kd"}[raw_name.lower()]
        rows.append(
            {
                "name": canonical,
                "value": float(match.group("value")),
                "units": match.group("units"),
                "source_span": match.group(0),
            }
        )
    return rows
