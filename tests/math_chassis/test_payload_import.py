"""Import of caller-supplied payload physical properties.

Numeric values in these tests are arbitrary fixtures. They are not measured
radii, linker sigmas, or other biological parameters.
"""

import hashlib
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


def test_payload_without_external_fields_loads():
    omitted = load_payloads([_row()])
    explicit_nulls = load_payloads(
        [
            _row(
                external_ddg=None,
                external_ddg_units=None,
                external_ddg_source=None,
                external_tool=None,
            )
        ]
    )

    for records in (omitted, explicit_nulls):
        record = records[0]
        assert record.payload_id == "alpha"
        assert record.radius_A == 12.5
        assert record.linker_sigma_A == 8.0
        assert record.external_ddg is None
        assert record.external_ddg_units is None
        assert record.external_ddg_source is None
        assert record.external_tool is None


def test_partial_external_ddg_without_units_source_or_tool_raises():
    with pytest.raises(ValueError, match="alpha") as missing:
        load_payloads([_row(external_ddg=-1.25)])
    message = str(missing.value)
    assert "external_ddg_units" in message
    assert "external_ddg_source" in message
    assert "external_tool" in message

    blank_units = _row(
        external_ddg=-1.25,
        external_ddg_units="  ",
        external_ddg_source="caller note",
        external_tool="fixture-tool",
    )
    with pytest.raises(ValueError, match="alpha") as blank:
        load_payloads([blank_units])
    assert "external_ddg_units" in str(blank.value)


def test_protein_sequence_is_checksummed_and_not_a_radius() -> None:
    records = load_payloads([_row(protein_sequence="  acdefg  ")])
    record = records[0]
    assert record.protein_sequence == "ACDEFG"
    assert record.sequence_checksum == hashlib.sha256(b"ACDEFG").hexdigest()
    assert record.radius_A == 12.5


def test_mw_requires_source_and_is_not_converted() -> None:
    with pytest.raises(ValueError, match="mw_source"):
        load_payloads([_row(mw_Da=47400.0)])
    records = load_payloads(
        [_row(mw_Da=47400.0, mw_source="caller construct calculator")]
    )
    assert records[0].mw_Da == 47400.0
    assert records[0].mw_source == "caller construct calculator"
    assert records[0].radius_A == 12.5


def test_invalid_protein_sequence_is_rejected() -> None:
    with pytest.raises(ValueError, match="alphabet"):
        load_payloads([_row(protein_sequence="ACDEFGBX")])


def test_complete_external_fusion_context_preserves_values():
    # Arbitrary fixture number. Not a tool result and not a cutoff.
    records = load_payloads(
        [
            _row(
                external_ddg=-1.25,
                external_ddg_units="kcal/mol",
                external_ddg_source="caller-supplied fixture",
                external_tool="fixture-tool",
            )
        ]
    )

    record = records[0]
    assert record.external_ddg == -1.25
    assert record.external_ddg_units == "kcal/mol"
    assert record.external_ddg_source == "caller-supplied fixture"
    assert record.external_tool == "fixture-tool"
    assert record.radius_A == 12.5
    assert record.linker_sigma_A == 8.0
