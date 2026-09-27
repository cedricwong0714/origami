"""Loader tests for caller-supplied thermal-table JSON.

Numbers, DOIs, and citation strings in these tests are arbitrary fixtures.
They are not measured melting temperatures, folding free energies, or
literature citations.
"""

import json
from pathlib import Path

import pytest

from origami.stability import ThermalObservation, load_thermal_table


def _row(**overrides: object) -> dict:
    row: dict = {
        "record_id": "rec-1",
        "doi": "10.0000/fixture",
        "citation": "fixture citation, not a publication",
        "year": 2000,
        "construct": "fixture-construct",
        "n_repeats": 2,
        "observable": "Tm_C",
        "value": 1.5,
        "units": "C",
        "uncertainty": None,
        "method": "fixture-method",
        "buffer": "fixture-buffer",
        "pH": None,
        "figure_or_table": "Table S0",
        "peer_reviewed": True,
        "data_class": "literature",
    }
    row.update(overrides)
    return row


def _write(tmp_path: Path, payload: object, name: str = "thermal.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_valid_literature_row_kept(tmp_path: Path):
    path = _write(tmp_path, [_row()])

    records = load_thermal_table(path)

    assert records == [
        ThermalObservation(
            record_id="rec-1",
            doi="10.0000/fixture",
            citation="fixture citation, not a publication",
            year=2000,
            construct="fixture-construct",
            n_repeats=2,
            observable="Tm_C",
            value=1.5,
            units="C",
            uncertainty=None,
            method="fixture-method",
            buffer="fixture-buffer",
            pH=None,
            figure_or_table="Table S0",
            peer_reviewed=True,
            data_class="literature",
        )
    ]


def test_synthetic_row_dropped_by_default(tmp_path: Path):
    path = _write(
        tmp_path,
        [
            _row(record_id="lit-1", data_class="literature"),
            _row(
                record_id="syn-1",
                data_class="synthetic_fixture",
                peer_reviewed=False,
            ),
        ],
    )

    records = load_thermal_table(path)

    assert [record.record_id for record in records] == ["lit-1"]
    assert records[0].data_class == "literature"


def test_synthetic_row_kept_when_allow_synthetic(tmp_path: Path):
    path = _write(
        tmp_path,
        [
            _row(record_id="lit-1", data_class="literature"),
            _row(
                record_id="syn-1",
                data_class="synthetic_fixture",
                peer_reviewed=False,
            ),
        ],
    )

    records = load_thermal_table(path, allow_synthetic=True)

    assert [record.record_id for record in records] == ["lit-1", "syn-1"]
    assert records[1].data_class == "synthetic_fixture"


def test_missing_doi_raises(tmp_path: Path):
    omitted = _row(record_id="rec-missing-doi")
    del omitted["doi"]
    path = _write(tmp_path, [omitted])

    with pytest.raises(ValueError, match="rec-missing-doi") as exc_info:
        load_thermal_table(path)

    assert "doi" in str(exc_info.value)


def test_bad_observable_raises(tmp_path: Path):
    path = _write(tmp_path, [_row(record_id="rec-bad-obs", observable="folding")])

    with pytest.raises(ValueError, match="rec-bad-obs") as exc_info:
        load_thermal_table(path)

    assert "observable" in str(exc_info.value)


def test_empty_file_and_empty_rows_return_empty_list(tmp_path: Path):
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    wrapped = _write(tmp_path, {"rows": []}, name="wrapped.json")

    assert load_thermal_table(empty) == []
    assert load_thermal_table(wrapped) == []


def test_rows_object_keeps_literature_row(tmp_path: Path):
    path = _write(tmp_path, {"rows": [_row(record_id="wrapped")]})

    records = load_thermal_table(path)

    assert [record.record_id for record in records] == ["wrapped"]


def test_n_repeats_below_one_raises(tmp_path: Path):
    path = _write(tmp_path, [_row(record_id="rec-repeats", n_repeats=0)])

    with pytest.raises(ValueError, match="rec-repeats") as exc_info:
        load_thermal_table(path)

    assert "n_repeats" in str(exc_info.value)


def test_tm_units_must_be_c(tmp_path: Path):
    path = _write(tmp_path, [_row(record_id="rec-units", units="K")])

    with pytest.raises(ValueError, match="rec-units") as exc_info:
        load_thermal_table(path)

    assert "C" in str(exc_info.value)


def test_delta_g_units_are_stored_as_stated(tmp_path: Path):
    path = _write(
        tmp_path,
        [
            _row(
                record_id="rec-dg",
                observable="delta_G",
                value=3.25,
                units="kJ/mol",
                uncertainty=0.5,
            )
        ],
    )

    records = load_thermal_table(path)

    assert len(records) == 1
    assert records[0].observable == "delta_G"
    assert records[0].units == "kJ/mol"
    assert records[0].value == 3.25
    assert records[0].uncertainty == 0.5
