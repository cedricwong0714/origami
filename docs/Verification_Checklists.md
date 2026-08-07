# Verification Checklists

Standards for dry-lab data ingestion, design verification, and pre-wiki release checks in ORIGAMI / CLASP.

Use these lists before promoting a number into:

- the evidence store (`src/evidence_engine/`)  
- Learn Mode training  
- a Proximity Design Passport  
- the team wiki  

---

## A. Design verification (software)

Run automatically via `src/verification/engine.py` and Design Mode.

- [ ] MoClo overhang continuity (`assemble_level1_vector`)  
- [ ] Docking positions within `[1, repeat_count]`  
- [ ] ODE integration completes without exception  
- [ ] Mechanism profile `validate_inputs` returns no errors  
- [ ] All `part_id`s on `approved_parts.json`  
- [ ] Expression plan is not solo **pET28a+**  
- [ ] Passport generated with evidence-maturity label  

Command smoke test:

```bash
pytest tests/unit_tests/test_verification.py tests/unit_tests/test_profiles_modes_compiler.py -q
```

---

## B. Physical / numerical invariants

- [ ] Concentrations remain non-negative over the simulated horizon  
- [ ] Intermediate-transfer mass accounting documented (substrate / intermediate / product)  
- [ ] CTPR constants unchanged unless a human-approved literature update is logged  
- [ ] NanoBiT distance claims respect ≤ 3.0 nm reconstitution rule  
- [ ] Uncertainty intervals are not narrower than the evidence tier allows  

```bash
pytest tests/physical_invariants -q
```

---

## C. Evidence ingestion (Explore Mode corpus)

Before adding or updating an `EvidenceEntry`:

- [ ] `parameter_key` is stable and documented  
- [ ] Numeric `value` + `unit` present  
- [ ] `confidence_score` ∈ [0, 1] justified  
- [ ] `experimental_context` states assay system (host, T, purified vs lysate)  
- [ ] Citation has title, authors, journal, year, and DOI **or** PMID  
- [ ] Source was read by a human (not LLM-only)  
- [ ] Direct CLASP measurement vs literature inference is labeled correctly  
- [ ] Contradictory prior entries are flagged, not silently overwritten  

Refusal rule: if confidence &lt; project threshold, Explore Mode must return insufficient evidence.

---

## D. Experimental time-series → Learn Mode

- [ ] Time grid and product series lengths match  
- [ ] Blank / negative controls recorded alongside the series  
- [ ] Units match the profile’s primary metric  
- [ ] Mechanism profile ID stored with the dataset  
- [ ] Instrument, buffer, temperature, biological replicate ID in metadata  
- [ ] RMSE / residual summary reviewed by a human before wiki use  
- [ ] Next-experiment suggestions treated as **proposals**, not orders  

---

## E. Sequence / compiler release gate

- [ ] Short parts with `sequence_status: verified_short_part` pass SHA-256 checksum  
- [ ] `reference_only` ORFs have provenance notes; no invented coding sequences  
- [ ] Coexpression strategy is `dual_cassette`, `dual_plasmid`, or reviewed `operon`  
- [ ] Dual-use / payload scope reviewed against allowlist intent  
- [ ] GenBank draft watermarked as *draft / not ordered* until human sign-off  

---

## F. Pre-wiki / judging freeze

- [ ] `pytest` green on `main` (GitLab CI)  
- [ ] README install path works on a clean machine  
- [ ] No secrets, API keys, or unpublished third-party data in the repo  
- [ ] Claims match evidence tier (no “validated diagnostic” language without support)  
- [ ] Zenodo DOIs linked from README for large datasets (when available)  
- [ ] Attributions form updated for software contributors  

---

## Related code

| Checklist | Code |
|-----------|------|
| A | `src/verification/`, `src/ui/design_mode.py` |
| B | `tests/physical_invariants/` |
| C | `src/evidence_engine/`, `src/ui/explore_mode.py` |
| D | `src/ui/learn_mode.py`, `src/data_ingestion/learn_timeseries.py`, `data/stage1_ingestion/templates/`, `src/gp_model/` |
| E | `src/compiler/` |
| F | `.gitlab-ci.yml`, `README.md` |
