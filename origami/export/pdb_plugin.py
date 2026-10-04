"""Read C-alpha coordinates from a local PDB. Does not replace the CTPR screw."""

from __future__ import annotations

import math
from typing import Any


class PdbPluginError(ValueError):
    """The PDB text cannot be scored."""


def ca_xyz(text: str, chain: str | None = None) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for line in text.splitlines():
        if not line.startswith("ATOM"):
            continue
        if line[12:16].strip() != "CA":
            continue
        if line[16] not in (" ", "A"):
            continue
        if chain is not None and line[21] != chain:
            continue
        points.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
    if not points:
        raise PdbPluginError("no C-alpha atoms in this PDB text")
    return points


def ca_size_scales(points: list[tuple[float, float, float]]) -> dict[str, Any]:
    n = len(points)
    cx = sum(p[0] for p in points) / n
    cy = sum(p[1] for p in points) / n
    cz = sum(p[2] for p in points) / n
    rg2 = sum((p[0] - cx) ** 2 + (p[1] - cy) ** 2 + (p[2] - cz) ** 2 for p in points) / n
    rg = math.sqrt(rg2)
    r_sphere = math.sqrt(5.0 / 3.0) * rg
    r_max = max(math.sqrt((p[0] - cx) ** 2 + (p[1] - cy) ** 2 + (p[2] - cz) ** 2) for p in points)
    return {
        "n_ca": n,
        "rg_A": rg,
        "r_sphere_A": r_sphere,
        "r_max_A": r_max,
        "method": "sqrt(5/3) * C-alpha Rg; side chains ignored",
        "replaces_ctpr_screw": False,
        "usable_as_clash_radius": False,
        "calibrated": False,
        "note": (
            "These numbers describe the uploaded coordinate set. "
            "They do not edit deposited CTPR rise or twist. "
            "Set usable_as_clash_radius only after a human names the sphere convention."
        ),
    }


def describe_pdb(text: str, chain: str | None = None) -> dict[str, Any]:
    return ca_size_scales(ca_xyz(text, chain))
