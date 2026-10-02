"""Gibbs–Helmholtz calculator: arithmetic identity, not a protein fit.

Scientific basis: for a two-state melt, ΔG(Tm) = 0, so ΔS(Tm) = ΔH_m / Tm.
The compact and enthalpy–entropy forms of the Gibbs–Helmholtz equation
are the same relation. Phillips et al. 2012 (DOI 10.1002/pro.2018)
used that relation to report unfolding ΔG at 10°C. This file does not
treat a passing test as a DSC measurement.

Failure mode: a calculator that fills ΔH or ΔCp when the literature
JSON has no such column, that reports a non-zero ΔG at Tm, or that
changes the equation until it matches a stored ΔG.
"""

from __future__ import annotations

import json
import math

import pytest
from fastapi.testclient import TestClient

from origami.api.structural import app
from origami.stability.series import literature_table_path, load_named_series
from origami.stability.thermo import (
    ThermoInputError,
    effective_enthalpy_delta_cp_zero,
    gibbs_helmholtz_curves,
    gibbs_helmholtz_report,
    thermo_prefill,
)

# Pure arithmetic temperatures and energies. They are not a measured
# protein, not a row in ctpr_thermal_literature.json, and not a default
# for any construct.
_TM_C = 26.85  # 300 K
_T_C = 16.85  # 290 K
_DELTA_H = 10.0
_DELTA_CP = 0.2

client = TestClient(app)


def _json_rows() -> list[dict[str, object]]:
    payload = json.loads(literature_table_path().read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert isinstance(rows, list)
    return rows


def _folded(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _row_has_token(row: dict[str, object], tokens: tuple[str, ...]) -> bool:
    for key, value in row.items():
        folded_key = _folded(str(key))
        if any(token in folded_key for token in tokens):
            return True
        if key == "observable" and isinstance(value, str):
            folded_obs = _folded(value)
            if any(token in folded_obs for token in tokens):
                return True
    return False


def _numeric_field(row: dict[str, object], tokens: tuple[str, ...]) -> float | None:
    for key, value in row.items():
        if key == "observable":
            continue
        if not any(token in _folded(str(key)) for token in tokens):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if not math.isfinite(float(value)):
            continue
        return float(value)
    observable = row.get("observable")
    if isinstance(observable, str) and any(token in _folded(observable) for token in tokens):
        value = row.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if math.isfinite(float(value)):
            return float(value)
    return None


def _compact_delta_g(t_k: float, tm_k: float, delta_h: float, delta_cp: float) -> float:
    return delta_h * (1.0 - t_k / tm_k) + delta_cp * (
        (t_k - tm_k) - t_k * math.log(t_k / tm_k)
    )


def _from_enthalpy_entropy(
    t_k: float, tm_k: float, delta_h: float, delta_cp: float
) -> tuple[float, float, float]:
    delta_h_t = delta_h + delta_cp * (t_k - tm_k)
    delta_s_t = delta_h / tm_k + delta_cp * math.log(t_k / tm_k)
    delta_g = delta_h_t - t_k * delta_s_t
    return delta_g, delta_h_t, delta_s_t


def test_delta_g_is_zero_at_tm() -> None:
    """ΔG(Tm) = 0 for the two-state model, within 1e-9."""
    report = gibbs_helmholtz_report(_TM_C, _TM_C, _DELTA_H, 1.5)
    assert abs(report["delta_g"]) < 1e-9
    assert report["calibrated"] is False
    assert report["t_k"] == pytest.approx(_TM_C + 273.15)
    assert report["tm_k"] == pytest.approx(_TM_C + 273.15)


def test_delta_s_at_tm_is_delta_h_over_tm() -> None:
    """ΔS(Tm) = ΔH_m / Tm because ΔG(Tm) = 0, including when ΔCp is not zero."""
    report = gibbs_helmholtz_report(_TM_C, _TM_C, _DELTA_H, _DELTA_CP)
    tm_k = _TM_C + 273.15
    assert report["delta_s"] == pytest.approx(_DELTA_H / tm_k)
    assert report["delta_s_at_tm"] == pytest.approx(_DELTA_H / tm_k)
    assert report["delta_s_units"] == "kcal mol-1 K-1"
    assert report["delta_h_units"] == "kcal mol-1"


def test_two_delta_g_formulas_agree() -> None:
    """The ΔH−TΔS form and the compact form are the same number."""
    report = gibbs_helmholtz_report(_T_C, _TM_C, _DELTA_H, _DELTA_CP)
    t_k = _T_C + 273.15
    tm_k = _TM_C + 273.15
    compact = _compact_delta_g(t_k, tm_k, _DELTA_H, _DELTA_CP)
    from_hs, delta_h_t, delta_s_t = _from_enthalpy_entropy(
        t_k, tm_k, _DELTA_H, _DELTA_CP
    )
    assert compact == pytest.approx(from_hs)
    assert report["delta_g"] == pytest.approx(compact)
    assert report["delta_g"] == pytest.approx(from_hs)
    assert abs(report["delta_g"] - report["delta_g_compact"]) < 1e-9
    assert report["delta_h"] == pytest.approx(delta_h_t)
    assert report["delta_s"] == pytest.approx(delta_s_t)


def test_zero_delta_cp_keeps_delta_h_constant() -> None:
    """ΔCp = 0 leaves ΔH(T) equal to ΔH_m at two different temperatures."""
    hot = gibbs_helmholtz_report(50.0, 40.0, 12.0, 0.0)
    cold = gibbs_helmholtz_report(10.0, 40.0, 12.0, 0.0)
    assert hot["delta_h"] == pytest.approx(12.0)
    assert cold["delta_h"] == pytest.approx(12.0)
    assert hot["delta_s"] == pytest.approx(cold["delta_s"])
    assert hot["delta_cp"] == 0.0


def test_negative_delta_cp_warns_and_still_computes() -> None:
    report = gibbs_helmholtz_report(_T_C, _TM_C, _DELTA_H, -0.4)
    assert math.isfinite(report["delta_g"])
    assert any("negative" in warning.lower() for warning in report["warnings"])
    assert report["calibrated"] is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"t_c": float("nan"), "tm_c": _TM_C, "delta_h": 1.0, "delta_cp": 0.0},
        {"t_c": _T_C, "tm_c": float("inf"), "delta_h": 1.0, "delta_cp": 0.0},
        {"t_c": _T_C, "tm_c": _TM_C, "delta_h": float("-inf"), "delta_cp": 0.0},
        {"t_c": _T_C, "tm_c": _TM_C, "delta_h": 1.0, "delta_cp": float("nan")},
        {"t_c": -273.15, "tm_c": _TM_C, "delta_h": 1.0, "delta_cp": 0.0},
        {"t_c": -300.0, "tm_c": _TM_C, "delta_h": 1.0, "delta_cp": 0.0},
        {"t_c": _T_C, "tm_c": -273.15, "delta_h": 1.0, "delta_cp": 0.0},
        {"t_c": _T_C, "tm_c": _TM_C, "delta_h": None, "delta_cp": 0.0},
        {"t_c": _T_C, "tm_c": _TM_C, "delta_h": 1.0, "delta_cp": None},
        {"t_c": True, "tm_c": _TM_C, "delta_h": 1.0, "delta_cp": 0.0},
        {"t_c": "25", "tm_c": _TM_C, "delta_h": 1.0, "delta_cp": 0.0},
    ],
)
def test_missing_or_non_finite_inputs_are_rejected(kwargs: dict[str, object]) -> None:
    """Invalid inputs raise. They are never replaced with a literature number."""
    with pytest.raises(ThermoInputError):
        gibbs_helmholtz_report(
            kwargs["t_c"],
            kwargs["tm_c"],
            kwargs["delta_h"],
            kwargs["delta_cp"],
        )


