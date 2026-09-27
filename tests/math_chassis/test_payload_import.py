"""Import of caller-supplied payload physical properties.

Numeric values in these tests are arbitrary fixtures. They are not measured
radii, linker sigmas, or other biological parameters.
"""

import json
from pathlib import Path

import pytest

from origami.io import PayloadRecord, load_payloads
from origami.io.payloads import load_payloads_json


def _row(**overrides: object) -> dict:
    row: dict = {
        "payload_id": "alpha",
        "role": "upstream",
        "fusion_terminus": "N",
        "repeat_index": 0,
        "radius_A": 12.5,
        "linker_sigma_A": 8.0,
    }
    row.update(overrides)
    return row


def test_two_valid_rows():
    rows = [
        _row(
            payload_id="alpha",
            role="upstream",
            fusion_terminus="N",
            repeat_index=0,
            radius_A=12.5,
            linker_sigma_A=8.0,
            structure_id="local-alpha",
        ),
        _row(
            payload_id="beta",
            role="downstream",
            fusion_terminus="C",
            repeat_index=3,
            radius_A=4.0,
            linker_sigma_A=1.5,
        ),
    ]

    records = load_payloads(rows)

    assert records == [
        PayloadRecord(
            payload_id="alpha",
            role="upstream",
            fusion_terminus="N",
            repeat_index=0,
            radius_A=12.5,
            linker_sigma_A=8.0,
            structure_id="local-alpha",
        ),
        PayloadRecord(
            payload_id="beta",
            role="downstream",
            fusion_terminus="C",
            repeat_index=3,
            radius_A=4.0,
            linker_sigma_A=1.5,
            structure_id=None,
        ),
    ]


def test_missing_radius_names_payload_and_field():
    omitted = _row()
    del omitted["radius_A"]
    with pytest.raises(ValueError, match="alpha") as missing:
        load_payloads([omitted])
    assert "radius_A" in str(missing.value)

    null_radius = _row(radius_A=None)
    with pytest.raises(ValueError, match="radius_A") as null:
        load_payloads([null_radius])
    assert "alpha" in str(null.value)


def test_missing_linker_names_payload_and_field():
    omitted = _row()
    del omitted["linker_sigma_A"]
    with pytest.raises(ValueError, match="alpha") as missing:
        load_payloads([omitted])
    assert "linker_sigma_A" in str(missing.value)

    null_linker = _row(linker_sigma_A=None)
    with pytest.raises(ValueError, match="linker_sigma_A") as null:
        load_payloads([null_linker])
    assert "alpha" in str(null.value)


def test_nonpositive_radius_is_rejected():
    with pytest.raises(ValueError, match="radius_A"):
        load_payloads([_row(radius_A=0)])
    with pytest.raises(ValueError, match="alpha"):
        load_payloads([_row(radius_A=-3.0)])


def test_bad_terminus_is_rejected():
    with pytest.raises(ValueError, match="fusion_terminus"):
        load_payloads([_row(fusion_terminus="X")])
    with pytest.raises(ValueError, match="alpha"):
        load_payloads([_row(fusion_terminus="n")])


def test_nonpositive_linker_and_negative_repeat_are_rejected():
    with pytest.raises(ValueError, match="linker_sigma_A"):
        load_payloads([_row(linker_sigma_A=0)])
    with pytest.raises(ValueError, match="repeat_index"):
        load_payloads([_row(repeat_index=-1)])


def test_load_payloads_json_reads_caller_supplied_rows(tmp_path: Path):
    path = tmp_path / "payloads.json"
    path.write_text(
        json.dumps(
            [
                _row(payload_id="alpha", structure_id="local-alpha"),
                _row(payload_id="beta", fusion_terminus="C", repeat_index=1),
            ]
        ),
        encoding="utf-8",
    )

    records = load_payloads_json(path)

    assert [record.payload_id for record in records] == ["alpha", "beta"]
    assert records[0].structure_id == "local-alpha"
    assert records[1].fusion_terminus == "C"
    assert records[1].repeat_index == 1
