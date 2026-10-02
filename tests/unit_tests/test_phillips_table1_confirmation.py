"""Lock checked-in Phillips 2012 DSC/CD values to the printed Table I.

Source: Phillips et al. 2012 (Protein Sci.), Table I, retrieved from the
published page text during the stability confirmation. This confirms
transcription only; it is not scientific validation of the length models.
"""

import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "data/stability/ctpr_thermal_literature.json"

# construct: (DSC Tm degC, +/-, DG10C kcal/mol, +/-)
TABLE_I_DSC = {
    "CTPRa2": (53, 0.3, 3.2, 0.6),
    "CTPRa3": (63, 0.6, 4.8, 0.4),
    "CTPRa4": (68, 0.1, 4.2, 1.1),
    "CTPRa6": (71, 1.0, 7.7, 0.2),
    "CTPRa8": (74, 0.5, 14.3, 1.5),
    "CTPRa10": (74, 1.3, 23.4, 2.1),
    "CTPR2": (68, 0.04, 7.6, 1.1),
    "CTPR3": (76, 0.1, 12.0, 0.7),
}


def _rows():
    d = json.loads(DATA.read_text())
    return d if isinstance(d, list) else d.get("records", d.get("rows"))


@pytest.mark.parametrize("construct", sorted(TABLE_I_DSC))
def test_dsc_rows_match_printed_table(construct):
    tm, tm_err, dg, dg_err = TABLE_I_DSC[construct]
    mine = [
        r
        for r in _rows()
        if r["construct"] == construct
        and r["record_id"].startswith("phillips2012")
        and r["method"] == "DSC"
    ]
    got = {r["observable"]: r for r in mine}
    assert got["Tm_C"]["value"] == tm and got["Tm_C"]["uncertainty"] == tm_err
    assert got["delta_G"]["value"] == dg and got["delta_G"]["uncertainty"] == dg_err


# construct: (dH_cal kcal/mol, +/-) from Phillips 2012 Table I, DSC model-free column
TABLE_I_DH = {
    "CTPRa2": (44, 4), "CTPRa3": (65, 3), "CTPRa4": (73, 7), "CTPRa5": (95, 5),
    "CTPRa6": (116, 2), "CTPRa8": (178, 8), "CTPRa10": (250, 11),
    "CTPR2": (73, 0.4), "CTPR3": (108, 1),
}


@pytest.mark.parametrize("construct", sorted(TABLE_I_DH))
def test_delta_hcal_matches_printed_table(construct):
    rows = [
        r for r in _rows()
        if r["construct"] == construct and r["record_id"].startswith("phillips2012")
        and r["record_id"].endswith("_tm_dsc")
    ]
    assert len(rows) == 1
    dh, err = TABLE_I_DH[construct]
    assert rows[0]["delta_Hcal"] == dh and rows[0]["delta_Hcal_uncertainty"] == err
    assert rows[0]["delta_Hcal_units"] == "kcal mol-1"
    assert "delta_Cp" not in rows[0]
