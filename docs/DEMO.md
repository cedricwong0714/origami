# ORIGAMI demo walkthrough (≈5 min for judges)

Software-only demo path — no wet-lab claims.

## Setup

```bash
pip install -e ".[ui]"
streamlit run app.py
```

Optional browser-only CTPR optimizer: open `web/ctpr_scaffold_optimizer.html`.

## 1. Explore evidence (~1 min)

1. Mode: **Explore evidence**
2. Select `k_cat_OtsA` (or another curated key)
3. Show citation fields + confidence
4. Type `made_up_kcat` → show **honest refusal** (no fabricated citation)

## 2. Optimize CTPR spacing (~1 min)

1. Mode: **Optimize CTPR spacing**
2. Default radii + **Metabolic cascade**
3. **Calculate optimum** → table + Φ ranking + ASCII map
4. **Send to Design Mode** → sidebar switches; docking sites pre-filled

Note: Φ is Tier-3 computational ranking, not calibrated fitness.

## 3. Design a CLASP system (~2 min)

1. Confirm pre-fill banner (if from optimizer)
2. **Run Design Mode**
3. Show passport metrics, prediction with 95% CI, geometry plot
4. **Download passport JSON** and **wiki markdown snippet**
5. If time: switch scaffold vector to solo `pET28a+` → biosecurity reject

## 4. Learn from data (~1 min)

1. Mode: **Learn from data**
2. Use **Synthetic demo curve** (labeled fixture)
3. Show ODE vs observation + GP band + next-experiment table
4. Mention Tier-1 path: CSV + metadata from `data/stage1_ingestion/templates/`
5. Or click **Load tracked synthetic example** (SYN_LEARN_001) then **Run Learn Mode**

## What to say out loud

- Mechanism-aware profiles, not one universal proximity score
- Uncertainty and evidence tier on every prediction
- Allowlist + coexpression gates are enforced
- Synthetic fixtures are labeled — not wiki measurements

## CI

```bash
pytest
```

Run `pytest` on your own machine. GitHub does not run a workflow for this repository and does not publish `web/` as a Pages site. Open `web/index.html` locally for the static landing page.
