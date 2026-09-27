"""Deterministic citation support checks (string matching only)."""

from __future__ import annotations

import re

_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9.])[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9.])")


def _normalize_doi(token: str) -> str:
    return token.rstrip(").,;:")


def _passage_blob(retrieved_passages: list[dict]) -> str:
    parts: list[str] = []
    for item in retrieved_passages:
        for key in ("extracted_passage", "text", "doi", "source_id", "title"):
            value = item.get(key)
            if value is None:
                continue
            parts.append(str(value))
    return " ".join(parts)


def check_citation(answer: str, retrieved_passages: list[dict]) -> dict:
    """Classify claims in ``answer`` as supported or unsupported by passages.

    Unsupported if:
    - the answer contains a DOI-like token that does not appear in the passages, or
    - the answer claims a numeric token that does not appear in the passages.

    Matching is deterministic substring / token equality (case-insensitive for DOIs).
    """
    blob = _passage_blob(retrieved_passages)
    blob_lower = blob.lower()

    unsupported: list[str] = []
    supported: list[str] = []

    dois_in_answer = [_normalize_doi(d) for d in _DOI_RE.findall(answer or "")]
    doi_spans = " ".join(dois_in_answer)
    for doi in dois_in_answer:
        if doi.lower() in blob_lower:
            supported.append(doi)
        else:
            unsupported.append(doi)

    numbers_in_answer = _NUMBER_RE.findall(answer or "")
    for num in numbers_in_answer:
        if num in doi_spans:
            continue
        if num in blob:
            supported.append(num)
        else:
            unsupported.append(num)

    return {
        "supported": supported,
        "unsupported": unsupported,
        "is_supported": len(unsupported) == 0,
    }
