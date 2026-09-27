import importlib.util
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parents[2] / "src" / "gp_model" / "check_ood.py"


def _load_check_ood():
    spec = importlib.util.spec_from_file_location("origami_check_ood", _MOD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.check_ood


check_ood = _load_check_ood()


def test_in_domain_when_all_within_bounds():
    features = {"x": 0.5, "y": 2.0}
    bounds = {"x": (0.0, 1.0), "y": (1.0, 3.0)}
    result = check_ood(features, bounds)
    assert result["in_domain"] is True
    assert result["reasons"] == []


def test_out_of_domain_value():
    features = {"x": 1.5}
    bounds = {"x": (0.0, 1.0)}
    result = check_ood(features, bounds)
    assert result["in_domain"] is False
    assert len(result["reasons"]) >= 1


def test_missing_bounds_is_ood():
    features = {"x": 0.2, "z": 0.1}
    bounds = {"x": (0.0, 1.0)}
    result = check_ood(features, bounds)
    assert result["in_domain"] is False
    assert any("no bounds" in r for r in result["reasons"])
