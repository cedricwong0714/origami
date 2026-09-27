"""Pinning scan for requirements text. Does not invent CVE identifiers."""

from __future__ import annotations


def scan_deps(requirements_text: str) -> list[dict]:
    """Flag requirement lines that are not pinned with ``==``.

    Empty list if every non-empty, non-comment line contains ``==``.
    Does not look up advisories or invent CVE numbers.
    """
    findings: list[dict] = []
    for line in requirements_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "==" not in stripped:
            findings.append(
                {
                    "package_line": stripped,
                    "issue": "unpinned: missing == version",
                }
            )
    return findings
