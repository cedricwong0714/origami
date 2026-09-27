"""Test runner stub. Does not execute untrusted code."""

from __future__ import annotations


def run_tests(code_or_path: str) -> dict:
    """Return a sandboxed result. Does not spawn pytest or eval code.

    Literal marker ``self-check`` yields ``pass``. Any other input yields
    ``fail`` with an instruction to run pytest from CI.
    """
    if code_or_path == "self-check":
        return {"status": "pass", "reason": "self-check marker"}
    return {
        "status": "fail",
        "reason": "execution sandboxed; call pytest from CI",
    }
