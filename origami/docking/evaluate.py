"""Docking chassis: screw chord, clash, and effective concentration.

The chord between two repeat indices comes from the deposited screw.
Clash and effective concentration are computed only when the caller
supplies both payload radii. A missing radius is not replaced with the
25 Å placeholder.

Linker width defaults to the sourced (GGGGS)3 RMS. A caller may override
it. The C_eff interval propagates the junction-chord sigma through
dC/dr. Linker-length uncertainty is omitted, because that paper did not
print a standard error.

``calibrated`` stays false.
"""

from __future__ import annotations

import math
from typing import Any

from origami.docking.local_kinetics import local_kinetics
from origami.physical.backbone import m13_graft_index
from origami.physical.geometry import build_ctpr
from origami.physical.linkers import gaussian_chain_ceff
from origami.physical.steric import steric_report
from origami.physical.structure import structural_report
from origami.priors import LINKER_SIGMA_A, N_REPEATS_MAX, N_REPEATS_MIN

_Z95 = 1.96


class DockingError(ValueError):
    """The docking request is not usable."""


def evaluate_docking(
    n_repeats: int,
    *,
    indices: list[int] | None = None,
    radii_A: list[float] | None = None,
    linker_sigma_A: float | None = None,
    spy_k_on_per_M_s: float | None = None,
    spy_k_on_sigma: float | None = None,
) -> dict[str, Any]:
    """Return screw geometry, and clash plus C_eff when radii exist."""
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise DockingError("n_repeats must be an integer")
    if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
        raise DockingError(f"n_repeats must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]")
    sites = _indices(n_repeats, indices)
    linker = LINKER_SIGMA_A.value if linker_sigma_A is None else float(linker_sigma_A)
    if not math.isfinite(linker) or linker <= 0:
        raise DockingError("linker_sigma_A must be finite and > 0")

    geometry = build_ctpr(n_repeats)
    structure = structural_report(geometry, sites)
    pair = next(item for item in structure.pairs if {item.i, item.j} == set(sites))
    chord = pair.to_dict()
    base: dict[str, Any] = {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "n_repeats": n_repeats,
        "indices": sites,
        "indices_source": "caller"
        if indices is not None
        else "n_terminus_and_named_graft_or_c_terminus",
        "chord_A": chord["chord_A"],
        "chord_sigma_A": chord["chord_sigma_A"],
        "chord_95_low_A": chord["chord_95_low_A"],
        "chord_95_high_A": chord["chord_95_high_A"],
        "facing_cosine": chord["facing_cosine"],
        "axial_A": chord["axial_A"],
        "linker_sigma_A": linker,
        "linker_origin": "caller" if linker_sigma_A is not None else "literature_prior",
        "linker_source": LINKER_SIGMA_A.source,
    }
    if radii_A is None:
        return {
            **base,
            "clash_computable": False,
            "missing": ["both payload radii in angstroms"],
            "note": "The chord does not need a radius. Clash and C_eff do.",
            "local_kinetics": local_kinetics(None, None),
        }
    if len(radii_A) != 2:
        raise DockingError("radii_A must contain two angstrom values")
    radii = [float(radii_A[0]), float(radii_A[1])]
    if any((not math.isfinite(radius)) or radius <= 0 for radius in radii):
        raise DockingError("each payload radius must be finite and > 0")

    steric = steric_report(geometry, sites, radii, standoff_A=[linker, linker])
    clash = steric.pairs[0]
    ceff = gaussian_chain_ceff(clash.distance_A, sigma_A=math.hypot(linker, linker))
    ceff_sigma = _ceff_sigma(
        ceff.C_eff_M, clash.distance_A, pair.chord_sigma_A, ceff.sigma_A
    )
    low = None if ceff_sigma is None else ceff.C_eff_M - _Z95 * ceff_sigma
    high = None if ceff_sigma is None else ceff.C_eff_M + _Z95 * ceff_sigma
    return {
        **base,
        "clash_computable": True,
        "missing": [],
        "radii_A": radii,
        "radius_origin": "caller",
        "center_distance_A": clash.distance_A,
        "contact_A": clash.contact_A,
        "p_clash": clash.p_clash,
        "p_scaffold_clash": steric.p_scaffold_clash,
        "p_any_instability": steric.p_any_instability,
        "c_eff_M": ceff.C_eff_M,
        "c_eff_sigma_M": ceff_sigma,
        "c_eff_95_lower_M": low,
        "c_eff_95_upper_M": high,
        "note": (
            "The C_eff band propagates the junction-chord sigma through dC/dr. "
            "Linker-length uncertainty is omitted because the source printed none."
        ),
        "local_kinetics": local_kinetics(
            ceff.C_eff_M,
            ceff_sigma,
            spy_k_on_per_M_s=spy_k_on_per_M_s,
            spy_k_on_sigma=spy_k_on_sigma,
        ),
    }


def _indices(n_repeats: int, indices: list[int] | None) -> list[int]:
    if indices is None:
        graft = m13_graft_index(n_repeats)
        second = graft if graft not in (None, 0) else n_repeats - 1
        return [0, int(second)]
    if len(indices) != 2:
        raise DockingError("indices must be two repeat indexes")
    parsed: list[int] = []
    for index in indices:
        if isinstance(index, bool) or not isinstance(index, int):
            raise DockingError("each index must be an integer")
        if index < 0 or index >= n_repeats:
            raise DockingError(f"index {index} is outside n={n_repeats}")
        parsed.append(index)
    if parsed[0] == parsed[1]:
        raise DockingError("the two docking indexes must differ")
    return parsed


def _ceff_sigma(
    c_eff_M: float,
    distance_A: float,
    chord_sigma_A: float,
    linker_sigma_A: float,
) -> float | None:
    if not math.isfinite(chord_sigma_A) or chord_sigma_A < 0:
        return None
    if chord_sigma_A == 0:
        return 0.0
    derivative = abs(c_eff_M * 3.0 * distance_A / (linker_sigma_A**2))
    return derivative * chord_sigma_A
