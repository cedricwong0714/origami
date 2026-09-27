"""run_design is the single interface over payloads, signal pairs, and reports.

Radii, linker widths, free concentrations, and the custom Kd below are
caller-supplied fixtures. They are not measured biological constants.
The CaM–M13 Kd used by default_cam_m13_pair() is the published peptide value.
"""

import json
import math

import numpy as np
import pytest

from origami.engine import run_design
from origami.io.payloads import load_payloads
from origami.io.signal_pairs import SignalPair, default_cam_m13_pair
from origami.physical.geometry import build_ctpr
from origami.physical.linkers import gaussian_chain_ceff
from origami.physical.steric import payload_center
from origami.priors import CTPR_SCAFFOLD_RADIUS_A
from origami.report import DesignReport
from src.core.ctpr_geometry import CTPR_RADIUS_NM

# Caller-supplied free concentration for the Langmuir check, in molar.
# θ_ss = C_free / (C_free + Kd). This is not a measured intracellular value.
_C_FREE_M = 1e-9


def _payload_rows() -> list[dict]:
    # Explicit radii and linker sigmas. Not estimated by the importer.
    return [
        {
            "payload_id": "alpha",
            "role": "upstream",
            "fusion_terminus": "N",
            "repeat_index": 0,
            "radius_A": 20.0,
            "linker_sigma_A": 12.0,
        },
        {
            "payload_id": "beta",
            "role": "downstream",
            "fusion_terminus": "C",
            "repeat_index": 7,
            "radius_A": 22.0,
            "linker_sigma_A": 15.0,
        },
    ]


def test_run_design_packages_payloads_and_default_pair():
    rows = _payload_rows()
    loaded = load_payloads(rows)
    pair = default_cam_m13_pair()

    from_rows = run_design(
        "integrated",
        8,
        payloads=rows,
        signal_pair=pair,
        c_free_M=_C_FREE_M,
    )
    from_records = run_design(
        "integrated",
        8,
        payloads=loaded,
        signal_pair=pair,
        c_free_M=_C_FREE_M,
    )

    assert isinstance(from_rows, DesignReport)
    assert from_rows.calibrated is False
    assert from_records.to_dict() == from_rows.to_dict()

    # Langmuir isotherm at the fixture free concentration and the published Kd.
    expected_theta = _C_FREE_M / (_C_FREE_M + pair.kd_M)
    assert from_rows.theta_ss == pytest.approx(expected_theta)
    assert from_rows.theta_95_lower is not None
    assert from_rows.theta_95_upper is not None
    assert from_rows.theta_95_lower <= from_rows.theta_ss <= from_rows.theta_95_upper

    assert "kon" in from_rows.omitted
    assert from_rows.omitted == ["kon", "k_cat", "K_m", "k_escape", "v_prod"]
    assert from_rows.da is None
    assert from_rows.p_capture is None
    assert from_rows.prior_geometry_id == "src.core.ctpr_geometry"
    assert from_rows.prior_kd_id == "cam_m13_peptide_0.19nM"
    for name in ("theta_t", "time_s", "theta_time", "time_course"):
        assert not hasattr(from_rows, name)
    payload = from_rows.to_dict()
    assert "theta_t" not in payload
    assert "time_s" not in payload
    assert json.loads(json.dumps(payload)) == payload

    # Pair C_eff uses both supplied linker widths as the standoffs. Variances add.
    geom = build_ctpr(8)
    distance_A = float(
        np.linalg.norm(
            payload_center(geom.site(0), 12.0 + 20.0)
            - payload_center(geom.site(7), 15.0 + 22.0)
        )
    )
    sigma_A = math.hypot(12.0, 15.0)
    expected_ceff = gaussian_chain_ceff(distance_A, sigma_A).C_eff_M
    assert from_rows.pair_distances_A["0-7"] == pytest.approx(distance_A)
    assert from_rows.c_eff_M["0-7"] == pytest.approx(expected_ceff)
    assert 0.0 <= from_rows.p_clash["0-7"] <= 1.0


def test_custom_pair_without_sigma_does_not_borrow_peptide_width():
    # Fixture Kd. Not the CaM–M13 value and not a literature parameter.
    pair = SignalPair(
        signal_id="ligand",
        binder_id="binder",
        partner_id="partner",
        kd_M=1e-6,
        kd_source="unit-test fixture Kd; not a literature value",
        kd_sigma_M=None,
        kon_per_M_s=None,
    )
    # Equal to the fixture Kd, so the Langmuir occupancy is exactly 1/2.
    c_free_M = 1e-6
    report = run_design("custom-kd", 6, signal_pair=pair, c_free_M=c_free_M)

    expected = c_free_M / (c_free_M + pair.kd_M)
    assert report.theta_ss == pytest.approx(expected)
    assert report.theta_ss == pytest.approx(0.5)
    assert report.theta_95_lower is not None
    assert report.theta_95_upper is not None
    span = report.theta_95_upper - report.theta_95_lower
    assert span <= 8 * math.ulp(report.theta_ss)
    assert "kon" in report.omitted
    assert "theta_t" not in report.to_dict()
    assert report.calibrated is False


def test_payload_dict_missing_linker_is_not_defaulted():
    row = _payload_rows()[0]
    del row["linker_sigma_A"]
    with pytest.raises(ValueError, match="linker_sigma_A"):
        run_design("missing-linker", 6, payloads=[row])


def test_scaffold_radius_is_the_deposited_centroid_in_angstroms():
    # 1 nm = 10 Å. CTPR_RADIUS_NM is the deposited repeat-centroid radius.
    assert CTPR_SCAFFOLD_RADIUS_A.value == pytest.approx(CTPR_RADIUS_NM * 10.0)
    assert CTPR_SCAFFOLD_RADIUS_A.value == pytest.approx(12.185585199113614)
    assert CTPR_SCAFFOLD_RADIUS_A.units == "Å"
    assert "10.1107/S0907444907024353" in CTPR_SCAFFOLD_RADIUS_A.source
    assert CTPR_SCAFFOLD_RADIUS_A.sigma == pytest.approx(0.5696084155839191)
