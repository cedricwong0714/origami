import pytest

from src.predictions.sensitivity import parameter_elasticities


def test_alpha_elasticity_below_one_and_background_dominates_at_zero_signal():
    """R = r0 + alpha*(B + eta*L): scaling alpha scales only the signal part,
    so its elasticity lies in [0, 1], reaching 1 only if r0 is negligible."""
    out = parameter_elasticities(1e-5)
    e = out["elasticities"]
    assert 0.0 <= e["alpha"] <= 1.0 + 1e-6
    assert e["r0"] >= 0.0
    assert e["alpha"] + e["r0"] == pytest.approx(1.0, abs=1e-3)


def test_reports_not_an_uncertainty():
    out = parameter_elasticities(1e-5)
    assert out["is_uncertainty"] is False
    assert out["most_sensitive_parameter"] in out["elasticities"]


def test_deterministic():
    assert parameter_elasticities(1e-5) == parameter_elasticities(1e-5)
