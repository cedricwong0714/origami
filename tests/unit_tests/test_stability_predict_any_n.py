"""Length-model Tm and ΔG are available at repeat counts without a table row."""

from origami.api.stability import literature_confirm, stability_at_n


def test_n_14_prediction_matches_the_confirmation_row() -> None:
    """n = 14 has no Phillips table cell. The length fit still has a value.

    Scientific basis: the confirmation payload already evaluates the
    Phillips 2012 CTPRa DSC length model at n = 14.
    Failure mode: the calculator refuses n = 14 because the paper has no row.
    """
    confirm = literature_confirm(37.0)
    row = next(item for item in confirm["rows"] if item["n_repeats"] == 14)
    predicted = stability_at_n(14, 37.0)
    assert predicted["calibrated"] is False
    assert predicted["row"]["tm_C"] == row["tm_C"]
    assert predicted["row"]["delta_g"] == row["delta_g"]
    assert predicted["anchor_temperature_C"] == 10.0
    assert predicted["row"]["tm_C"] is not None
    assert predicted["row"]["delta_g"] is not None


def test_a_repeat_count_outside_3_to_24_is_rejected() -> None:
    try:
        stability_at_n(2, 37.0)
    except ValueError as exc:
        assert "n_repeats" in str(exc)
    else:
        raise AssertionError("n = 2 was accepted")
