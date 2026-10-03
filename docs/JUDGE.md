# ORIGAMI for judges

Hong Kong team, ISEF 2026. This page is the software exhibit for CLASP. It says what the program does, how to run it, and what a screen must not be read as. It is not a wet-lab result.

Repository: https://gitlab.ISEF.org/2026/software/hong-kong-team/origami

Longer operator notes: [USER_MANUAL.md](USER_MANUAL.md). One card per calculator: [MODEL_CARDS.md](MODEL_CARDS.md). HTTP routes: [API.md](API.md). Which numbers still need the lab: [DATA_DEPENDENCY_MATRIX.md](DATA_DEPENDENCY_MATRIX.md).

## What the software is

ORIGAMI is a set of transparent calculators for a consensus-tetratricopeptide-repeat (CTPR) scaffold. A user types a repeat count and, where needed, concentrations or a plate file. The program returns geometry, a literature stability lookup, a docking and clash score, a kinetics time course, and a suggestion for the next measurement.

It is not a black-box model of one fusion protein. It does not generate DNA or protein sequences. It does not mark a design safe to order. Every prediction that rests on literature parameters is returned with `calibrated: false`.

A number on screen is one of three things:

1. A literature value the team can point to (PDB screw, Phillips table, Zakeri rate, and similar).
2. A team assumption that warns when it is used (the recruitment on-rate is the example).
3. A blank field waiting for a measurement this team has not made yet.

## How this fits the project

CLASP needs a way to compare scaffold lengths before and after assays, without hiding which equation ran. ORIGAMI is that record. Structure, stability, docking, and kinetics stay separate. A later luminescence reading does not overwrite the screw or the melting-temperature table. It is stored as an observation and used only in the learning layer.

Other ISEF teams can clone the repository, change the repeat count and the concentrations, and rerun the same functions. The install path below does not depend on a private notebook.

## What a judge can open

**Static demo.** GitLab → Deploy → Pages, on the default branch `main`. That URL is a landing page plus an in-browser CTPR spacing demo. It does not run the Python chassis.

**Full program**, on a computer with Python 3.10+ and Node:

```bash
git clone https://gitlab.ISEF.org/2026/software/hong-kong-team/origami.git
cd origami
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python host_sa.py
```

Second terminal:

```bash
cd web/structural
npm install
npm run dev
```

Open http://127.0.0.1:3000 . The API is http://127.0.0.1:41287/docs .

| Page | What to look at |
|---|---|
| `/` | Contour, axial span, and rigid versus flexible for an integer repeat count from 3 to 24 |
| `/stability` | Phillips 2012 CTPRa lookup. Missing uncertainty stays blank. Lengths past the cited range are marked extrapolated |
| `/stability/calculator` | Gibbs–Helmholtz ΔG(T). Enthalpy and ΔCp are filled only where the table has them |
| `/kinetics` | A time course or occupancy after the user types concentrations |
| `/ssdk` | The four calculators for one length, then the luminescence gate |
| `/learn` | A recommended next repeat count. The sentence on the page says it is the next measurement, not a validated design |
| `/lab` and `/intake` | Empty slots, and a plate CSV import that subtracts blanks and stores a checksum |
| `/guide` | The split between literature, lab-pending fields, and team dry-lab inputs |

Tests: `pytest -q` from the repository root. A green run means the code matches its pinned inputs. It does not mean a construct works in cells.

## How to read a result

- `calibrated: false` means this team has not approved a project dataset for that claim. Literature priors are labelled as literature, not as our assay.
- Luminescence pass/fail uses the lower 95% bound, μ − 1.96σ, against a threshold in `data/config/active_learning_config.json`. That threshold is tagged `unmeasured`. Until the plate-reader coefficient of variation is entered and the tag is changed, a pass is a software demo.
- Two recommenders can name different repeat counts. The default `next_n` is the sklearn Matérn residual on wet luminescence when a wet row exists. `design_engine_next_n` is the older residual Gaussian process and is what you get if the request sets `learner` to `design_engine`, or if there is no wet row (`learner_family` is then `design_engine_fallback`). A batch of up to 12 lengths is ranked by expected improvement per cost, with a penalty when fitted solubility or purity misses the placeholder gate. All of these are suggestions for the next wells.
- The stability calculator’s ΔG at 10 °C is 0.5–5.0 kcal/mol higher than Phillips’ printed ΔG. The difference is pinned by a test and described in the changelog. It is not averaged away.
- n = 17 can be typed and computed. It is not a calibrated design point. The lengths the team treats as the planned series are 3, 8, and 14.
- Checked-in freezes for those three lengths are `data/predictions/frozen/scaffold-n3.json`, `scaffold-n8.json`, and `scaffold-n14.json`. Contour and the Phillips length curve change with n. The luminescence numbers in those files do not, and their ±30% band is a placeholder (`hypothesis_only`, `calibrated: false`).

## What is deliberately unfinished

Measured assay noise, written pass/fail limits on the real RLU scale, and group labels for real plates. Those inputs change the learning layer. They are not invented here. Enzyme assays (OtsA/OtsB), circular dichroism, thermal shift, size-exclusion chromatography, and cryo-EM are out of this team’s wet-lab plan. Stability on those points stays a literature lookup.

## AI tools

Cursor, DeepSeek, and Gemini assisted coding, drafting, and literature triage. The team chose which papers entered the parameter file, rejected numbers that were not in the cited source, and is responsible for the repository and the wiki. The attribution form on the team wiki is the record of that use. This file is not a claim that a model validated the biology.

## A short path through the demo

1. Open `/`. Set the repeat count to 8. Read contour and the rigid/flexible line.
2. Open `/stability`. Confirm the Phillips row is a lookup, and that a length past the table is marked as such.
3. Open `/ssdk`. Run repeat count 8 with kinetics left off, then again with concentrations filled in. Empty kinetics stays empty.
4. Open `/learn` or the gate on `/ssdk`. Enter two synthetic readings. Read the recommended n and the `calibrated: false` line.
5. Open `/guide` for the list of fields that are still waiting on the lab.
