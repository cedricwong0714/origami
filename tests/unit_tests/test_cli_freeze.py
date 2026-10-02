"""CLI freeze and compare use a labeled placeholder interval."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.ui.cli import _cmd_compare, _cmd_freeze


def test_cli_freeze_labels_placeholder_interval_and_compares(tmp_path, monkeypatch):
    frozen_dir = tmp_path / "frozen"
    comparison_dir = tmp_path / "comparisons"
    monkeypatch.setattr("src.predictions.freeze.FROZEN_PREDICTIONS_DIR", frozen_dir)
    monkeypatch.setattr("src.predictions.freeze.COMPARISONS_DIR", comparison_dir)

    code = _cmd_freeze(
        SimpleNamespace(
            prediction_id="CLI_FREEZE_TEST",
            calcium_uM="1",
            e_t=1e-6,
            m_t=1e-6,
            t_end=10.0,
            overwrite=False,
            json=False,
        )
    )
    assert code == 0
    frozen_path = frozen_dir / "CLI_FREEZE_TEST.json"
    payload = json.loads(frozen_path.read_text(encoding="utf-8"))
    row = payload["predictions"]["ca_1uM"]
    assert row["uncertainty_method"] == "fixed_relative_placeholder_pm_30_percent"
    assert row["uncertainty_95_lower"] == row["predicted_value"] * 0.7
    assert row["uncertainty_95_upper"] == row["predicted_value"] * 1.3
    assert row["confidence_tier"] == "hypothesis_only"
    sources = " ".join(payload["parameter_sources"])
    assert "not printed" in sources
    assert any("fixed relative placeholder" in item for item in payload["assumptions"])

    observations = tmp_path / "observations.json"
    observations.write_text(
        json.dumps({"ca_1uM": row["predicted_value"]}),
        encoding="utf-8",
    )
    compare_code = _cmd_compare(
        SimpleNamespace(
            frozen=str(frozen_path),
            observations=str(observations),
            comparison_id="CLI_FREEZE_TEST_CMP",
            overwrite=False,
        )
    )
    assert compare_code == 0
    comparison = json.loads(
        (comparison_dir / "CLI_FREEZE_TEST_CMP.json").read_text(encoding="utf-8")
    )
    assert comparison["comparisons"]["ca_1uM"]["within_95ci"] is True
