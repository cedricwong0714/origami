# Literature fetch

## Purpose
Pull bibliographic metadata for a DOI from Crossref, and an abstract from Europe PMC when one exists. Search hits are titles only. They are not installed as biological priors.

## Scientific basis
None. This is an HTTP client. Numbers in an abstract are not copied into `origami.priors` by this module.

## Inputs
DOI string, or a Crossref query.

## Outputs
JSON under `data/literature/retrieved/`. `calibrated` is false. `usable_as_prior` is false on search hits.

## Assumptions
Crossref and Europe PMC are the allowed endpoints. Publisher PDFs are not downloaded.

## Known limitations
Paywalled full text is absent. A search for k_on does not set recruitment k_on.

## Parameter sources
None created here.

## Tests
`pytest tests/unit_tests/test_literature_fetch.py`

## Owner
Dry-lab / math chassis.
