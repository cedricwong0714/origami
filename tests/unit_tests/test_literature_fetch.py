"""Literature fetch uses Crossref JSON fixtures, not invented papers."""

from __future__ import annotations

import json

from origami.literature.fetch import fetch_crossref, normalize_doi, search_crossref


class _Resp:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode()

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1101/cshperspect.a033845") == (
        "10.1101/cshperspect.a033845"
    )


def test_fetch_crossref_parses_message(monkeypatch):
    def fake_open(req, timeout=20.0):
        return _Resp(
            {
                "message": {
                    "DOI": "10.1101/cshperspect.a033845",
                    "title": ["Protein Solubility Predictions Using the CamSol Method"],
                    "author": [{"given": "Pietro", "family": "Sormanni"}],
                    "container-title": ["Cold Spring Harbor Perspectives in Biology"],
                    "issued": {"date-parts": [[2019]]},
                    "type": "journal-article",
                    "abstract": None,
                }
            }
        )

    monkeypatch.setattr("origami.literature.fetch.urllib.request.urlopen", fake_open)
    rec = fetch_crossref("10.1101/cshperspect.a033845")
    assert rec["year"] == 2019
    assert rec["doi"] == "10.1101/cshperspect.a033845"
    assert rec["calibrated"] is False
    assert "Sormanni" in rec["authors"][0]


def test_search_hits_are_not_priors(monkeypatch):
    def fake_open(req, timeout=20.0):
        return _Resp(
            {
                "message": {
                    "items": [
                        {
                            "DOI": "10.0000/example",
                            "title": ["Not a rate table"],
                            "author": [],
                            "issued": {"date-parts": [[2000]]},
                            "container-title": ["Example"],
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr("origami.literature.fetch.urllib.request.urlopen", fake_open)
    hits = search_crossref("calmodulin M13 kon")
    assert hits[0]["usable_as_prior"] is False
    assert hits[0]["calibrated"] is False
