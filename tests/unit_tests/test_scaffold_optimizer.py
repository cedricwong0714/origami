"""CTPR spacing optimizer — geometry invariants and ranking smoke tests."""

import pytest

from src.core.ctpr_geometry import CTPR_RISE_NM, CTPR_TWIST_DEG
from src.scaffold_optimizer import InteractionClass, optimize_ctpr_spacing


def test_optimizer_uses_origami_geometry_constants():
    # Payload radii chosen so ≥1 Δi clears sterics under 45°/repeat twist
    result = optimize_ctpr_spacing(20.0, 20.0, InteractionClass.METABOLIC, km_M=1e-4)
    assert result.geometry_constants["CTPR_RISE_NM"] == CTPR_RISE_NM
    assert result.geometry_constants["CTPR_TWIST_DEG"] == CTPR_TWIST_DEG
    assert result.geometry_constants["CTPR_TWIST_DEG"] == 45.0
    assert result.optimal_delta_i >= 1
    assert result.recommended_scaffold_repeats == result.anchor_repeat + result.optimal_delta_i + 1
    assert len(result.candidates) == 6
    assert any(c.state == "Optimal" for c in result.candidates)
    assert "Tier 3" in result.honesty_note


def test_binding_class_runs():
    result = optimize_ctpr_spacing(30.0, 30.0, InteractionClass.BINDING)
    assert result.interaction_class == InteractionClass.BINDING
    assert result.best_score >= 0.0


def test_rejects_non_positive_radii():
    with pytest.raises(ValueError, match="positive"):
        optimize_ctpr_spacing(0.0, 25.0, InteractionClass.ELECTRON)


def test_static_html_demo_exists_and_uses_origami_priors():
    from src.core.asset_paths import REPO_ROOT

    html = (REPO_ROOT / "web" / "ctpr_scaffold_optimizer.html").read_text(encoding="utf-8")
    assert "1.1 nm" in html or "dz = 11.0" in html
    assert "45.0" in html or "45°" in html
    assert "const theta = 20.0" not in html  # superseded: Kajander 2007 → 45°/repeat
