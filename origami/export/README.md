# Export and interchange

## Purpose
Turn a team sequence or a chassis evaluation into files other tools can open: protein GenBank, SBOL 3 XML, SBML, a JSON passport, a batch CSV table, and a labelled synthetic fixture.

## Scientific basis
Kinetics SBML restates equations already in `origami.physical.recruitment`, `origami.kinetics.covalent`, and `origami.kinetics.nanobit`. Sequence files restates team-supplied amino acids. PDB plugin restates C-alpha Rg from an uploaded file using the same sphere formula as `scripts/derive_payload_radii.py`.

## Inputs
Repeat count, optional kinetics body, optional PDB text, optional plate CSV.

## Outputs
Text files and JSON. `calibrated` is false.

## Assumptions
The team sequences in `data/constructs/team_cam_m13_series.json` are the intended wet constructs. CTPR+LgBiT CamSol pH curves are validation-only and are not in that table.

## Known limitations
No DNA. No SynBioHub upload. No custom ODE compiler. PDB upload does not replace the deposited CTPR screw. CamSol scores are dry.

## Parameter sources
Rates come from existing prior slots or the caller. Sequences come from the team table.

## Tests
`pytest tests/unit_tests/test_software_exports.py`

## Owner
Dry-lab / math chassis.
