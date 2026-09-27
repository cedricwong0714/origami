from src.ode_model.check_simulation import check_simulation


def test_valid_config_no_errors():
    errors = check_simulation(
        {
            "model_version": "ode-1",
            "timestep": 0.1,
            "units": {"time": "s"},
            "calibrated": False,
        }
    )
    assert errors == []


def test_missing_model_version():
    errors = check_simulation({"timestep": 1.0, "units": {"t": "s"}})
    assert "missing model_version" in errors


def test_nonpositive_timestep():
    errors = check_simulation(
        {"model_version": "v", "timestep": 0, "units": {"t": "s"}}
    )
    assert "timestep<=0" in errors


def test_missing_units():
    errors = check_simulation({"model_version": "v", "timestep": 0.5})
    assert "missing units" in errors


def test_calibrated_without_dataset_id():
    errors = check_simulation(
        {
            "model_version": "v",
            "timestep": 0.5,
            "units": {"t": "s"},
            "calibrated": True,
        }
    )
    assert "calibrated flag True without dataset_id" in errors
