# ISEF 2026 Dry Lab Megadoc

**Hong Kong team · CLASP / ORIGAMI**

This megadoc is the **operational dry-lab checklist** for measurement, modeling, and how wet-lab outputs enter ORIGAMI.  
Full narrative, equations, and human-practices context live in [`CLASP Docs.md`](CLASP%20Docs.md). Do not treat this file as a substitute for primary data or peer-reviewed sources.

---

## 1. Purpose

Dry lab work must answer three questions before software claims are published:

1. **Is assembly physically plausible?** (geometry, reach, sterics, recruitment)  
2. **What functional mechanism is being claimed?** (one of four ORIGAMI profiles)  
3. **What evidence maturity and uncertainty apply?** (Tier 1 / 2 / 3)

Every number that reaches the wiki or ORIGAMI passport needs: **units, n, uncertainty, and provenance**.

---

## 2. SCALE — measurement standard (summary)

**SCALE** = Standardized Calibration, Assembly, and Luminescence Evaluation.

> SCALE converts CLASP experiments into SI-traceable absolute units with uncertainty budgets, so assembly is measured as molecules per cell (or per OD) — not orphan RLU.

Authoritative detail: `CLASP Docs.md` § SCALE.

### 2.1 Absolute metrics to report

1. **AES** — assembled NanoLuc molecules per cell (or per OD)  
2. **EC50** — free Ca²⁺ for half-maximal assembly (µM) ± 95% CI  
3. **Hill n** ± CI  
4. **Dynamic range** (fold)  
5. **Lock retention** (% signal after EGTA)  
6. **Trehalose fold-change** (scaffolded / free) ± CI  
7. **Solubility %**  
8. **SpyCatcher conversion %** at a fixed time (e.g. 10 min)  
9. **Inter-day CV** of AES  
10. **Combined standard uncertainty** for every derived quantity  

### 2.2 MVP ladder

| Level | Name | Must have |
|-------|------|-----------|
| **M0** | Lights on | NanoLuc + OD + one ±Ca²⁺ luminescence |
| **M1** | SCALE core | Full Ca²⁺ dose–response + ≥2 negatives + absolute AES + EC50±CI |
| **M2** | SCALE complete | + Spy kinetics + solubility + lock test + uncertainty budget + SOP |
| **M3** | SCALE+ | + CTPR geometry series (3 lengths) + trehalose dual readout + inter-day CV |

**Do M1 no matter what.** Add M2 as pieces finish. Attempt M3 only if CTPR and Ots constructs exist.

### 2.3 Fixed experimental constraints (lean rules)

1. One host, one media, one lysis method for all SCALE data  
2. One master expression day → frozen lysates when possible  
3. Every plate: blanks, negatives, and a standard  
4. No orphan numbers — units, n, uncertainty  
5. Geometry series is **3 points**, not 20  
6. Trehalose validates **function**; it does not redefine assembly  

### 2.4 Mandatory controls (never skip)

- No Ca²⁺  
- Scrambled docking  
- Dead / inactive CaM  
- No scaffold  
- Reporter halves alone  
- Free enzymes (for trehalose assays)

---

## 3. How SCALE feeds ORIGAMI

| SCALE output | ORIGAMI use |
|--------------|-------------|
| NanoLuc + OD curves | Unit layer / calibration |
| Spy kinetics | Locking submodel prior |
| Solubility | Expression / burden penalty |
| Ca²⁺ dose–response | Primary calibration target |
| Negatives | Specificity constraint |
| AES absolute | Training / residual GP target |
| Trehalose fold | Functional validation (not AES training) |
| Uncertainty | Displayed on every prediction |
| Geometry series | Tests spacing hypotheses |

Software entry points:

- Explore → `src/ui/explore_mode.py`  
- Design / passport → `src/ui/design_mode.py`  
- Learn / next experiment → `src/ui/learn_mode.py`  
- Ingestion checklists → [`docs/Verification_Checklists.md`](docs/Verification_Checklists.md)

---

## 4. Modeling checklist (pre-pipette and post-data)

### Before wet lab

- [ ] Mechanism profile selected and justified  
- [ ] Scaffold repeat count + docking positions recorded  
- [ ] Damköhler / channeling or distance hypothesis stated  
- [ ] Predictions frozen (timestamped) before looking at key results  
- [ ] Evidence maturity labeled Tier 2 or Tier 3 (not “validated”)

### After wet lab

- [ ] Raw files archived with metadata (buffer, T, instrument)  
- [ ] Conversion equations documented  
- [ ] Prediction vs observation compared in Learn Mode or equivalent  
- [ ] Model revisions logged (what changed and why)  
- [ ] Passport / wiki figures use absolute units where claimed  

---

## 5. Reporting standards for the wiki

Minimum figure set for measurement claims:

- Standard curves  
- Dose–response with fit + CI band  
- Control bar plot  
- AES in absolute units  
- Residual / prediction–observation plot  
- Uncertainty budget table  
- Optional: geometry series bar plot  

Language rules:

- Prefer **screening-assay proof of concept** over “diagnostic” unless clinical validation exists  
- Prefer **relative ranking** over absolute H₂ titre for redox until calibrated  
- Never present AI-generated numbers as measured data  

---

## 6. Related documents

- [`CLASP Docs.md`](CLASP%20Docs.md) — full specification  
- [`docs/ORIGAMI_UI_UX_Guide.md`](docs/ORIGAMI_UI_UX_Guide.md) — software modes  
- [`docs/Verification_Checklists.md`](docs/Verification_Checklists.md) — data ingestion gates  
- [`AGENTS.md`](AGENTS.md) §15 — software invariants for AI/human contributors  
