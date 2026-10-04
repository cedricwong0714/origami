"""Plate-reader CSV to SSDK learn result.

Imports a plate CSV (blank-corrected per batch, see origami.lab.plate_reader)
and passes the rows to ``learn_ssdk`` as observations. Optional ``output``
and ``fidelity`` columns stay on those rows. Every other learn field
(construct, kinetics, sequence, quantify_luminescence, learner) comes from
the caller options. Observations are never taken from those options.

Observation units stay RLU unless ``quantify_luminescence`` converts them.
Only rows with an integer n_repeats inside n_min..n_max are accepted by the
learner, and an out-of-range row raises rather than being dropped.
The result keeps the learner's calibrated=False and hypothesis_only tier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from origami.lab.plate_reader import load_plate_csv
from origami.ssdk.learn import learn_ssdk


def learn_from_plate(path: str | Path, **options: Any) -> dict[str, Any]:
    """Run the SSDK learner on blank-corrected plate observations."""
    plate = load_plate_csv(path)
    body = dict(options)
    if "observations" in body:
        raise ValueError("observations come from the plate file; do not pass them")
    body["observations"] = [
        {
            "n_repeats": row["n_repeats"],
            "y": row["y"],
            "sigma": row["sigma"],
            "source": row["source"],
            "units": row["units"],
            "output": row.get("output", "luminescence"),
            "fidelity": row.get("fidelity", 1),
        }
        for row in plate["observations"]
    ]
    result = learn_ssdk(body)
    result["plate_provenance"] = {
        "source": plate["source"],
        "input_sha256": plate["input_sha256"],
        "normalization_method": plate["normalization_method"],
        "n_rows": len(plate["observations"]),
        "outputs": sorted({row["output"] for row in body["observations"]}),
    }
    return result
