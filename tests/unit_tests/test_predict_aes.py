import importlib.util
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parents[2] / "src" / "gp_model" / "predict_aes.py"


def _load_predict_aes():
    spec = importlib.util.spec_from_file_location("origami_predict_aes", _MOD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.predict_aes


predict_aes = _load_predict_aes()


def test_predict_aes_is_deterministic_and_not_bare_number():
    features = {"length": 1.0, "gc": 0.5}
    a = predict_aes(features)
    b = predict_aes(features)
    assert a["predicted_value"] == b["predicted_value"]
    assert a["units"] == "AES"
    assert "uncertainty_95_lower" in a
    assert "uncertainty_95_upper" in a
    assert a["uncertainty_95_lower"] <= a["predicted_value"] <= a["uncertainty_95_upper"]
    assert a["confidence_tier"] == "hypothesis_only"
    assert a["is_extrapolation"] is True
    assert a["human_review_required"] is True
    assert any("UNCALIBRATED" in w for w in a["warnings"])


def test_empty_features_still_structured():
    result = predict_aes({})
    assert result["units"] == "AES"
    assert result["confidence_tier"] == "hypothesis_only"
    assert result["is_extrapolation"] is True
