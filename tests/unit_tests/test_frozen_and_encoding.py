"""Pass/fail, frozen table, sequence fallback. Execution tests, not validation."""

import json
import warnings

import numpy as np
import pytest

from src.experiment_design.frozen_table import (
    build_frozen_row,
    cost_weighted_ei,
    evaluate_pass_fail,
    load_config,
    passes,
    write_frozen_table,
)
from src.gp_model.sequence_encoding import composition_features, encode_sequence


def test_pass_requires_the_lower_95_bound():
    assert passes(1.0, 0.1, 0.8) is True
    assert passes(1.0, 0.2, 0.8) is False  # 1 - 1.96*0.2 = 0.608 < 0.8


def test_overall_pass_needs_every_output():
    cfg = load_config()
    good = {k: (10.0, 0.01) for k in ("luminescence", "locking_fraction", "solubility", "purity")}
    assert evaluate_pass_fail(good, cfg)["overall_status"] == "PASS"
    bad = dict(good, purity=(0.1, 0.01))
    assert evaluate_pass_fail(bad, cfg)["overall_status"] == "FAIL"


def test_cost_weighted_ei_divides_by_the_configured_cost():
    cfg = load_config()
    a = cost_weighted_ei(np.array([1.0]), np.array([1.0]), 0.0, "wet_full_panel", cfg)
    b = cost_weighted_ei(np.array([1.0]), np.array([1.0]), 0.0, "dry_docking", cfg)
    assert a[0] * 10 == pytest.approx(b[0] * 0.01)


def test_frozen_table_refuses_overwrite(tmp_path):
    cfg = load_config()
    preds = {k: (10.0, 0.01) for k in ("luminescence", "locking_fraction", "expression", "solubility", "purity")}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        row = build_frozen_row(
            "s1", "m0", {"geometry_group": "CTPR17", "application_group": "general_platform"},
            "onehot", "dry+wet", preds, cfg, 0.0, "wet",
        )
    assert any("unmeasured" in str(x.message) for x in w)
    assert row["geometry_group"] == "CTPR17"
    assert row["application_group"] == "general_platform"
    path = tmp_path / "frozen.json"
    write_frozen_table([row], path)
    with pytest.raises(FileExistsError):
        write_frozen_table([row], path)
    assert json.loads(path.read_text())[0]["overall_status"] == "PASS"


def test_encode_sequence_falls_back_to_onehot_without_torch():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        vec, method = encode_sequence("ACDE", method="esm2")
    assert method == "onehot"
    assert vec.shape == (21,)
    assert any("ESM-2" in str(x.message) for x in w)
    c = composition_features("AAAA")
    assert c[0] == 1.0 and c.sum() == pytest.approx(1.0)
