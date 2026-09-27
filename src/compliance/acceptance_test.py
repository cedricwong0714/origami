"""Acceptance gate stub. Never regenerates plasmids or exports sequences."""

from __future__ import annotations


def acceptance_test(code: str) -> dict:
    """Pass only the known checksum marker. Fail sequence-export requests.

    Passes solely when ``code`` is the literal ``known-plasmid-checksums-ok``.
    Any request to export a sequence fails.
    """
    lowered = code.lower()
    if "export" in lowered and "sequence" in lowered:
        return {"status": "fail", "reason": "sequence export is not allowed here"}
    if code == "known-plasmid-checksums-ok":
        return {"status": "pass", "reason": "known-plasmid-checksums-ok"}
    return {"status": "fail", "reason": "acceptance marker not matched"}
