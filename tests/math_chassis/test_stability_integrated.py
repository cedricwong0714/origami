"""Thermal gate integrated with the repeat-count scan.

Temperatures, payload radii, and linker widths in this file are synthetic
fixtures. They are not literature melting temperatures, measured payload
sizes, or other biological constants. data_class marks that fact. The
production table loader is not given allow_synthetic=True; a test that
needs a synthetic file row calls load_thermal_table itself.
"""

import inspect
import json
from pathlib import Path

import pytest

from origami.design_engine.active_learning import recommend
from origami.engine import ClaspDesignEngine, Observation, run_design
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN
from origami.stability.gate import ThermalRow
from origami.stability.table import load_thermal_table

# recommend()'s existing steric mask. Not a new biological threshold.
_CLASH_LIMIT = float(inspect.signature(recommend).parameters["clash_limit"].default)


def _tm(n_repeats: int, value: float, uncertainty: float | None = None) -> ThermalRow:
    """Synthetic Tm row. The number is a fixture, not a cited measurement."""
    return ThermalRow(
        n_repeats=n_repeats,
        observable="Tm_C",
        value=value,
        units="C",
        uncertainty=uncertainty,
        data_class="synthetic_fixture",
    )


def _literature_shaped_row(**overrides: object) -> dict[str, object]:
    """JSON object the thermal loader accepts.

    The doi, citation, and value are fixture text. They are not a paper
    and not a measured melting temperature.
    """
    row: dict[str, object] = {
        "record_id": "fixture-1",
        "doi": "10.0000/fixture",
        "citation": "fixture citation, not a publication",
        "year": 2000,
        "construct": "fixture-construct",
        "n_repeats": 4,
        "observable": "Tm_C",
        "value": 1.0,
        "units": "C",
        "uncertainty": None,
        "method": "fixture-method",
        "buffer": "fixture-buffer",
        "pH": None,
        "figure_or_table": "Table S0",
        "peer_reviewed": False,
        "data_class": "literature",
    }
    row.update(overrides)
    return row


def _steric_p_by_n(radii: list[float] | None = None) -> dict[int, float]:
    kwargs: dict[str, object] = {}
    if radii is not None:
        kwargs["payload_radii_A"] = radii
    preview = ClaspDesignEngine(**kwargs).run()
    return {n: float(p) for n, p in zip(preview.candidates, preview.p_instability)}


def test_no_thermal_rows_keeps_the_steric_recommendation() -> None:
    # Rule under test: thermal_rows is None, so the gate is skipped.
    steric_only = ClaspDesignEngine().run()
    assert steric_only.next_experiment is not None
    report = run_design("omit-table", 8)
    explicit = run_design("omit-table", 8, thermal_rows=None, t_assay_C=None)

    assert report.stability_state == "omitted"
    assert report.stability_tier == "omitted"
    assert report.stability_omitted == ["tm_table"]
    assert report.tm_C is None
    assert report.tm_interval_low is None
    assert report.tm_interval_high is None
    assert report.calibrated is False
    assert report.next_n == steric_only.next_experiment.n_repeats
    assert explicit.next_n == report.next_n
    assert explicit.to_dict()["stability_state"] == "omitted"
    assert "tm_table" in explicit.stability_omitted


def test_two_passing_tm_rows_recommend_one_of_them() -> None:
    # 80 C and 70 C are fixtures. Assay 37 C is below both, so both pass.
    rows = [_tm(4, 80.0, uncertainty=1.0), _tm(6, 70.0, uncertainty=2.0)]
    clash = _steric_p_by_n()
    assert clash[4] < _CLASH_LIMIT
    assert clash[6] < _CLASH_LIMIT

    report = run_design("both-pass", 4, thermal_rows=rows, t_assay_C=37.0)

    assert report.next_n in {4, 6}
    assert report.stability_state == "pass"
    assert report.stability_tier == "literature_prior"
    assert report.tm_C == 80.0
    assert report.tm_interval_low == 79.0
    assert report.tm_interval_high == 81.0
    assert report.stability_omitted == []
    assert report.calibrated is False


def test_hot_steric_best_is_not_recommended() -> None:
    baseline = run_design("steric-only", 8)
    best = baseline.next_n
    assert best is not None
    passer = 8 if best != 8 else 12
    clash = _steric_p_by_n()
    assert clash[best] < _CLASH_LIMIT
    assert clash[passer] < _CLASH_LIMIT

    # Assay 50 C is above the fixture Tm at the steric recommendation and
    # below the fixture Tm at the other length.
    rows = [_tm(best, 30.0), _tm(passer, 90.0)]
    report = run_design("avoid-hot", passer, thermal_rows=rows, t_assay_C=50.0)

    assert report.next_n == passer
    assert report.next_n != best
    assert report.stability_state == "pass"
    assert report.stability_tier == "literature_prior"
    assert report.tm_C == 90.0
    assert report.calibrated is False
    assert any(
        f"n={best} infeasible" in warning and "thermal gate fail" in warning
        for warning in report.warnings
    )


