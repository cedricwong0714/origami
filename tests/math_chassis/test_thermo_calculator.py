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

    if not has_any_dh:
        assert prefill["delta_h"] is None
    if not has_any_dcp:
        assert prefill["delta_cp"] is None

    if not (has_any_dh and has_any_dcp):
        assert prefill["delta_h"] is None or not has_any_dh
        assert prefill["delta_cp"] is None or not has_any_dcp
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
    """A missing ΔHcal or ΔCp does not become a curve of zeros."""
    for kwargs in (
        {"tm_c": 60.0, "delta_h": None, "delta_cp": 0.2},
        {"tm_c": 60.0, "delta_h": 10.0, "delta_cp": None},
        {"tm_c": None, "delta_h": None, "delta_cp": None},
    ):
        report = gibbs_helmholtz_curves(**kwargs)
        assert report["has_curve"] is False
        assert report["calibrated"] is False
        assert report["points"] == []
        assert report["delta_g"] is None
        assert report["delta_h"] is None
        assert report["delta_s"] is None
        assert report["delta_g_at_tm"] is None
        assert report["missing_inputs"]
        assert "calorimetry inputs are missing" in report["message"].lower()
        encoded = json.dumps(report["points"])
        assert encoded == "[]"


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
        "delta_h",
        "delta_H",
        "delta_hcal",
        "delta_Hcal",
        "delta_cp",
        "delta_Cp",
        "DeltaCp",
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
        prefill = thermo_prefill("phillips2012_ctpra_dsc", n_repeats)
        assert prefill["tm_status"] == "cited"
        assert prefill["tm_c"] == tm_raw["value"]
        assert prefill["tm_units"] == tm_raw["units"]
        assert prefill["delta_g"] == dg_raw["value"]
        assert prefill["delta_g_units"] == dg_raw["units"]
        assert prefill["delta_h"] is None
        assert prefill["delta_cp"] is None
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
    assert prefill["delta_h"] is None
    assert prefill["delta_cp"] is None
    assert prefill["calibrated"] is False
    assert prefill["interpolated"] is False


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
    assert payload["delta_h"] is None
    assert payload["delta_cp"] is None
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
        assert payload["delta_h"] is None
        assert payload["delta_cp"] is None
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
    assert extrapolated.json()["delta_h"] is None

    missing_curve = client.post(
        "/api/stability/thermo/curves",
        json={"tm_c": _TM_C, "delta_cp": _DELTA_CP},
    )
    assert missing_curve.status_code == 400
    assert "missing" in missing_curve.json()["detail"].lower()
    assert "points" not in missing_curve.json()

    null_curve = client.post(
        "/api/stability/thermo/curves",
        json={"tm_c": _TM_C, "delta_h": None, "delta_cp": _DELTA_CP},
    )
    assert null_curve.status_code == 400
    assert "points" not in null_curve.json()

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
