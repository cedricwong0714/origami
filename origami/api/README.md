# Structural analysis API

## Purpose

HTTP wrapper around payload-free CTPR screw measurements for the wiki UI.
It calls `backbone_constructs`, `backbone_library`, and `structural_report`.
It does not place enzyme spheres and it does not compute clash or \(C_{\mathrm{eff}}\).

## Scientific basis

Canonical screw from deposited 2AVP / 2HYZ / 2FO7 Cα (Kajander et al. 2007,
DOI 10.1107/S0907444907024353). Persistence length 15 nm is the project
cutoff, not a retrieved value. `(GGGGS)3` RMS is the existing linker prior
and is used only as a comparison window, labelled as such.

## Inputs

- `n`: comma-separated integers in [3, 24]. Default `3,8,14`.

## Outputs

JSON with screw invariants, per-n constructs, deposited step table, helix
traces, and derived readings. `calibrated` is always false.

## Assumptions

The measured block is the CTPR screw. FL, spacers, SpyCatcher, flx, and
LgBiT have no lengths here.

## Known limitations

Cα trace only. No side chains. End chord is not a SpyCatcher-to-LgBiT
distance. Passing a test is not scientific validation.

## Parameter sources

`origami/priors.py`, `origami/physical/deposited.py`, `origami/linker_prior.py`.

## Tests

```bash
python -m pytest tests/unit_tests/test_structural_api.py
```

## Owner

Hong Kong team by Wong Shun Hei, Cheuk Mivon, and Fong Ming. ORIGAMI software.