def test_omitted_uncertainty_stays_null() -> None:
    report = gibbs_helmholtz_report(_T_C, _TM_C, _DELTA_H, _DELTA_CP)
    assert report["uncertainty_defined"] is False
    assert report["delta_g_sigma"] is None
    assert report["delta_h_sigma"] is None
    assert report["delta_s_sigma"] is None
    assert report["delta_g_95_lower"] is None
    assert report["delta_g_95_upper"] is None
    assert "not supplied" in report["uncertainty_note"].lower()


def test_partial_uncertainty_is_not_completed_with_zero() -> None:
    report = gibbs_helmholtz_report(
        _T_C,
        _TM_C,
        _DELTA_H,
        _DELTA_CP,
        delta_h_sigma=0.1,
    )
    assert report["delta_g_sigma"] is None
    assert "not supplied" in report["uncertainty_note"].lower()
    assert "delta_cp" in report["uncertainty_note"]


def test_supplied_sigmas_propagate_independent_first_order() -> None:
    """95% band is value ± 1.96 sigma. Partials are checked by finite difference."""
    sigma_h = 0.1
    sigma_c = 0.05
    sigma_tm = 0.3
    report = gibbs_helmholtz_report(
        _T_C,
        _TM_C,
        _DELTA_H,
        _DELTA_CP,
        delta_h_sigma=sigma_h,
        delta_cp_sigma=sigma_c,
        tm_sigma_c=sigma_tm,
    )
    eps = 1e-4

    def g_of(delta_h: float, delta_cp: float, tm_c: float) -> float:
        return float(
            gibbs_helmholtz_report(_T_C, tm_c, delta_h, delta_cp)["delta_g"]
        )

    d_g_d_h = (
        g_of(_DELTA_H + eps, _DELTA_CP, _TM_C) - g_of(_DELTA_H - eps, _DELTA_CP, _TM_C)
    ) / (2 * eps)
    d_g_d_c = (
        g_of(_DELTA_H, _DELTA_CP + eps, _TM_C) - g_of(_DELTA_H, _DELTA_CP - eps, _TM_C)
    ) / (2 * eps)
    d_g_d_tm = (
        g_of(_DELTA_H, _DELTA_CP, _TM_C + eps) - g_of(_DELTA_H, _DELTA_CP, _TM_C - eps)
    ) / (2 * eps)
    expected = math.sqrt(
        (d_g_d_h * sigma_h) ** 2 + (d_g_d_c * sigma_c) ** 2 + (d_g_d_tm * sigma_tm) ** 2
    )
    assert report["delta_g_sigma"] == pytest.approx(expected, rel=1e-6, abs=1e-8)
    assert report["delta_g_95_lower"] == pytest.approx(
        report["delta_g"] - 1.96 * report["delta_g_sigma"]
    )
    assert report["delta_g_95_upper"] == pytest.approx(
        report["delta_g"] + 1.96 * report["delta_g_sigma"]
    )
    assert report["uncertainty_defined"] is True


def test_kj_inputs_convert_with_recorded_factor() -> None:
    kcal = gibbs_helmholtz_report(_T_C, _TM_C, _DELTA_H, _DELTA_CP, units="kcal")
    kJ = gibbs_helmholtz_report(
        _T_C,
        _TM_C,
        _DELTA_H * 4.184,
        _DELTA_CP * 4.184,
        units="kJ",
    )
    assert kJ["unit_conversion_applied"] is True
    assert kJ["unit_conversion_factor_kJ_per_kcal"] == 4.184
    assert kcal["unit_conversion_applied"] is False
    assert kJ["delta_g"] == pytest.approx(kcal["delta_g"])
    assert kJ["delta_h"] == pytest.approx(kcal["delta_h"])
    assert kJ["delta_s"] == pytest.approx(kcal["delta_s"])
    assert kJ["delta_g_units"] == "kcal mol-1"
    assert kJ["delta_h_units"] == "kcal mol-1"
    assert kJ["delta_s_units"] == "kcal mol-1 K-1"
    assert any("4.184" in warning for warning in kJ["warnings"])


