"""Score many repeat counts. One chassis call per CSV row."""

from __future__ import annotations

import csv
import io
from typing import Any

from origami.ssdk.chassis import ChassisError, evaluate_chassis


def batch_chassis_csv(text: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or "n_repeats" not in reader.fieldnames:
        raise ChassisError("CSV must have an n_repeats column")
    rows: list[dict[str, Any]] = []
    for raw in reader:
        body = dict(extra or {})
        body["n_repeats"] = int(raw["n_repeats"])
        report = evaluate_chassis(body)
        rows.append(
            {
                "n_repeats": report["n_repeats"],
                "contour_nm": report["structure"]["contour_nm"],
                "tm_C": report["stability"]["tm_C"],
                "delta_g": report["stability"]["delta_g"],
                "clash_computable": report["docking"].get("clash_computable"),
                "calibrated": False,
            }
        )
    rows.sort(key=lambda r: (r["tm_C"] is None, -(r["tm_C"] or 0.0)))
    return {
        "calibrated": False,
        "n_rows": len(rows),
        "ranked_by": "Phillips Tm when present, else n_repeats",
        "rows": rows,
        "note": "Ranking uses the literature length curve. It is not a wet ranking.",
    }
