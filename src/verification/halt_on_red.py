"""Hard stop when any check reports red / block / refuse. Never uses an LLM."""

from __future__ import annotations

_STOP_VALUES = frozenset({"red", "block", "refuse"})


def halt_on_red(checks: list[dict]) -> dict:
    """Return ``decision`` ``stop`` or ``proceed``.

    Any check whose ``status`` or ``severity`` is ``red``, ``block``, or
    ``refuse`` yields ``stop``. Otherwise ``proceed``.
    """
    for check in checks:
        status = str(check.get("status", "")).lower()
        severity = str(check.get("severity", "")).lower()
        if status in _STOP_VALUES or severity in _STOP_VALUES:
            return {"decision": "stop", "reasons": ["red-path check failed"]}
    return {"decision": "proceed", "reasons": []}