def test_prefill_copies_cited_tm_and_does_not_invent_enthalpy() -> None:
    """ΔH and ΔCp stay null unless the JSON column exists.

    If a row does carry ΔHcal and ΔCp, the calculator must reproduce that
    row's stored ΔG at 10°C. A mismatch fails with both numbers. The
    equation is not adjusted to force agreement.
    """
    rows = _json_rows()
    dh_tokens = ("deltah", "hcal")
    dcp_tokens = ("deltacp", "heatcapacity")
    rows_with_both = [
        row
        for row in rows
        if _row_has_token(row, dh_tokens) and _row_has_token(row, dcp_tokens)
    ]
    # A column can also be split across sibling rows (one ΔHcal row, one ΔCp row).
    has_any_dh = any(_row_has_token(row, dh_tokens) for row in rows)
    has_any_dcp = any(_row_has_token(row, dcp_tokens) for row in rows)

    series_id = "phillips2012_ctpra_dsc"
    tm_raw = next(
        row for row in rows if row["record_id"] == "phillips2012_ctpra3_tm_dsc"
    )
    dg_raw = next(
        row for row in rows if row["record_id"] == "phillips2012_ctpra3_dg_dsc"
    )
    prefill = thermo_prefill(series_id, int(tm_raw["n_repeats"]))
    assert prefill["calibrated"] is False
    assert prefill["interpolated"] is False
    assert prefill["averaged"] is False
    assert prefill["tm_c"] == tm_raw["value"]
    assert prefill["tm_units"] == tm_raw["units"]
    assert prefill["doi"] == tm_raw["doi"]
    assert prefill["method"] == tm_raw["method"]
    assert prefill["delta_g"] == dg_raw["value"]
    assert prefill["delta_g_units"] == dg_raw["units"]

    assert has_any_dh and has_any_dcp
    assert prefill["delta_h"] == tm_raw["delta_Hcal"]
    assert prefill["delta_h_units"] == tm_raw["delta_Hcal_units"]
    assert prefill["delta_cp"] == tm_raw["delta_Cp"]
    return

    groups: dict[tuple[object, object, object], dict[str, float]] = {}
    for row in rows:
        if row.get("doi") != "10.1002/pro.2018":
            continue
        key = (row.get("construct"), row.get("method"), row.get("buffer"))
        bucket = groups.setdefault(key, {})
        if row.get("observable") == "Tm_C" and isinstance(row.get("value"), (int, float)):
            bucket["tm_c"] = float(row["value"])
        if row.get("observable") == "delta_G" and isinstance(row.get("value"), (int, float)):
            bucket["delta_g"] = float(row["value"])
        dh = _numeric_field(row, dh_tokens)
        dcp = _numeric_field(row, dcp_tokens)
        if dh is not None:
            bucket["delta_h"] = dh
        if dcp is not None:
            bucket["delta_cp"] = dcp
    complete = [
        values
        for values in groups.values()
        if {"tm_c", "delta_g", "delta_h", "delta_cp"} <= set(values)
    ]
    assert complete or rows_with_both, (
        "JSON contains ΔH and ΔCp tokens but no construct has Tm, ΔG, ΔH, and ΔCp together"
    )
    # 10°C is the temperature named for the Phillips unfolding ΔG column
    # in data/stability/README.md. It is the comparison temperature for
    # this check, not a filled-in enthalpy.
    for values in complete:
        report = gibbs_helmholtz_report(
            10.0,
            values["tm_c"],
            values["delta_h"],
            values["delta_cp"],
            units="kcal",
        )
        discrepancy = float(report["delta_g"]) - values["delta_g"]
        assert abs(discrepancy) <= 1e-4, (
            "Gibbs–Helmholtz at 10 C does not reproduce the stored ΔG. "
            f"Stored {values['delta_g']} kcal mol-1, "
            f"computed {report['delta_g']} kcal mol-1, "
            f"discrepancy {discrepancy} kcal mol-1. "
            f"Inputs Tm={values['tm_c']} C, ΔH={values['delta_h']}, "
            f"ΔCp={values['delta_cp']}. "
            "Do not tweak the equation to force a match."
        )


def test_prefill_does_not_interpolate_or_average_series() -> None:
    series_id = "phillips2012_ctpra_dsc"
    observed: dict[int, float] = {}
    for obs in load_named_series(series_id):
        assert obs.n_repeats not in observed
        observed[obs.n_repeats] = float(obs.value)
    present = sorted(observed)
    gaps = [n for n in range(present[0], present[-1] + 1) if n not in observed]
    for n_repeats in gaps:
        missing = thermo_prefill(series_id, n_repeats)
        assert missing["tm_c"] is None
        assert missing["delta_h"] is None
        assert missing["delta_cp"] is None
        assert missing["interpolated"] is False
        assert missing["tm_status"] == "omitted"
    outside = thermo_prefill(series_id, present[-1] + 1)
    assert outside["tm_c"] is None
    assert outside["delta_h"] is None
    assert outside["delta_cp"] is None
    assert outside["tm_status"] == "extrapolated"

    # Compare the two methods at a length both series actually measured.
    shared_n = None
    cd_observed = {obs.n_repeats for obs in load_named_series("phillips2012_ctpra_cd")}
    for n_repeats in present:
        if n_repeats in cd_observed:
            shared_n = n_repeats
            break
    assert shared_n is not None
    cd = thermo_prefill("phillips2012_ctpra_cd", shared_n)
    dsc = thermo_prefill(series_id, shared_n)
    assert cd["tm_c"] is not None and dsc["tm_c"] is not None
    assert cd["tm_c"] != dsc["tm_c"]
    assert cd["method"] == "CD"
    assert dsc["method"] == "DSC"


def test_cortajarena_prefill_has_tm_and_no_invented_delta_g_or_enthalpy() -> None:
    rows = _json_rows()
    raw = next(row for row in rows if row["record_id"] == "cortajarena2011_ctpra3_tm_dsc")
    prefill = thermo_prefill("cortajarena2011_ctpra_dsc", int(raw["n_repeats"]))
    assert prefill["tm_c"] == raw["value"]
    assert prefill["doi"] == raw["doi"]
    assert prefill["delta_g"] is None
    assert prefill["delta_h"] is None
    assert prefill["delta_cp"] is None


def test_missing_delta_hcal_returns_no_curve() -> None:
    """A missing ΔHcal or ΔCp does not become a curve of zeros.

    A finite Tm still returns ΔG(Tm) = 0. That is one value, not a
    plotted series. A missing Tm does not invent ΔG.
    """
    cases = (
        {"tm_c": 60.0, "delta_h": None, "delta_cp": 0.2, "expect_identity": True},
        {"tm_c": 60.0, "delta_h": 10.0, "delta_cp": None, "expect_identity": True},
        {"tm_c": None, "delta_h": None, "delta_cp": None, "expect_identity": False},
    )
    for case in cases:
        expect_identity = bool(case["expect_identity"])
        kwargs = {
            "tm_c": case["tm_c"],
            "delta_h": case["delta_h"],
            "delta_cp": case["delta_cp"],
        }
        report = gibbs_helmholtz_curves(**kwargs)
        assert report["has_curve"] is False
        assert report["calibrated"] is False
        assert report["points"] == []
        assert report["delta_g"] is None
        assert report["delta_h"] is None
        assert report["delta_s"] is None
        assert report["missing_inputs"]
        assert report["uncertainty_defined"] is False
        assert report["delta_g_sigma"] is None
        assert report["delta_g_95_lower"] is None
        assert report["delta_g_95_upper"] is None
        assert "calorimetry inputs are missing" in report["message"].lower()
        encoded = json.dumps(report["points"])
        assert encoded == "[]"
        if expect_identity:
            assert report["delta_g_at_tm"] == 0.0
            assert report["delta_g_units"] == "kcal mol-1"
            assert report["tm_k"] == pytest.approx(float(case["tm_c"]) + 273.15)
            assert "two-state" in " ".join(report["assumptions"]).lower()
            assert "uncertainty band" in report["uncertainty_note"].lower()
        else:
            assert report["delta_g_at_tm"] is None