def test_all_thermal_failures_withhold_next_n() -> None:
    # One failing fixture Tm at every library length. 25 C is not a measurement.
    rows = [_tm(n, 25.0) for n in range(N_REPEATS_MIN, N_REPEATS_MAX + 1)]
    report = run_design("all-fail", 8, thermal_rows=rows, t_assay_C=40.0)

    assert report.next_n is None
    assert report.stability_state == "fail"
    assert report.stability_tier == "literature_prior"
    assert report.tm_C == 25.0
    assert report.tm_interval_low == 25.0
    assert report.tm_interval_high == 25.0
    assert report.calibrated is False
    fail_lines = [warning for warning in report.warnings if " infeasible:" in warning]
    assert len(fail_lines) == N_REPEATS_MAX - N_REPEATS_MIN + 1
    assert all("thermal gate fail" in warning for warning in fail_lines)
    assert any("next_n is None" in warning for warning in report.warnings)


def test_n_outside_cited_range_is_not_chosen() -> None:
    baseline = run_design("steric-only", 8)
    best = baseline.next_n
    assert best is not None
    passer = 6 if best != 6 else 10
    assert passer != best

    # A single cited fixture. Lengths other than `passer` are outside the
    # cited repeat range, so they are extrapolated and not feasible.
    report = run_design(
        "in-range",
        passer,
        thermal_rows=[_tm(passer, 80.0, uncertainty=1.0)],
        t_assay_C=37.0,
    )

    assert report.next_n == passer
    assert report.next_n != best
    assert report.stability_state == "pass"
    assert report.stability_tier == "literature_prior"
    assert report.tm_C == 80.0
    assert any(
        f"n={best} infeasible" in warning and "extrapolated" in warning
        for warning in report.warnings
    )


def test_steric_refusal_and_thermal_fail_are_different_n() -> None:
    # 50 Å and 10 Å are fixture sizes, not measured payload dimensions.
    radii = [50.0, 50.0]
    clash = _steric_p_by_n(radii)
    refused = [n for n, p in clash.items() if not p < _CLASH_LIMIT]
    allowed = [n for n, p in clash.items() if p < _CLASH_LIMIT]
    assert refused
    assert len(allowed) >= 2
    thermal_fail_n = allowed[0]
    passer = allowed[-1]
    steric_fail_n = refused[0]
    assert len({thermal_fail_n, passer, steric_fail_n}) == 3

    rows = [
        _tm(thermal_fail_n, 30.0),
        _tm(steric_fail_n, 90.0),
        _tm(passer, 90.0),
    ]
    payloads = [
        {
            "payload_id": "alpha",
            "role": "fixture",
            "fusion_terminus": "N",
            "repeat_index": 0,
            "radius_A": 50.0,
            "linker_sigma_A": 10.0,
        },
        {
            "payload_id": "beta",
            "role": "fixture",
            "fusion_terminus": "C",
            "repeat_index": passer - 1,
            "radius_A": 50.0,
            "linker_sigma_A": 10.0,
        },
    ]
    report = run_design(
        "split-gates",
        passer,
        payloads=payloads,
        thermal_rows=rows,
        t_assay_C=50.0,
    )

    assert report.next_n == passer
    assert report.next_n != thermal_fail_n
    assert report.next_n != steric_fail_n
    assert any(
        f"n={thermal_fail_n} infeasible" in warning and "thermal gate fail" in warning
        for warning in report.warnings
    )
    assert any(
        f"n={steric_fail_n} infeasible" in warning and "steric refusal" in warning
        for warning in report.warnings
    )
    steric_line = next(
        warning for warning in report.warnings if f"n={steric_fail_n} infeasible" in warning
    )
    thermal_line = next(
        warning
        for warning in report.warnings
        if f"n={thermal_fail_n} infeasible" in warning
    )
    assert "thermal gate fail" not in steric_line
    assert "steric refusal" not in thermal_line


