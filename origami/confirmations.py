"""Library tables the sandbox can download.

These rows are the structural report, the Phillips thermal gate, and the
physics score the engine already computes. Nothing here is a new model.
``calibrated`` stays false. Team lengths are not written in as optima.
"""

from __future__ import annotations

from typing import Any

from origami.engine import ClaspDesignEngine
from origami.physical.deposited import placed_ca_cloud
from origami.physical.steric import payload_center
from origami.physical.structure import structural_report
from origami.priors import (
    DEFAULT_PAYLOAD_RADIUS_A,
    LINKER_SIGMA_A,
    N_REPEATS_MAX,
    N_REPEATS_MIN,
)
from origami.stability.series import PHILLIPS_2012_CTPRA_DSC, delta_g_at_n

# Coordinates are stored to 0.001 Å, the same rounding as the deposited table.
_COORD_DECIMALS = 3


def confirm_library(
    payload_radii_A: list[float] | None = None,
    *,
    thermal_prior: bool = True,
    t_assay_C: float | None = None,
) -> dict[str, Any]:
    """One row per repeat count from the existing engine.

    Two radii place payloads on the end repeats, matching
    ``ClaspDesignEngine.evaluate_one``. The linker on this library scan is
    ``LINKER_SIGMA_A``. A custom design tether is not substituted here.
    """
    radii = payload_radii_A
    if radii is not None and len(radii) != 2:
        raise ValueError("library confirmation expects two payload radii or none")
    engine = ClaspDesignEngine(payload_radii_A=radii)
    result = engine.run(thermal_prior=thermal_prior, t_assay_C=t_assay_C)
    rows: list[dict[str, Any]] = []
    for n_repeats in result.candidates:
        physics = result.reports[n_repeats]
        structure = structural_report(physics.geometry, [0, n_repeats - 1])
        structure_row = structure.to_dict()
        pair = structure_row["pairs"][0]
        gate = None if result.thermal_by_n is None else result.thermal_by_n[n_repeats]
        dg = None if not thermal_prior else delta_g_at_n(PHILLIPS_2012_CTPRA_DSC, n_repeats)
        end_clash = _end_clash(physics.steric.pairs, n_repeats)
        end_distance = physics.pair_distances_A.get((0, n_repeats - 1))
        end_ceff = physics.ceff.get((0, n_repeats - 1))
        rows.append(
            {
                "n_repeats": int(n_repeats),
                "rise_A": float(structure_row["rise_A"]),
                "twist_rad": float(structure_row["twist_rad"]),
                "docking_radius_A": float(structure_row["docking_radius_A"]),
                "scaffold_radius_A": float(structure_row["scaffold_radius_A"]),
                "pitch_A": float(structure_row["pitch_A"]),
                "repeats_per_turn": float(structure_row["repeats_per_turn"]),
                "axial_span_A": float(structure_row["axial_span_A"]),
                "contour_nm": float(structure_row["contour_nm"]),
                "persistence_length_nm": float(structure_row["persistence_length_nm"]),
                "wlc_end_to_end_rms_nm": float(structure_row["wlc_end_to_end_rms_nm"]),
                "rigid_screw": bool(structure_row["rigid_screw"]),
                "end_pair_chord_A": float(pair["chord_A"]),
                "end_pair_chord_sigma_A": float(pair["chord_sigma_A"]),
                "end_pair_phase_rad": float(pair["phase_rad"]),
                "end_pair_facing_cosine": float(pair["facing_cosine"]),
                "physics_score": float(physics.physics_score),
                "p_instability": float(physics.steric.p_any_instability),
                "p_scaffold_max": float(max(physics.steric.p_scaffold_clash)),
                "end_pair_p_clash": float(end_clash),
                "end_pair_distance_A": None if end_distance is None else float(end_distance),
                "end_pair_c_eff_M": None if end_ceff is None else float(end_ceff.C_eff_M),
                "steric_feasible": bool(physics.feasible),
                "thermal_state": "not_scored" if gate is None else gate.state,
                "tm_C": None if gate is None or gate.tm_C is None else float(gate.tm_C),
                "tm_interval_low": (
                    None if gate is None or gate.interval_low is None else float(gate.interval_low)
                ),
                "tm_interval_high": (
                    None
                    if gate is None or gate.interval_high is None
                    else float(gate.interval_high)
                ),
                "thermal_reason": "" if gate is None else gate.reason,
                "delta_g": None if dg is None else float(dg.value),
                "delta_g_units": None if dg is None else dg.units,
                "delta_g_uncertainty": (
                    None if dg is None or dg.uncertainty is None else float(dg.uncertainty)
                ),
            }
        )
    if [row["n_repeats"] for row in rows] != list(range(N_REPEATS_MIN, N_REPEATS_MAX + 1)):
        raise RuntimeError("confirmation library does not cover n = 3..24")
    return {
        "calibrated": False,
        "thermal_series": PHILLIPS_2012_CTPRA_DSC if thermal_prior else None,
        "linker_sigma_A": float(LINKER_SIGMA_A.value),
        "payload_radii_A": (
            [float(DEFAULT_PAYLOAD_RADIUS_A.value), float(DEFAULT_PAYLOAD_RADIUS_A.value)]
            if radii is None
            else [float(value) for value in radii]
        ),
        "notes": [
            "Each row is structural_report plus the thermal gate plus physics_report.",
            "rigid_screw is true when contour length is at most the 15 nm persistence length.",
            "thermal_state pass requires a matched Phillips 2012 CTPRa DSC Tm above t_assay.",
            "n outside that table is extrapolated. No Tm(n) was fit.",
            "delta_g is the printed unfolding value. It does not set thermal_state.",
            "The library linker is the (GGGGS)3 RMS. A design-specific tether is not used here.",
        ],
        "rows": rows,
    }


