"""Backbone-only CTPR screw measurements. No payload spheres.

These rows are the solenoid: rise, twist, contour, worm-like-chain
comparison, deposited C-alpha envelope, and junction-to-junction
chords. They do not place enzymes and they do not compute C_eff.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from origami.physical.deposited import placed_ca_cloud
from origami.physical.geometry import build_ctpr
from origami.physical.structure import structural_report
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN


def backbone_library(
    n_min: int = N_REPEATS_MIN,
    n_max: int = N_REPEATS_MAX,
) -> dict[str, Any]:
    """One screw row per repeat count. No radii, no clash, no C_eff."""
    if n_min < 1 or n_max < n_min:
        raise ValueError("n range is empty")
    rows: list[dict[str, Any]] = []
    screw = None
    deposited = None
    for n_repeats in range(n_min, n_max + 1):
        geom = build_ctpr(n_repeats)
        report = structural_report(geom, [])
        if screw is None:
            screw = {
                "calibrated": False,
                "rise_A": float(report.rise_A),
                "twist_deg": float(np.degrees(report.twist_rad)),
                "repeats_per_turn": float(report.repeats_per_turn),
                "pitch_A": float(report.pitch_A),
                "scaffold_centroid_radius_A": float(report.scaffold_radius_A),
                "junction_radius_A": float(report.docking_radius_A),
                "persistence_length_nm": float(report.persistence_length_nm),
                "docking_curvature_per_A": float(report.docking_curvature_per_A),
                "docking_torsion_per_A": float(report.docking_torsion_per_A),
                "backbone_curvature_per_A": float(report.backbone_curvature_per_A),
                "backbone_torsion_per_A": float(report.backbone_torsion_per_A),
                "uncertainty_model": report.uncertainty_model,
            }
            deposited = report.deposited
        cloud = placed_ca_cloud(n_repeats, geom.rise_A, geom.rotation_rad)
        radial = np.sqrt(cloud[:, 0] ** 2 + cloud[:, 1] ** 2)
        rows.append(
            {
                "n_repeats": int(n_repeats),
                "axial_span_A": float(report.axial_span_A),
                "contour_A": float(report.contour_A),
                "contour_nm": float(report.contour_nm),
                "wlc_end_to_end_rms_nm": float(report.wlc_end_to_end_rms_nm),
                "rigid_screw": bool(report.rigid_screw),
                "ca_count": int(cloud.shape[0]),
                "ca_radial_mean_A": float(radial.mean()),
                "ca_radial_min_A": float(radial.min()),
                "ca_radial_max_A": float(radial.max()),
            }
        )
    geom_sites = build_ctpr(16)
    junctions = structural_report(geom_sites, list(range(16)))
    site_steps = [
        {
            "delta_i": int(pair.delta_repeats),
            "phase_deg": float(np.degrees(pair.phase_rad)),
            "facing_cosine": float(pair.facing_cosine),
            "chord_A": float(pair.chord_A),
            "chord_95_low_A": float(pair.chord_95_low_A),
            "chord_95_high_A": float(pair.chord_95_high_A),
            "axial_A": float(pair.axial_A),
        }
        for pair in junctions.pairs
        if pair.i == 0
    ]
    return {
        "calibrated": False,
        "payloads": False,
        "notes": [
            "No payload spheres. Junction chords are scaffold docking sites.",
            "rigid_screw is true when contour <= 15 nm persistence cutoff.",
            "The 15 nm cutoff is not a retrieved persistence length.",
        ],
        "screw": screw,
        "deposited": deposited,
        "by_n": rows,
        "junction_from_repeat_0": site_steps,
    }


# Caller architecture, N to C. These names are labels on the drawing.
# They are not sequences, masses, or radii.
CONSTRUCT_N_TO_C = (
    "FL",
    "rigid_spacer",
    "rigid_spacer",
    "FL",
    "SpyCatcher",
    "CTPR",
    "flx",
    "flx",
    "flx",
    "LgBiT",
)
CONSTRUCT_N_VALUES = (3, 8, 14)


def backbone_constructs(
    n_values: tuple[int, ...] = CONSTRUCT_N_VALUES,
) -> dict[str, Any]:
    """Structural report for the CTPR block of one fusion drawing.

    The drawing is FL, two rigid spacers, FL, SpyCatcher, CTPR(n)
    with one m13 loop graft, three flexible linkers, then LgBiT.
    Only the CTPR screw is measured. The graft repeat was not
    supplied, so no repeat is marked as the graft.
    """
    if not n_values:
        raise ValueError("n_values is empty")
    rows: list[dict[str, Any]] = []
    screw = None
    for n_repeats in n_values:
        if n_repeats < 1:
            raise ValueError("n_repeats must be >= 1")
        geom = build_ctpr(int(n_repeats))
        report = structural_report(geom, list(range(n_repeats)))
        if screw is None:
            screw = {
                "calibrated": False,
                "rise_A": float(report.rise_A),
                "twist_deg": float(np.degrees(report.twist_rad)),
                "repeats_per_turn": float(report.repeats_per_turn),
                "pitch_A": float(report.pitch_A),
                "scaffold_centroid_radius_A": float(report.scaffold_radius_A),
                "junction_radius_A": float(report.docking_radius_A),
                "persistence_length_nm": float(report.persistence_length_nm),
                "uncertainty_model": report.uncertainty_model,
            }
        cloud = placed_ca_cloud(n_repeats, geom.rise_A, geom.rotation_rad)
        radial = np.sqrt(cloud[:, 0] ** 2 + cloud[:, 1] ** 2)
        repeats = []
        for site in geom.sites:
            block = geom.coord_covariance[
                3 * site.index : 3 * site.index + 3,
                3 * site.index : 3 * site.index + 3,
            ]
            rms = float(np.sqrt(np.trace(block) / 3.0))
            phase = float(np.degrees(site.index * geom.rotation_rad))
            repeats.append(
                {
                    "repeat_index": int(site.index),
                    "phase_deg": phase,
                    "phase_mod_360_deg": float(phase % 360.0),
                    "facing_cosine_vs_repeat_0": float(np.cos(site.index * geom.rotation_rad)),
                    "x_A": float(site.xyz_A[0]),
                    "y_A": float(site.xyz_A[1]),
                    "z_A": float(site.xyz_A[2]),
                    "position_rms_A": rms,
                    "m13_graft": False,
                }
            )
        pairs = []
        for pair in report.pairs:
            pairs.append(
                {
                    "i": int(pair.i),
                    "j": int(pair.j),
                    "delta_i": int(pair.delta_repeats),
                    "phase_deg": float(np.degrees(pair.phase_rad)),
                    "facing_cosine": float(pair.facing_cosine),
                    "chord_A": float(pair.chord_A),
                    "axial_A": float(pair.axial_A),
                    "chord_sigma_A": float(pair.chord_sigma_A),
                    "chord_95_low_A": float(pair.chord_95_low_A),
                    "chord_95_high_A": float(pair.chord_95_high_A),
                }
            )
        end = next(pair for pair in pairs if pair["i"] == 0 and pair["j"] == n_repeats - 1)
        rows.append(
            {
                "n_repeats": int(n_repeats),
                "axial_span_A": float(report.axial_span_A),
                "contour_nm": float(report.contour_nm),
                "wlc_end_to_end_rms_nm": float(report.wlc_end_to_end_rms_nm),
                "rigid_screw": bool(report.rigid_screw),
                "ca_count": int(cloud.shape[0]),
                "ca_z_min_A": float(cloud[:, 2].min()),
                "ca_z_max_A": float(cloud[:, 2].max()),
                "ca_radial_min_A": float(radial.min()),
                "ca_radial_mean_A": float(radial.mean()),
                "ca_radial_max_A": float(radial.max()),
                "end_junction": end,
                "repeats": repeats,
                "pairs": pairs,
            }
        )
    return {
        "calibrated": False,
        "payloads": False,
        "m13_graft_repeat_index": None,
        "n_to_c": list(CONSTRUCT_N_TO_C),
        "measured_block": "CTPR",
        "notes": [
            "Measured block is the CTPR screw only.",
            "FL, rigid spacers, SpyCatcher, flx, and LgBiT have no lengths in this run.",
            "One m13 graft was requested. The repeat index was not supplied, so every m13_graft flag is false.",
            "End-junction chord is repeat 0 to repeat n-1. It is not a SpyCatcher-to-LgBiT distance.",
        ],
        "screw": screw,
        "constructs": rows,
    }
