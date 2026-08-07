# ORIGAMI

**Hong Kong team · ISEF 2026 Software**

Mechanism-aware design engine for **CLASP** (*Conditional Localized Assembly of Synthetic Proteins*).

ORIGAMI does not score every payload with one universal “proximity” heuristic. It uses a **shared physical engine** (scaffold geometry, linker reach, steric accessibility, Ca²⁺–CaM–M13 recruitment) connected to **separate functional models** for four mechanism profiles:

| Profile | Mechanism | Reference use |
|---------|-----------|---------------|
| `trehalose_synthesis` | Intermediate transfer | OtsA → OtsB osmoprotectant pathway |
| `target_complementation` | Target-induced complementation | Cell-free / screening-assay split reporter |
| `redox_transfer` | Redox electron transfer | Organized donor–acceptor pairs |
| `covalent_capture` | Covalent lock | SpyTag / SpyCatcher proximity capture |

Three operating modes:

1. **Explore** — retrieve evidence; refuse when evidence is insufficient  
2. **Design** — geometry → mechanistic prediction → allowlisted construct checks → Proximity Design Passport  
3. **Learn** — compare prediction with data; recommend the next informative experiment  

Repository (judging artifact): [gitlab.ISEF.org/2026/software/hong-kong-team/origami](https://gitlab.ISEF.org/2026/software/hong-kong-team/origami)

> **Using an AI assistant?** Read [.claude/RESPONSIBLE_AI_USE.md](.claude/RESPONSIBLE_AI_USE.md) and [AGENTS.md](AGENTS.md). You remain responsible for every claim and every commit.

## Requirements

- Python **3.10+** (3.12 recommended)
- `pip` / venv

## Installation

```bash
git clone https://gitlab.ISEF.org/2026/software/hong-kong-team/origami.git
cd origami
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -e ".[dev]"
```

Core dependencies are declared in [`pyproject.toml`](pyproject.toml). Optional UI extras (`streamlit`, etc.) live under `[project.optional-dependencies].ui` and [`copilot/requirements.txt`](copilot/requirements.txt).

## Quick start

### Streamlit UI (Explore / Design / Learn)

```bash
pip install -e ".[ui]"
streamlit run app.py
```

Opens a local dashboard with four modes:

1. **Explore evidence** — retrieve parameters or refuse honestly  
2. **Design a CLASP system** — geometry, prediction, passport, allowlist checks  
3. **Optimize CTPR spacing** — rank docking Δi (Tier-3 computational ranking)  
4. **Learn from data** — ODE vs observations + next-experiment suggestions  

Synthetic Learn curves are labeled fixtures — not Tier-1 lab data.

Standalone HTML demo (same palette / corrected ORIGAMI CTPR priors):

```bash
# open locally
web/ctpr_scaffold_optimizer.html
```

**GitLab Pages** (after CI deploy on `main`): project **Deploy → Pages** in GitLab shows the public URL.
Static demos: landing page + CTPR optimizer.

### Validate a Learn Mode data package

```bash
origami validate-learn path/to.csv path/to.metadata.json
```

Uses templates in `data/stage1_ingestion/templates/`. Synthetic example:

```bash
origami validate-learn \
  data/stage1_ingestion/examples/learn_product_timeseries/SYN_LEARN_001.csv \
  data/stage1_ingestion/examples/learn_product_timeseries/SYN_LEARN_001.metadata.json

### Rank CTPR docking spacings (CLI)

```bash
origami optimize --radius-a 45 --radius-b 25 --interaction Metabolic
origami optimize --radius-a 30 --radius-b 30 --interaction Binding --json
```
```

### CLI pipeline (verification → MoClo → ODE → optional GP)

```bash
python -m src.ui.cli --design-id DEMO_001 --chassis E_coli
```

### Explore / Design / Learn (Python API)

```python
from src.core.schema import DesignSpec, ScaffoldSpec, MechanismType, MoCloPart
from src.compiler.expression_vector import ExpressionPlan
from src.ui.explore_mode import explore
from src.ui.design_mode import design
from src.ui.learn_mode import learn
import numpy as np

# Explore — evidence or honest refusal
print(explore("k_cat_OtsA"))

spec = DesignSpec(
    design_id="DEMO_001",
    chassis="E_coli",
    mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
    scaffold=ScaffoldSpec(
        scaffold_id="CTPR5",
        repeat_count=5,
        docking_positions=[1, 3],
    ),
    payload_ids=["OtsA", "OtsB"],
    operating_mode="reversible",
)
parts = [
    MoCloPart(
        part_id="Promoter_J23100",
        overhang_5prime="GGAG",
        overhang_3prime="AATG",
        sequence="TTGACAGCTAGCTCAGTCCTAGGTATAATACTAGT",
    ),
    MoCloPart(
        part_id="RBS_B0034",
        overhang_5prime="AATG",
        overhang_3prime="CGCT",
        sequence="AAAGAGGAGAAA",
    ),
]
plan = ExpressionPlan(
    scaffold_vector_id="vector_pETDuet",
    payload_vector_ids=["vector_dual_plasmid_set"],
    coexpression_strategy="dual_cassette",
)

result = design(spec, parts, expression_plan=plan)
print(result["status"], result["passport"]["mechanism_profile"])

t = np.linspace(0, 100, 40)
exp = 0.8 * (1.0 - np.exp(-0.04 * t))
print(learn(spec, experimental_product=exp)["next_experiment_recommendations"][:1])
```

## Tests

```bash
pytest
```

CI on GitLab runs the same suite (see [`.gitlab-ci.yml`](.gitlab-ci.yml)).

## Repository layout

```
src/
  core/            Shared physical engine (CTPR, Ca²⁺, linkers, NanoBiT, sterics)
  profiles/        Mechanism Profile Standard packages
  ode_model/       Mechanism-specific kinetic solvers
  evidence_engine/ Curated parameter store + retrieval
  compiler/        Approved-parts allowlist + coexpression rules
  moclo_compiler/  Level-1 assembly + GenBank draft
  verification/    Multi-layer design checks
  ui/              Explore / Design / Optimize / Learn + CLI
  scaffold_optimizer/  CTPR Δi spacing ranking
  data_ingestion/  Learn timeseries package loaders
web/               Standalone HTML demos (CTPR optimizer)
models/
  kinetic_models/        Tracked JSON rate priors (loaded by profiles)
  structure_predictions/ AF/ESM summaries (PDBs gitignored → Zenodo)
  benchmarks/            Held-out evaluation index
data/
  stage1_ingestion/      Assay metadata + Learn CSV templates/schema
  stage2_baselines/      Geometry / intracellular baselines + schema
  raw_metadata/          Assay-condition templates
tests/
  unit_tests/
  physical_invariants/
  golden_references/     Regression fixtures for Design Mode
docs/
  ORIGAMI_UI_UX_Guide.md
  Verification_Checklists.md
  DEMO.md                 5-minute judge walkthrough
```

Full platform specification: [`CLASP Docs.md`](CLASP%20Docs.md)  
Dry-lab / SCALE checklist: [`ISEF 2026 Dry Lab Megadoc.md`](ISEF%202026%20Dry%20Lab%20Megadoc.md)

## Biosecurity constraints (software)

- Parts must appear on [`src/compiler/approved_parts.json`](src/compiler/approved_parts.json)
- Large ORFs are allowlisted by **ID + provenance** until checksummed DNA is deposited — ORIGAMI will not invent gene sequences
- Solo **pET28a+** hosting of scaffold + payload is rejected
- Explore Mode refuses answers when evidence confidence is insufficient
- Do not present screening-assay models as clinical diagnostics

## Data and large files

Keep this repository for **source code**. Datasets, model weights, and heavy media belong on [Zenodo](https://teams.ISEF.org/go/deliverables/software/zenodo) with DOIs linked from this README once uploaded.

## Authors

**ISEF 2026 Hong Kong team** — CLASP / ORIGAMI software track.

## License

[Apache License 2.0](LICENSE)