def geometry_scene(
    n_repeats: int,
    indices: list[int],
    radii_A: list[float],
    standoff_A: list[float],
) -> dict[str, Any]:
    """Cα cloud and payload centers for one scaffold already scored.

    Coordinates are rounded to 0.001 Å. The cloud is the consensus repeat
    placed on the runtime screw. Side chains are not included.
    """
    if len(indices) != len(radii_A) or len(indices) != len(standoff_A):
        raise ValueError("indices, radii, and standoffs must have the same length")
    from origami.physical.geometry import build_ctpr

    geom = build_ctpr(n_repeats)
    cloud = placed_ca_cloud(n_repeats, geom.rise_A, geom.rotation_rad)
    payloads = []
    for index, radius, standoff in zip(indices, radii_A, standoff_A):
        site = geom.site(index)
        center = payload_center(site, float(standoff) + float(radius))
        payloads.append(
            {
                "repeat_index": int(index),
                "radius_A": float(radius),
                "standoff_A": float(standoff),
                "center_A": _xyz(center),
            }
        )
    return {
        "n_repeats": int(n_repeats),
        "method": "delta_method_ca_envelope",
        "ca_count": int(cloud.shape[0]),
        "residues_per_repeat": 34,
        "ca_A": [_xyz(point) for point in cloud],
        "sites_A": [_xyz(site.xyz_A) for site in geom.sites],
        "payloads": payloads,
        "notes": [
            "C-alpha trace only. Side chains are absent, so excluded volume is understated.",
            "Each payload center is one tether RMS plus one radius out from the junction.",
        ],
    }


def _xyz(point: Any) -> list[float]:
    return [
        round(float(point[0]), _COORD_DECIMALS),
        round(float(point[1]), _COORD_DECIMALS),
        round(float(point[2]), _COORD_DECIMALS),
    ]


def _end_clash(pairs: list[Any], n_repeats: int) -> float:
    for pair in pairs:
        if {int(pair.i), int(pair.j)} == {0, n_repeats - 1}:
            return float(pair.p_clash)
    if len(pairs) == 1:
        return float(pairs[0].p_clash)
    raise RuntimeError(f"no end-pair clash at n={n_repeats}")

