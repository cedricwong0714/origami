# Team constructs

## Purpose
Store amino-acid strings the team pasted for the CaM–M13 CTPR series. ORIGAMI does not invent these sequences.

## Inputs
`team_cam_m13_series.json`: n = 3, 8, 14; CamSol intrinsic scores at a stated pH range 7.4–7.6; architecture flags.

## Outputs
Checksums and export (GenBank / SBOL) of those strings. CamSol values are dry (`fidelity: 0`) solubility scores. `calibrated` stays false.

## Assumptions
The strings are the designs the team will clone. Junction linker copy number differs on n = 8 (three `GGGGGS`) versus n = 3 and 14 (one `GGGGGS`).

## Known limitations
No DNA sequence is stored. No kit-protocol pH is stored. CamSol is not a wet soluble fraction.

## Parameter sources
None. Sequences are team-supplied.

## Tests
`pytest tests/unit_tests/test_software_exports.py`

## Owner
Dry-lab / math chassis.