@pytest.mark.parametrize("acquisition", ["ucb", "ei", "entropy"])
def test_acquisition_runs_only_on_the_feasible_subset(acquisition: str) -> None:
    engine = ClaspDesignEngine(n_min=4, n_max=7, acquisition=acquisition)
    engine.add_observation(Observation(n_repeats=4, y=0.2, source="user_entered"))
    # n=4 fails the fixture assay. n=5 has no row, so it is not interpolated.
    # n=6 and n=7 pass. 20 C and 80 C are fixtures.
    rows = [_tm(4, 20.0), _tm(6, 80.0), _tm(7, 80.0)]
    result = engine.run(thermal_rows=rows, t_assay_C=40.0)

    assert result.next_experiment is not None
    assert result.next_experiment.n_repeats in {6, 7}
    assert result.thermal_by_n is not None
    assert result.thermal_by_n[4].state == "fail"
    assert result.thermal_by_n[5].state == "omitted"
    assert result.thermal_by_n[6].state == "pass"
    assert result.thermal_by_n[7].state == "pass"


def test_delta_g_only_rows_do_not_recommend_a_length() -> None:
    # -4 kcal/mol is a fixture label, not a folding free energy used as Tm.
    rows = [
        ThermalRow(
            n_repeats=n,
            observable="delta_G",
            value=-4.0,
            units="kcal/mol",
            uncertainty=None,
            data_class="synthetic_fixture",
        )
        for n in (4, 5)
    ]
    result = ClaspDesignEngine(n_min=4, n_max=5).run(thermal_rows=rows, t_assay_C=25.0)
    assert result.next_experiment is None
    assert result.thermal_by_n is not None
    assert result.thermal_by_n[4].state == "omitted"
    assert result.thermal_by_n[4].tm_C is None


def test_to_dict_is_json_serializable() -> None:
    report = run_design(
        "json",
        4,
        thermal_rows=[_tm(4, 80.0, uncertainty=1.0)],
        t_assay_C=37.0,
    )
    payload = report.to_dict()
    assert json.loads(json.dumps(payload)) == payload
    for key in (
        "tm_C",
        "tm_interval_low",
        "tm_interval_high",
        "stability_state",
        "stability_tier",
        "stability_omitted",
    ):
        assert key in payload
    assert payload["calibrated"] is False
    assert payload["stability_state"] == "pass"
    assert payload["stability_tier"] == "literature_prior"
    assert type(payload["tm_C"]) is float
    # Only n=4 has a passing fixture Tm, so the recommendation is that length.
    assert payload["next_n"] == 4
    assert type(payload["next_n"]) is int

    omitted = run_design("json-omit", 8)
    omitted_payload = omitted.to_dict()
    assert json.loads(json.dumps(omitted_payload)) == omitted_payload
    assert type(omitted_payload["next_n"]) is int
    assert omitted_payload["stability_state"] == "omitted"
    assert omitted_payload["stability_omitted"] == ["tm_table"]


def test_table_path_drops_synthetic_rows(tmp_path: Path) -> None:
    best = run_design("steric-only", 8).next_n
    assert best is not None
    # 95 C would pass an assay of 10 C if the row were kept. It must not be
    # kept by the production loader.
    path = tmp_path / "thermal.json"
    path.write_text(
        json.dumps(
            [
                _literature_shaped_row(
                    record_id="syn-only",
                    n_repeats=best,
                    value=95.0,
                    data_class="synthetic_fixture",
                )
            ]
        ),
        encoding="utf-8",
    )

    via_path = run_design("path", best, thermal_table_path=path, t_assay_C=10.0)
    assert via_path.next_n is None
    assert via_path.stability_state == "omitted"
    assert via_path.tm_C is None
    assert "tm_table" not in via_path.stability_omitted
    assert "Tm_C" in via_path.stability_omitted

    loaded = load_thermal_table(path, allow_synthetic=True)
    via_memory = run_design("memory", best, thermal_rows=loaded, t_assay_C=10.0)
    assert via_memory.next_n == best
    assert via_memory.stability_state == "pass"
    assert via_memory.tm_C == 95.0
    assert via_memory.calibrated is False


def test_literature_class_fixture_on_a_path_can_pass(tmp_path: Path) -> None:
    # data_class is "literature" so the production loader keeps the row.
    # The value is still a fixture, not a cited melting temperature.
    path = tmp_path / "kept.json"
    path.write_text(
        json.dumps([_literature_shaped_row(n_repeats=6, value=80.0, uncertainty=1.0)]),
        encoding="utf-8",
    )
    report = run_design("kept", 6, thermal_table_path=path, t_assay_C=37.0)
    assert report.next_n == 6
    assert report.stability_state == "pass"
    assert report.tm_C == 80.0
    assert report.tm_interval_low == 79.0
    assert report.tm_interval_high == 81.0
    assert report.calibrated is False


def test_t_assay_is_required_when_rows_are_supplied() -> None:
    with pytest.raises(ValueError, match="t_assay_C"):
        run_design("missing-assay", 8, thermal_rows=[_tm(4, 80.0)])