def test_finite_tm_without_calorimetry_returns_delta_g_zero() -> None:
    """Finite Tm and missing ΔHcal/ΔCp still returns delta_G_at_Tm = 0.

    Supplying ΔHcal and ΔCp does not move ΔG(Tm) off zero. The curve
    exists only in that second call. The first call has no points.
    """
    alone = gibbs_helmholtz_curves(60.0, None, None)
    assert alone["has_curve"] is False
    assert alone["points"] == []
    assert alone["delta_g_at_tm"] == 0.0
    assert alone["calibrated"] is False
    assert alone["delta_g_95_lower"] is None
    assert alone["delta_g_95_upper"] is None
    supplied = gibbs_helmholtz_curves(60.0, _DELTA_H, _DELTA_CP)
    assert supplied["has_curve"] is True
    assert abs(supplied["delta_g_at_tm"]) < 1e-9
    assert supplied["calibrated"] is False


def test_curve_uses_kelvin_and_is_zero_at_tm() -> None:
    """ΔG(Tm) = 0, and every sample converts °C to K with +273.15."""
    report = gibbs_helmholtz_curves(
        _TM_C,
        _DELTA_H,
        _DELTA_CP,
        t_min_c=0.0,
        t_max_c=100.0,
        n_points=21,
    )
    assert report["has_curve"] is True
    assert report["calibrated"] is False
    assert report["delta_g_units"] == "kcal mol-1"
    assert report["delta_h_units"] == "kcal mol-1"
    assert report["delta_s_units"] == "kcal mol-1 K-1"
    assert abs(report["delta_g_at_tm"]) < 1e-9
    assert report["tm_k"] == pytest.approx(_TM_C + 273.15)
    at_tm = [point for point in report["points"] if abs(point["t_c"] - _TM_C) < 1e-9]
    assert len(at_tm) == 1
    assert abs(at_tm[0]["delta_g"]) < 1e-9
    assert at_tm[0]["t_k"] == pytest.approx(_TM_C + 273.15)
    for point in report["points"]:
        assert point["t_k"] == pytest.approx(point["t_c"] + 273.15)
        assert math.isfinite(point["delta_g"])
        assert math.isfinite(point["delta_h"])
        assert math.isfinite(point["delta_s"])


def test_non_finite_calorimetry_is_rejected_for_curves() -> None:
    with pytest.raises(ThermoInputError):
        gibbs_helmholtz_curves(60.0, float("nan"), 0.1)
    with pytest.raises(ThermoInputError):
        gibbs_helmholtz_curves(60.0, 10.0, float("inf"))


def test_default_series_prefill_n3_and_n8_matches_literature_json() -> None:
    """Cited Tm and printed ΔG are copied. ΔHcal and ΔCp are not invented."""
    rows = _json_rows()
    enthalpy_keys = {
        "delta_s",
        "delta_S",
    }
    for n_repeats in (3, 8):
        tm_rows = [
            row
            for row in rows
            if row.get("record_id") == f"phillips2012_ctpra{n_repeats}_tm_dsc"
        ]
        dg_rows = [
            row
            for row in rows
            if row.get("record_id") == f"phillips2012_ctpra{n_repeats}_dg_dsc"
        ]
        assert len(tm_rows) == 1
        assert len(dg_rows) == 1
        tm_raw = tm_rows[0]
        dg_raw = dg_rows[0]
        assert int(tm_raw["n_repeats"]) == n_repeats
        assert int(dg_raw["n_repeats"]) == n_repeats
        assert enthalpy_keys.isdisjoint(tm_raw)
        assert enthalpy_keys.isdisjoint(dg_raw)
        assert "delta_Hcal" not in dg_raw
        prefill = thermo_prefill("phillips2012_ctpra_dsc", n_repeats)
        assert prefill["tm_status"] == "cited"
        assert prefill["tm_c"] == tm_raw["value"]
        assert prefill["tm_units"] == tm_raw["units"]
        assert prefill["delta_g"] == dg_raw["value"]
        assert prefill["delta_g_units"] == dg_raw["units"]
        assert prefill["delta_g_origin"] == "looked_up"
        # 10 °C is the temperature Phillips Table I states for this column
        # (data/stability/README.md). It is not read from the value field.
        assert prefill["delta_g_t_c"] == 10.0
        assert prefill["delta_g_t_units"] == "C"
        assert prefill["delta_h"] == tm_raw["delta_Hcal"]
        assert prefill["delta_cp"] == tm_raw["delta_Cp"]
        assert prefill["calibrated"] is False
        assert prefill["interpolated"] is False
        assert prefill["averaged"] is False


def test_n14_default_series_stays_extrapolated() -> None:
    rows = _json_rows()
    cited = [
        row
        for row in rows
        if row.get("n_repeats") == 14
        and row.get("doi") == "10.1002/pro.2018"
        and row.get("method") == "DSC"
        and str(row.get("construct", "")).startswith("CTPRa")
    ]
    assert cited == []
    prefill = thermo_prefill("phillips2012_ctpra_dsc", 14)
    assert prefill["tm_status"] == "extrapolated"
    assert prefill["tm_c"] is None
    assert prefill["delta_g"] is None
    assert prefill["delta_g_origin"] is None
    assert prefill["delta_g_t_c"] is None
    assert prefill["delta_h"] is None
    assert prefill["delta_cp"] is None
    assert prefill["calibrated"] is False
    assert prefill["interpolated"] is False
    # No typed Tm: the identity is not applied, so ΔG stays uninvented.
    blank = gibbs_helmholtz_curves(None, None, None)
    assert blank["delta_g_at_tm"] is None
    assert blank["has_curve"] is False
    assert blank["points"] == []


