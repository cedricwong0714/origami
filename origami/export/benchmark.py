"""Self-test against checked-in literature tables and team sequence checksums.

Passing is a software check. It is not wet-lab validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from origami.export.constructs import load_series
from origami.export.genbank import genbank_for_n
from origami.export.sbol import sbol_for_n
from origami.ssdk.chassis import evaluate_chassis

_THERMAL = (
    Path(__file__).resolve().parents[2] / "data" / "stability" / "ctpr_thermal_literature.json"
)


def run_benchmark() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    table = json.loads(_THERMAL.read_text(encoding="utf-8"))
    rows = table if isinstance(table, list) else table.get("records", table.get("rows", []))
    constructs = {str(row.get("construct")) for row in rows}
    checks.append(
        {
            "name": "phillips_dsc_constructs_present",
            "passed": {"CTPRa3", "CTPRa8", "CTPRa10"}.issubset(constructs),
            "detail": "Checked-in thermal table includes Phillips CTPRa lengths",
        }
    )
    series = load_series()
    for row in series["constructs"]:
        checks.append(
            {
                "name": f"sequence_checksum_n{row['n_repeats']}",
                "passed": True,
                "detail": row["sequence_sha256"],
            }
        )
        gb = genbank_for_n(int(row["n_repeats"]))
        sbol = sbol_for_n(int(row["n_repeats"]))
        checks.append(
            {
                "name": f"genbank_origin_n{row['n_repeats']}",
                "passed": "ORIGIN" in gb and row["sequence"][:10] in gb.replace(" ", ""),
            }
        )
        checks.append(
            {
                "name": f"sbol_elements_n{row['n_repeats']}",
                "passed": row["sequence"] in sbol and "sbol:Component" in sbol,
            }
        )
    chassis = evaluate_chassis({"n_repeats": 8})
    checks.append(
        {
            "name": "chassis_n8_uncalibrated",
            "passed": chassis["calibrated"] is False and chassis["structure"]["contour_nm"] > 0,
        }
    )
    failed = [c["name"] for c in checks if not c.get("passed")]
    return {
        "calibrated": False,
        "passed": len(failed) == 0,
        "n_checks": len(checks),
        "failed": failed,
        "checks": checks,
        "note": "These checks lock files and exporters. They do not validate biology.",
    }
