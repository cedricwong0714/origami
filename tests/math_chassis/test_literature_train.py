"""Residual GP on Phillips 2012 CTPRa DSC, which this lab will not measure.

The y values are the printed table cells. They are not surrogate
luminescence and they are not a fusion assay. A passing test is not
scientific validation.
"""

from __future__ import annotations

from origami.ssdk.learn import learn_ssdk
from origami.ssdk.literature_train import _fit_track, train_literature
from origami.stability.length_fit import fit_named_delta_g, fit_named_tm
from origami.stability.series import (
    PHILLIPS_2012_CTPRA_DSC,
    companion_delta_g_rows,
    load_named_series,
)
from origami.stability.table import ThermalObservation


def _printed(rows: list[ThermalObservation]) -> dict[int, tuple[float, float | None]]:
    return {row.n_repeats: (row.value, row.uncertainty) for row in rows}


def test_literature_tracks_match_the_phillips_table_and_stay_unlabeled_as_lab():
    report = train_literature()
    assert report["calibrated"] is False
    assert report["lab_will_measure_this"] is False
    assert report["confidence_tier"] == "hypothesis_only"
    tm_rows = load_named_series(PHILLIPS_2012_CTPRA_DSC)
    dg_rows = companion_delta_g_rows(PHILLIPS_2012_CTPRA_DSC)
    for key, source in (("tm", tm_rows), ("delta_g", dg_rows)):
        track = report[key]
        expected = _printed(source)
        assert track["calibrated"] is False
        assert track["gp_fitted"] is True
        assert track["training_lengths"] == sorted(expected)
        assert track["n_training"] == len(expected)
        assert "mean printed uncertainty" in track["noise_note"]
        for row in track["training_rows"]:
            value, sigma = expected[row["n_repeats"]]
            assert row["y"] == value
            assert row["sigma"] == sigma
            assert row["source"] == "literature"
            assert row["doi"] == "10.1002/pro.2018"
            assert row["sigma"] != 0 or sigma == 0
        nxt = track["next_n_if_this_observable_were_measured"]
        assert nxt not in expected
        assert 3 <= nxt <= 24
        assert "not a wet-lab instruction" in track["next_reason"]
        assert "DSC" in track["next_reason"]
        assert track["next_past_longest_cited_length"] is True
        assert "extrapolation" in track["next_reason"]
    # Tm residuals sit inside the printed uncertainties, so the kernel
    # variance hits the optimizer floor and UCB walks to the last candidate.
    assert "optimizer floor" in report["tm"]["identifiability_note"]
    assert report["tm"]["next_n_if_this_observable_were_measured"] == 24
    assert (
        "not evidence that a longer scaffold is more informative"
        in report["tm"]["next_reason"]
    )


def test_surrogate_rows_do_not_enter_the_literature_tracks():
    alone = train_literature()
    mixed = learn_ssdk(
        {
            "observations": [
                {"n_repeats": 8, "y": 0.2, "sigma": 0.01, "source": "surrogate"},
            ]
        }
    )
    trained = mixed["literature_training"]
    assert trained["tm"]["training_rows"] == alone["tm"]["training_rows"]
    assert trained["delta_g"]["training_rows"] == alone["delta_g"]["training_rows"]
    assert all(row["source"] == "literature" for row in trained["tm"]["training_rows"])
    assert mixed["gp_fitted"] is False
    assert mixed["n_observations"] == 1
    assert trained["tm"]["gp_fitted"] is True


def _fixture(n_repeats: int, value: float) -> ThermalObservation:
    return ThermalObservation(
        record_id=f"fixture_missing_sigma_{n_repeats}",
        doi="10.1000/fixture",
        citation="synthetic fixture, not a paper",
        year=2026,
        construct=f"FIXTURE{n_repeats}",
        n_repeats=n_repeats,
        observable="Tm_C",
        value=value,
        units="C",
        uncertainty=None,
        method="fixture",
        buffer="fixture",
        pH=None,
        figure_or_table="none",
        peer_reviewed=False,
        data_class="synthetic_fixture",
    )


def test_a_missing_printed_sigma_is_not_stored_as_zero():
    rows = [_fixture(3, 1.0), _fixture(4, 1.1), _fixture(5, 1.2)]

    class _Prediction:
        def __init__(self, value: float) -> None:
            self.value = value

    class _Fit:
        def predict(self, n_repeats: int) -> _Prediction:
            return _Prediction(float(n_repeats))

    track = _fit_track(rows, _Fit(), "Tm_C", "C")  # type: ignore[arg-type]
    assert [row["sigma"] for row in track["training_rows"]] == [None, None, None]
    assert "not stored as zero" in track["noise_note"]


def test_named_fits_used_as_physics_are_the_canonical_series():
    tm = fit_named_tm(PHILLIPS_2012_CTPRA_DSC)
    dg = fit_named_delta_g(PHILLIPS_2012_CTPRA_DSC)
    report = train_literature()
    tm_row = next(row for row in report["tm"]["training_rows"] if row["n_repeats"] == 8)
    dg_row = next(
        row for row in report["delta_g"]["training_rows"] if row["n_repeats"] == 8
    )
    assert tm_row["physics"] == tm.predict(8).value
    assert dg_row["physics"] == dg.predict(8).value
    assert tm_row["y"] == 74
    assert dg_row["y"] == 14.3