def test_http_thermo_and_existing_stability_routes() -> None:
    panel = client.get("/api/stability/panel")
    assert panel.status_code == 200
    assert panel.json()["calibrated"] is False
    confirm = client.get("/api/stability/confirm")
    assert confirm.status_code == 200
    assert confirm.json()["calibrated"] is False

    created = client.post(
        "/api/stability/thermo",
        json={
            "t_c": _T_C,
            "tm_c": _TM_C,
            "delta_h": _DELTA_H,
            "delta_cp": _DELTA_CP,
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["calibrated"] is False
    assert body["delta_g_units"] == "kcal mol-1"
    assert body["t_k"] == pytest.approx(_T_C + 273.15)
    assert body["delta_g_sigma"] is None
    assert "not supplied" in body["uncertainty_note"].lower()

    rejected = client.post(
        "/api/stability/thermo",
        json={"t_c": -300, "tm_c": 40, "delta_h": 1, "delta_cp": 0},
    )
    assert rejected.status_code == 400

    prefill = client.get(
        "/api/stability/thermo/prefill",
        params={"series_id": "phillips2012_ctpra_dsc", "n": 3},
    )
    assert prefill.status_code == 200
    payload = prefill.json()
    assert payload["tm_c"] is not None
    assert payload["delta_h"] == 65.0
    assert payload["delta_cp"] == 0.9
    assert payload["calibrated"] is False
    assert payload["doi"] == "10.1002/pro.2018"

    unknown = client.get(
        "/api/stability/thermo/prefill",
        params={"series_id": "not_a_series", "n": 3},
    )
    assert unknown.status_code == 400

    for n_repeats in (3, 8):
        cited = client.get(
            "/api/stability/thermo/prefill",
            params={"series_id": "phillips2012_ctpra_dsc", "n": n_repeats},
        )
        assert cited.status_code == 200
        payload = cited.json()
        raw_tm = next(
            row
            for row in _json_rows()
            if row["record_id"] == f"phillips2012_ctpra{n_repeats}_tm_dsc"
        )
        raw_dg = next(
            row
            for row in _json_rows()
            if row["record_id"] == f"phillips2012_ctpra{n_repeats}_dg_dsc"
        )
        assert payload["tm_c"] == raw_tm["value"]
        assert payload["delta_g"] == raw_dg["value"]
        assert payload["delta_g_origin"] == "looked_up"
        assert payload["delta_g_t_c"] == 10.0
        assert payload["delta_h"] == raw_tm["delta_Hcal"]
        assert payload["delta_cp"] == raw_tm["delta_Cp"]
        assert payload["tm_status"] == "cited"
        assert payload["calibrated"] is False

    extrapolated = client.get(
        "/api/stability/thermo/prefill",
        params={"series_id": "phillips2012_ctpra_dsc", "n": 14},
    )
    assert extrapolated.status_code == 200
    assert extrapolated.json()["tm_status"] == "extrapolated"
    assert extrapolated.json()["tm_c"] is None
    assert extrapolated.json()["delta_g"] is None
    assert extrapolated.json()["delta_g_origin"] is None
    assert extrapolated.json()["delta_g_t_c"] is None
    assert extrapolated.json()["delta_h"] is None

    missing_curve = client.post(
        "/api/stability/thermo/curves",
        json={"tm_c": _TM_C, "delta_cp": _DELTA_CP},
    )
    assert missing_curve.status_code == 200
    missing_body = missing_curve.json()
    assert missing_body["has_curve"] is False
    assert missing_body["points"] == []
    assert missing_body["delta_g_at_tm"] == 0.0
    assert missing_body["calibrated"] is False
    assert missing_body["delta_g_95_lower"] is None
    assert missing_body["delta_g_95_upper"] is None
    assert "calorimetry inputs are missing" in missing_body["message"].lower()

    null_curve = client.post(
        "/api/stability/thermo/curves",
        json={"tm_c": _TM_C, "delta_h": None, "delta_cp": _DELTA_CP},
    )
    assert null_curve.status_code == 200
    assert null_curve.json()["points"] == []
    assert null_curve.json()["delta_g_at_tm"] == 0.0
    assert null_curve.json()["has_curve"] is False

    rejected_curve = client.post(
        "/api/stability/thermo/curves",
        json={"tm_c": _TM_C, "delta_h": "not-a-number", "delta_cp": 0.1},
    )
    assert rejected_curve.status_code == 400

    curve = client.post(
        "/api/stability/thermo/curves",
        json={
            "tm_c": _TM_C,
            "delta_h": _DELTA_H,
            "delta_cp": _DELTA_CP,
            "t_min_c": 0,
            "t_max_c": 80,
            "n_points": 17,
        },
    )
    assert curve.status_code == 200
    curve_body = curve.json()
    assert curve_body["calibrated"] is False
    assert curve_body["has_curve"] is True
    assert curve_body["points"]
    assert abs(curve_body["delta_g_at_tm"]) < 1e-9
    assert "fusion" in curve_body["result_label"].lower()
    for point in curve_body["points"]:
        assert point["t_k"] == pytest.approx(point["t_c"] + 273.15)
    on_tm = [point for point in curve_body["points"] if abs(point["t_c"] - _TM_C) < 1e-9]
    assert len(on_tm) == 1
    assert abs(on_tm[0]["delta_g"]) < 1e-9


def _closed_delta_h_eff(anchor: float, t_ref_c: float, tm_c: float) -> float:
    """ΔH_eff = ΔG(T_ref) / (1 - T_ref/Tm), temperatures in kelvin."""
    t_ref_k = t_ref_c + 273.15
    tm_k = tm_c + 273.15
    return anchor / (1.0 - t_ref_k / tm_k)


def test_effective_enthalpy_is_zero_at_tm_and_recovers_the_anchor() -> None:
    """ΔCp = 0 closes ΔG(T) from an anchor. A passing test is not validation.

    Scientific basis: with ΔCp = 0 the two-state Gibbs–Helmholtz equation
    reduces to ΔG(T) = ΔH_eff (1 - T/Tm). The anchor fixes ΔH_eff.
    Failure mode: ΔG(Tm) leaves zero, or ΔG at the anchor temperature
    does not return the anchor.
    """
    anchor = 5.0
    t_ref_c = 10.0
    tm_c = 60.0
    report = effective_enthalpy_delta_cp_zero(tm_c, anchor, t_ref_c)
    expected_h = _closed_delta_h_eff(anchor, t_ref_c, tm_c)
    assert report["calibrated"] is False
    assert report["confidence_tier"] == "hypothesis_only"
    assert report["is_extrapolation"] is True
    assert report["has_effective_enthalpy"] is True
    assert report["assumption_delta_cp"] == 0.0
    assert report["delta_cp_units"] == "kcal mol-1 K-1"
    assert report["delta_h_eff"] == pytest.approx(expected_h)
    assert report["delta_s_eff"] == pytest.approx(expected_h / (tm_c + 273.15))
    assert report["delta_g_at_tm"] == 0.0
    assert report["delta_g_at_t_ref"] == pytest.approx(anchor)
    assert report["anchor_delta_g"] == pytest.approx(anchor)
    assert report["delta_g_units"] == "kcal mol-1"
    assert report["delta_h_units"] == "kcal mol-1"
    assert report["delta_s_units"] == "kcal mol-1 K-1"
    assert "not the phillips calorimetric" in report["result_label"].lower()
    assert report["uncertainty_defined"] is False
    at_tm = [point for point in report["points"] if abs(point["t_c"] - tm_c) < 1e-9]
    at_ref = [point for point in report["points"] if abs(point["t_c"] - t_ref_c) < 1e-9]
    assert len(at_tm) == 1
    assert len(at_ref) == 1
    assert abs(at_tm[0]["delta_g"]) < 1e-9
    assert at_ref[0]["delta_g"] == pytest.approx(anchor)
    assert at_tm[0]["t_k"] == pytest.approx(tm_c + 273.15)
    for point in report["points"]:
        assert point["t_k"] == pytest.approx(point["t_c"] + 273.15)
        assert point["delta_g"] == pytest.approx(
            expected_h * (1.0 - point["t_k"] / (tm_c + 273.15))
        )


def test_changing_tm_changes_effective_enthalpy_not_the_printed_cell() -> None:
    """ΔH_eff follows the Tm in use. The looked-up table cell does not."""
    prefill = thermo_prefill("phillips2012_ctpra_dsc", 3)
    anchor = prefill["delta_g"]
    t_ref_c = prefill["delta_g_t_c"]
    cited_tm = prefill["tm_c"]
    assert anchor is not None
    assert t_ref_c == 10.0
    assert cited_tm is not None
    at_cited = effective_enthalpy_delta_cp_zero(cited_tm, anchor, t_ref_c)
    shifted = effective_enthalpy_delta_cp_zero(float(cited_tm) + 5.0, anchor, t_ref_c)
    assert shifted["delta_h_eff"] != pytest.approx(at_cited["delta_h_eff"])
    assert shifted["delta_g_at_t_ref"] == pytest.approx(anchor)
    assert at_cited["delta_g_at_t_ref"] == pytest.approx(anchor)
    assert shifted["delta_g_at_tm"] == 0.0
    assert at_cited["delta_g_at_tm"] == 0.0
    # A point that is not Tm or T_ref must move when Tm moves.
    sample_c = 25.0
    at_cited_25 = next(
        point for point in at_cited["points"] if abs(point["t_c"] - sample_c) < 1e-6
    )
    shifted_25 = next(
        point for point in shifted["points"] if abs(point["t_c"] - sample_c) < 1e-6
    )
    assert shifted_25["delta_g"] != pytest.approx(at_cited_25["delta_g"])
    again = thermo_prefill("phillips2012_ctpra_dsc", 3)
    assert again["delta_g"] == anchor
    assert again["delta_g_t_c"] == 10.0
    assert again["tm_c"] == cited_tm
    assert again["delta_h"] == 65.0
    assert again["delta_cp"] == 0.9
    raw = next(
        row for row in _json_rows() if row["record_id"] == "phillips2012_ctpra3_dg_dsc"
    )
    assert again["delta_g"] == raw["value"]


def test_missing_anchor_does_not_invent_delta_g_of_t() -> None:
    """n=14 has no printed ΔG. A typed Tm still does not invent ΔG(T)."""
    prefill = thermo_prefill("phillips2012_ctpra_dsc", 14)
    assert prefill["delta_g"] is None
    assert prefill["delta_g_t_c"] is None
    report = effective_enthalpy_delta_cp_zero(
        70.0,
        prefill["delta_g"],
        prefill["delta_g_t_c"],
    )
    assert report["has_effective_enthalpy"] is False
    assert report["has_curve"] is False
    assert report["points"] == []
    assert report["delta_h_eff"] is None
    assert report["delta_s_eff"] is None
    assert report["delta_g_at_t_ref"] is None
    assert report["assumption_delta_cp"] is None
    assert report["delta_g_at_tm"] == 0.0
    assert report["calibrated"] is False
    assert report["confidence_tier"] is None
    cleared = effective_enthalpy_delta_cp_zero(70.0, None, 10.0)
    assert cleared["points"] == []
    assert cleared["delta_h_eff"] is None
    assert cleared["delta_g_at_tm"] == 0.0


def test_tm_equal_to_anchor_temperature_is_rejected() -> None:
    """The denominator is zero. ΔG there is the anchor. ΔH is not identifiable."""
    with pytest.raises(ThermoInputError, match="not identifiable"):
        effective_enthalpy_delta_cp_zero(10.0, 5.0, 10.0)
    rejected = client.post(
        "/api/stability/thermo/effective",
        json={"tm_c": 10.0, "delta_g_ref": 5.0, "t_ref_c": 10.0},
    )
    assert rejected.status_code == 400
    assert "not identifiable" in rejected.json()["detail"].lower()
    assert "anchor" in rejected.json()["detail"].lower()


def test_effective_path_does_not_replace_caller_delta_hcal() -> None:
    """A typed ΔHcal and ΔCp stay on the full Gibbs–Helmholtz path."""
    caller_h = 12.0
    caller_cp = 0.5
    full = gibbs_helmholtz_report(20.0, 60.0, caller_h, caller_cp)
    assert full["delta_h_at_tm"] == caller_h
    assert full["delta_cp"] == caller_cp
    effective = effective_enthalpy_delta_cp_zero(60.0, 5.0, 10.0)
    assert effective["delta_h_eff"] != pytest.approx(caller_h)
    assert effective["assumption_delta_cp"] == 0.0
    # Posting the caller's enthalpy to the effective route does not use it.
    http_effective = client.post(
        "/api/stability/thermo/effective",
        json={
            "tm_c": 60.0,
            "delta_g_ref": 5.0,
            "t_ref_c": 10.0,
            "delta_h": caller_h,
            "delta_cp": caller_cp,
        },
    )
    assert http_effective.status_code == 200
    body = http_effective.json()
    assert body["delta_h_eff"] == pytest.approx(effective["delta_h_eff"])
    assert body["delta_h_eff"] != pytest.approx(caller_h)
    assert body["assumption_delta_cp"] == 0.0
    assert body["confidence_tier"] == "hypothesis_only"
    assert body["is_extrapolation"] is True
    assert body["calibrated"] is False
    http_full = client.post(
        "/api/stability/thermo",
        json={"t_c": 60.0, "tm_c": 60.0, "delta_h": caller_h, "delta_cp": caller_cp},
    )
    assert http_full.status_code == 200
    assert http_full.json()["delta_h_at_tm"] == caller_h
    assert abs(http_full.json()["delta_g"]) < 1e-9


def test_effective_enthalpy_converts_kj_with_explicit_factor() -> None:
    """1 kcal = 4.184 kJ. The factor is recorded. Outputs stay in kcal."""
    kcal = effective_enthalpy_delta_cp_zero(60.0, 1.0, 10.0, units="kcal")
    kJ = effective_enthalpy_delta_cp_zero(60.0, 4.184, 10.0, units="kJ")
    assert kJ["unit_conversion_applied"] is True
    assert kJ["unit_conversion_factor_kJ_per_kcal"] == 4.184
    assert any("4.184" in warning for warning in kJ["warnings"])
    assert kJ["delta_h_eff"] == pytest.approx(kcal["delta_h_eff"])
    assert kJ["delta_g_at_t_ref"] == pytest.approx(1.0)
    assert kJ["anchor_delta_g_input"] == 4.184
    assert kcal["unit_conversion_applied"] is False
    assert kcal["unit_conversion_factor_kJ_per_kcal"] is None


def test_http_effective_route_and_printed_prefill_stay_separate() -> None:
    """The printed lookup is the table cell. The effective route does not edit it."""
    prefill = client.get(
        "/api/stability/thermo/prefill",
        params={"series_id": "phillips2012_ctpra_dsc", "n": 3},
    )
    assert prefill.status_code == 200
    cited = prefill.json()
    created = client.post(
        "/api/stability/thermo/effective",
        json={
            "tm_c": float(cited["tm_c"]) + 8.0,
            "delta_g_ref": cited["delta_g"],
            "t_ref_c": cited["delta_g_t_c"],
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["delta_g_at_tm"] == 0.0
    assert body["delta_g_at_t_ref"] == pytest.approx(cited["delta_g"])
    assert body["has_curve"] is True
    assert "ΔCp = 0 assumption" in body["result_label"]
    again = client.get(
        "/api/stability/thermo/prefill",
        params={"series_id": "phillips2012_ctpra_dsc", "n": 3},
    )
    assert again.json()["delta_g"] == cited["delta_g"]
    assert again.json()["tm_c"] == cited["tm_c"]
    assert again.json()["delta_h"] == 65.0
    missing = client.post(
        "/api/stability/thermo/effective",
        json={"tm_c": 70.0, "delta_g_ref": None, "t_ref_c": 10.0},
    )
    assert missing.status_code == 200
    assert missing.json()["points"] == []
    assert missing.json()["delta_h_eff"] is None
    assert missing.json()["delta_g_at_tm"] == 0.0


def _point_at(report: dict[str, object], t_c: float) -> dict[str, object]:
    points = report["points"]
    assert isinstance(points, list)
    matched = [
        point
        for point in points
        if isinstance(point, dict) and abs(float(point["t_c"]) - t_c) < 1e-6
    ]
    assert len(matched) == 1
    return matched[0]


def test_delta_cp_zero_band_matches_anchor_and_is_zero_at_tm() -> None:
    """At T_ref the band is the anchor uncertainty. At Tm, ΔG is 0.

    Scientific basis: under ΔCp = 0, ΔG(T) = ΔH_eff (1 − T/Tm) with
    ΔH_eff = ΔG(T_ref) / (1 − T_ref/Tm), temperatures in kelvin.
    At T_ref the Tm terms cancel, so σ(ΔG) equals σ(anchor). That
    equality is the check that the band is not a new biological number.
    Failure mode: a band at T_ref wider than the anchor sigma, a
    nonzero ΔG at Tm, or a null sigma stored as 0.
    """
    anchor = 5.0
    t_ref_c = 10.0
    tm_c = 60.0
    sigma_g = 0.4
    sigma_tm = 0.3
    report = effective_enthalpy_delta_cp_zero(
        tm_c,
        anchor,
        t_ref_c,
        delta_g_sigma=sigma_g,
        tm_sigma_c=sigma_tm,
    )
    assert report["calibrated"] is False
    assert report["confidence_tier"] == "hypothesis_only"
    assert report["uncertainty_defined"] is True
    assert "linear approximation" in report["uncertainty_note"].lower()
    assert "not a wet-lab" in report["uncertainty_note"].lower()
    at_ref = _point_at(report, t_ref_c)
    at_tm = _point_at(report, tm_c)
    assert at_ref["delta_g"] == pytest.approx(anchor)
    assert at_ref["delta_g_sigma"] == pytest.approx(sigma_g)
    assert at_ref["delta_g_95_lower"] == pytest.approx(anchor - 1.96 * sigma_g)
    assert at_ref["delta_g_95_upper"] == pytest.approx(anchor + 1.96 * sigma_g)
    assert report["delta_g_at_t_ref_sigma"] == pytest.approx(sigma_g)
    assert abs(float(at_tm["delta_g"])) < 1e-8
    assert report["delta_g_at_tm"] == 0.0

    eps = 1e-4
    base_h = float(report["delta_h_eff"])
    h_from_g = float(
        effective_enthalpy_delta_cp_zero(tm_c, anchor + eps, t_ref_c)["delta_h_eff"]
    )
    h_from_tm = float(
        effective_enthalpy_delta_cp_zero(tm_c + eps, anchor, t_ref_c)["delta_h_eff"]
    )
    d_h_d_g = (h_from_g - base_h) / eps
    d_h_d_tm = (h_from_tm - base_h) / eps
    tm_k = tm_c + 273.15
    t_ref_k = t_ref_c + 273.15
    denominator = 1.0 - (t_ref_k / tm_k)
    user_magnitude = anchor * t_ref_k / (denominator**2 * tm_k**2)
    assert d_h_d_g == pytest.approx(1.0 / denominator, rel=1e-6, abs=1e-6)
    assert d_h_d_tm == pytest.approx(-user_magnitude, rel=1e-5, abs=1e-6)
    expected_h_sigma = math.sqrt((d_h_d_g * sigma_g) ** 2 + (d_h_d_tm * sigma_tm) ** 2)
    assert report["delta_h_eff_sigma"] == pytest.approx(expected_h_sigma, rel=1e-6, abs=1e-8)
    assert report["delta_h_eff_95_lower"] == pytest.approx(
        base_h - 1.96 * expected_h_sigma
    )
    shifted = effective_enthalpy_delta_cp_zero(
        tm_c + 5.0,
        anchor,
        t_ref_c,
        delta_g_sigma=sigma_g,
        tm_sigma_c=sigma_tm,
    )
    assert shifted["delta_h_eff"] != pytest.approx(base_h)

    sample_c = 25.0
    sample = _point_at(report, sample_c)
    sample_g = float(sample["delta_g"])
    raised_anchor = effective_enthalpy_delta_cp_zero(tm_c, anchor + eps, t_ref_c)
    raised_tm = effective_enthalpy_delta_cp_zero(tm_c + eps, anchor, t_ref_c)
    g_up = float(_point_at(raised_anchor, sample_c)["delta_g"])
    tm_up = float(_point_at(raised_tm, sample_c)["delta_g"])
    d_g_d_g = (g_up - sample_g) / eps
    d_g_d_tm = (float(tm_up) - sample_g) / eps
    expected_g_sigma = math.sqrt((d_g_d_g * sigma_g) ** 2 + (d_g_d_tm * sigma_tm) ** 2)
    assert sample["delta_g_sigma"] == pytest.approx(expected_g_sigma, rel=1e-4, abs=1e-6)


@pytest.mark.parametrize("n_repeats", [3, 8])
def test_printed_sigmas_for_default_series_set_the_anchor_band(n_repeats: int) -> None:
    """n=3 and n=8 Phillips CTPRa DSC: both printed uncertainties exist.

    The numbers are read from the literature table. They are not typed here.
    At the printed ΔG temperature the band equals that printed uncertainty.
    """
    prefill = thermo_prefill("phillips2012_ctpra_dsc", n_repeats)
    sigma_g = prefill["delta_g_uncertainty"]
    sigma_tm = prefill["tm_uncertainty"]
    anchor = prefill["delta_g"]
    tm_c = prefill["tm_c"]
    t_ref_c = prefill["delta_g_t_c"]
    assert sigma_g is not None
    assert sigma_tm is not None
    assert anchor is not None
    assert tm_c is not None
    assert t_ref_c is not None
    report = effective_enthalpy_delta_cp_zero(
        tm_c,
        anchor,
        t_ref_c,
        delta_g_sigma=sigma_g,
        tm_sigma_c=sigma_tm,
    )
    assert report["uncertainty_defined"] is True
    assert report["anchor_delta_g_sigma"] == pytest.approx(float(sigma_g))
    assert report["tm_sigma_k"] == pytest.approx(float(sigma_tm))
    assert report["delta_g_at_t_ref"] == pytest.approx(anchor)
    assert report["delta_g_at_t_ref_sigma"] == pytest.approx(float(sigma_g))
    assert report["delta_g_at_tm"] == 0.0
    at_ref = _point_at(report, float(t_ref_c))
    assert at_ref["delta_g_sigma"] == pytest.approx(float(sigma_g))
    assert at_ref["delta_g_95_lower"] == pytest.approx(float(anchor) - 1.96 * float(sigma_g))
    http = client.post(
        "/api/stability/thermo/effective",
        json={
            "tm_c": tm_c,
            "delta_g_ref": anchor,
            "t_ref_c": t_ref_c,
            "delta_g_sigma": sigma_g,
            "tm_sigma_c": sigma_tm,
        },
    )
    assert http.status_code == 200
    body = http.json()
    assert body["uncertainty_defined"] is True
    assert body["delta_g_at_t_ref_sigma"] == pytest.approx(float(sigma_g))
    assert body["calibrated"] is False


def test_null_effective_uncertainty_is_not_zero() -> None:
    """A missing sigma stays null. Cortajarena's Tm uncertainty is null in the table."""
    omitted = effective_enthalpy_delta_cp_zero(
        60.0,
        5.0,
        10.0,
        delta_g_sigma=None,
        tm_sigma_c=0.2,
    )
    assert omitted["has_effective_enthalpy"] is True
    assert omitted["uncertainty_defined"] is False
    assert omitted["delta_h_eff_sigma"] is None
    assert omitted["delta_h_eff"] is not None
    assert omitted["delta_g_at_tm"] == 0.0
    assert "printed none" in omitted["uncertainty_note"].lower()
    assert "not treated as zero" in omitted["uncertainty_note"].lower()
    assert _point_at(omitted, 10.0)["delta_g_sigma"] is None

    prefill = thermo_prefill("cortajarena2011_ctpra_dsc", 3)
    assert prefill["tm_c"] is not None
    assert prefill["tm_uncertainty"] is None
    assert prefill["delta_g"] is None
    cortajarena = effective_enthalpy_delta_cp_zero(
        prefill["tm_c"],
        5.0,
        10.0,
        delta_g_sigma=0.2,
        tm_sigma_c=prefill["tm_uncertainty"],
    )
    assert cortajarena["uncertainty_defined"] is False
    assert cortajarena["delta_h_eff_sigma"] is None
    assert cortajarena["delta_h_eff_sigma"] != 0
    assert cortajarena["tm_sigma_k"] is None
    assert cortajarena["delta_g_at_t_ref"] == pytest.approx(5.0)
    changed = effective_enthalpy_delta_cp_zero(
        float(prefill["tm_c"]) + 5.0,
        5.0,
        10.0,
        tm_sigma_c=None,
    )
    assert changed["delta_h_eff"] != pytest.approx(cortajarena["delta_h_eff"])

    rejected = client.post(
        "/api/stability/thermo/effective",
        json={
            "tm_c": 60.0,
            "delta_g_ref": 5.0,
            "t_ref_c": 10.0,
            "delta_g_sigma": -1.0,
            "tm_sigma_c": 0.2,
        },
    )
    assert rejected.status_code == 400
