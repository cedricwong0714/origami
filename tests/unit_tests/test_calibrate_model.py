from src.calibration.calibrate_model import calibrate_model


def test_n_less_than_three_not_identifiable():
    result = calibrate_model([{"y": 1.0, "yhat": 1.1}, {"y": 2.0, "yhat": 2.2}])
    assert result["identifiable"] is False
    assert result["metrics"] is None
    assert "warning" in result


def test_loo_metrics_when_enough_points():
    data = [
        {"y": 1.0, "yhat": 1.0},
        {"y": 2.0, "yhat": 2.5},
        {"y": 3.0, "yhat": 2.5},
    ]
    result = calibrate_model(data)
    assert result["identifiable"] is True
    assert result["metrics"] is not None
    assert result["metrics"]["n"] == 3
    assert "rmse" in result["metrics"]
    assert "mae" in result["metrics"]
    assert "scientific validation" in result["warning"].lower()


def test_empty_data():
    result = calibrate_model([])
    assert result["identifiable"] is False
    assert result["metrics"] is None
