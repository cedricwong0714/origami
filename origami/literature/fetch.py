"""Fetch paper metadata from Crossref and Europe PMC.

This is not a chatbot. It does not invent DOIs or rates.
It does not download publisher PDFs.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = (
    "ORIGAMI-ISEF-Hong Kong team/0.1 "
    "(https://gitlab.ISEF.org/2026/software/hong-kong-team/origami; "
    "literature-metadata-only)"
)
CROSSREF = "https://api.crossref.org/works"
EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "literature" / "retrieved"
_DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


class LiteratureFetchError(ValueError):
    """The DOI or query cannot be fetched."""


def _http_json(url: str, timeout: float = 20.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise LiteratureFetchError(f"network error: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LiteratureFetchError("response was not JSON") from exc
    if not isinstance(data, dict):
        raise LiteratureFetchError("response JSON was not an object")
    return data


def normalize_doi(doi: str) -> str:
    token = doi.strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
    token = token.strip("/")
    if not _DOI_RE.match(token):
        raise LiteratureFetchError(f"not a DOI: {doi!r}")
    return token


def fetch_crossref(doi: str) -> dict[str, Any]:
    token = normalize_doi(doi)
    url = f"{CROSSREF}/{urllib.parse.quote(token)}"
    payload = _http_json(url)
    message = payload.get("message")
    if not isinstance(message, dict):
        raise LiteratureFetchError(f"Crossref had no work for {token}")
    authors = []
    for person in message.get("author") or []:
        given = person.get("given") or ""
        family = person.get("family") or ""
        authors.append(" ".join(part for part in (given, family) if part))
    year = None
    issued = (message.get("issued") or {}).get("date-parts") or [[]]
    if issued and issued[0]:
        year = issued[0][0]
    return {
        "doi": token,
        "title": " ".join(message.get("title") or []),
        "authors": authors,
        "container": " ".join(message.get("container-title") or []),
        "year": year,
        "type": message.get("type"),
        "abstract": message.get("abstract"),
        "url": f"https://doi.org/{token}",
        "source": "crossref",
        "calibrated": False,
    }


def fetch_europe_pmc(doi: str) -> dict[str, Any] | None:
    token = normalize_doi(doi)
    query = urllib.parse.urlencode(
        {
            "query": f"DOI:{token}",
            "format": "json",
            "resultType": "core",
            "pageSize": 1,
        }
    )
    payload = _http_json(f"{EUROPE_PMC}?{query}")
    hits = ((payload.get("resultList") or {}).get("result")) or []
    if not hits:
        return None
    hit = hits[0]
    return {
        "doi": token,
        "title": hit.get("title"),
        "authors": hit.get("authorString"),
        "year": hit.get("pubYear"),
        "abstract": hit.get("abstractText"),
        "pmid": hit.get("pmid"),
        "pmcid": hit.get("pmcid"),
        "is_open_access": hit.get("isOpenAccess"),
        "source": "europe_pmc",
        "calibrated": False,
    }


def search_crossref(query: str, rows: int = 5) -> list[dict[str, Any]]:
    if not query.strip():
        raise LiteratureFetchError("query is empty")
    params = urllib.parse.urlencode({"query": query.strip(), "rows": max(1, min(int(rows), 10))})
    payload = _http_json(f"{CROSSREF}?{params}")
    items = ((payload.get("message") or {}).get("items")) or []
    out: list[dict[str, Any]] = []
    for message in items:
        doi = message.get("DOI")
        if not doi:
            continue
        authors = []
        for person in message.get("author") or []:
            given = person.get("given") or ""
            family = person.get("family") or ""
            authors.append(" ".join(part for part in (given, family) if part))
        year = None
        issued = (message.get("issued") or {}).get("date-parts") or [[]]
        if issued and issued[0]:
            year = issued[0][0]
        out.append(
            {
                "doi": doi,
                "title": " ".join(message.get("title") or []),
                "authors": authors,
                "year": year,
                "container": " ".join(message.get("container-title") or []),
                "url": f"https://doi.org/{doi}",
                "source": "crossref_search",
                "calibrated": False,
                "usable_as_prior": False,
                "note": "Search hit only. A title match is not a sourced rate.",
            }
        )
    return out


def save_record(record: dict[str, Any], directory: Path | None = None) -> Path:
    folder = Path(directory) if directory is not None else OUT_DIR
    folder.mkdir(parents=True, exist_ok=True)
    doi = str(record.get("doi") or "unknown").replace("/", "_")
    path = folder / f"{doi}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def fetch_and_store(doi: str, directory: Path | None = None) -> dict[str, Any]:
    """Crossref bibliographic record, plus Europe PMC abstract when present."""
    record = fetch_crossref(doi)
    epmc = fetch_europe_pmc(doi)
    if epmc and epmc.get("abstract"):
        record["europe_pmc_abstract"] = epmc["abstract"]
        record["pmid"] = epmc.get("pmid")
        record["pmcid"] = epmc.get("pmcid")
    path = save_record(record, directory)
    record["stored_path"] = str(path)
    return record
