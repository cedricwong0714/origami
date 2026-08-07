# ORIGAMI UI / UX Guide

**Explore · Design · Learn**

This guide describes the three ORIGAMI operating modes as implemented in `src/ui/`.  
It is a software UX contract for contributors and judges — not a wet-lab protocol.

---

## Design principles

1. **One job per mode** — do not mix evidence retrieval, design compilation, and model updating in a single opaque call.  
2. **Show uncertainty** — every prediction carries a CI / maturity label.  
3. **Refuse honestly** — insufficient evidence is a valid answer.  
4. **Mechanism-aware** — the UI must name which profile is active; never a universal proximity score alone.  
5. **Biosecurity visible** — allowlist / expression failures are first-class errors, not silent skips.

---

## Mode 1 — Explore

**Entrypoint:** `src/ui/explore_mode.py` → `ExploreMode.ask` / `explore()`

**User intent:** “What evidence exists for parameter *X*?”

**Flow:**

1. User supplies a `parameter_key` (optionally a PubMed fallback for metadata).  
2. ORIGAMI queries the local evidence store.  
3. Result is classified as `direct_evidence`, `model_inference`, or `unsupported`.  
4. If unsupported / low confidence → status `INSUFFICIENT_EVIDENCE` with the fixed refusal string.

**UX must show:**

- Evidence class (direct vs inference)  
- Citation fields when present  
- Confidence score  
- Explicit refusal — never a fabricated citation

**Do not:** auto-invent parameter values to “be helpful.”

---

## Mode 2 — Design

**Entrypoint:** `src/ui/design_mode.py` → `DesignMode.run` / `design()`

**User intent:** “Turn this biological objective into a geometry, prediction, and construct check.”

**Flow:**

1. Validate inputs against the selected **mechanism profile**  
2. Run shared physical engine (CTPR geometry, linker C_eff, recruitment, sterics)  
3. Run profile-specific prediction (ODE / ranking)  
4. Verify MoClo / docking / mass-balance  
5. Check approved-parts allowlist + coexpression plan  
6. Emit a **Proximity Design Passport**

**UX must show:**

- Mechanism profile ID + version  
- Geometry summary (length, docking sites, rigidity)  
- Predicted metric + 95% CI + evidence maturity  
- Required controls and measurements  
- Biosecurity review state (`pass_allowlist` / blocked)  
- Blocking errors vs warnings  

**Hard rejects include:** unknown parts, solo pET28a+ strategy, failed verification layers, profile input errors.

**Soft warnings (MVP):** steric clashes flagged for human review; reference-only ORF sequences pending deposit.

---

## Mode 3 — Learn

**Entrypoint:** `src/ui/learn_mode.py` → `LearnMode.run` / `learn()`

**User intent:** “I have time-series product data — update the discrepancy model and tell me what to measure next.”

**Flow:**

1. Simulate mechanistic ODE baseline for the active profile  
2. Fit GP correction residual (observation − baseline)  
3. Report RMSE / max absolute error  
4. Rank next experiments via UCB or EI  

**UX must show:**

- Overlay of ODE baseline vs experimental series vs augmented mean±std  
- Evidence maturity upgraded to Tier 1 only when real data were supplied  
- Top-*k* recommended time points with acquisition scores  
- Reminder of mandatory controls from the active profile  

**Do not:** claim the GP “proves” a molecular mechanism; it corrects residual error with uncertainty.

---

## CLI and dashboard

| Surface | Role |
|---------|------|
| `python -m src.ui.cli` | Headless full pipeline smoke path |
| `src/ui/dashboard_backend.py` | Programmatic controller for future Streamlit / wiki demos |

Streamlit extras are optional (`pip install -e ".[ui]"`). Prefer a local offline demo path for judging.

---

## Accessibility & language

- Prefer plain labels: *Explore evidence*, *Design a CLASP system*, *Learn from data*  
- Avoid clinical “diagnostic” language in the UI chrome for the complementation profile  
- Always link out to passport JSON / downloadable summary for wiki figures  

---

## Related docs

- [`../CLASP Docs.md`](../CLASP%20Docs.md) — product narrative  
- [`Verification_Checklists.md`](Verification_Checklists.md) — data gates before Learn Mode  
- [`../AGENTS.md`](../AGENTS.md) §15 — invariants  
