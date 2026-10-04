"""The Vercel modelling page is a saved chassis lookup, not a live engine."""

from __future__ import annotations

import json
from pathlib import Path

SNAP = Path("web/modelling-static/snapshot.json")


def test_modelling_snapshot_matches_n8_graft() -> None:
    snap = json.loads(SNAP.read_text())
    assert snap["n8"]["indices"] == [0, 3]
    assert snap["n8"]["clash_computable"] is False
    assert snap["n8_with_2bbm_radii"]["clash_computable"] is True
    kd = snap["bound_fraction_at_1e-8_M"]["kd_M"]
    theta = 1e-8 / (1e-8 + kd)
    assert theta == snap["bound_fraction_at_1e-8_M"]["theta_ss"]
    assert snap["next_length_empty_readings"]["next_n"] == 9
    assert len(snap["series"]) == 22
