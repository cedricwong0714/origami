"""CLI validate-learn subcommand."""

from pathlib import Path

from src.data_ingestion.learn_timeseries import resolve_example_package


def test_validate_learn_example_package_via_loader():
    csv_path, meta_path = resolve_example_package()
    from src.data_ingestion import load_learn_timeseries_package

    pkg = load_learn_timeseries_package(csv_path, meta_path)
    assert pkg.metadata.data_class == "synthetic_fixture"
    assert len(pkg.time) >= 2


def test_cli_validate_learn_success(capsys):
    from src.ui.cli import _cmd_validate_learn

    csv_path, meta_path = resolve_example_package()
    code = _cmd_validate_learn(
        type("Args", (), {"csv": str(csv_path), "metadata": str(meta_path), "allow_missing_controls": False})()
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert "SYN_LEARN_001" in out


def test_cli_validate_learn_missing_file():
    from src.ui.cli import _cmd_validate_learn

    code = _cmd_validate_learn(
        type(
            "Args",
            (),
            {"csv": "missing.csv", "metadata": "missing.json", "allow_missing_controls": False},
        )()
    )
    assert code == 1


def test_cli_optimize_success(capsys):
    from src.ui.cli import _cmd_optimize

    code = _cmd_optimize(
        type(
            "Args",
            (),
            {
                "radius_a": 45.0,
                "radius_b": 25.0,
                "interaction": "Metabolic",
                "km": 1e-4,
                "json": False,
            },
        )()
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Δi" in out or "optimal" in out.lower()
    assert "Tier-3" in out


def test_cli_optimize_json(capsys):
    from src.ui.cli import _cmd_optimize

    code = _cmd_optimize(
        type(
            "Args",
            (),
            {
                "radius_a": 30.0,
                "radius_b": 30.0,
                "interaction": "Binding",
                "km": 1e-4,
                "json": True,
            },
        )()
    )
    assert code == 0
    assert "optimal_delta_i" in capsys.readouterr().out
