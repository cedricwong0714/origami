"""Screw fit of deposited CTPR crystal coordinates.

The coordinates are the asymmetric-unit C-alpha atoms of PDB 2AVP, 2HYZ,
and 2FO7, the structures cited by Kajander et al. 2007, DOI
10.1107/S0907444907024353. The article PDF is not open access. This module
does not copy a sentence from that PDF. It refits the deposited atoms.

Each chain is split into consecutive 34-residue blocks, the period at which
the deposited sequence repeats. Block i is rigidly mapped onto block i+1
by Kabsch. That rigid motion is a screw: a rotation about an axis, a
translation along the axis, and the distance of the repeat centroid from
the axis. The outer radius is the farthest C-alpha in the block from the
same axis.

The sample standard deviation uses the unbiased divisor (n - 1). It is the
scatter of these seven steps. It is not a standard error printed in the
paper, and it is not a wet-lab calibration.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "structure" / "ctpr_deposited_ca.json"
)

DEPOSITED_KEYS = frozenset(
    {
        "calibrated",
        "doi",
        "pdb_ids",
        "n_steps",
        "method",
        "rise_mean_A",
        "rise_sample_std_A",
        "rise_min_A",
        "rise_max_A",
        "twist_mean_deg",
        "twist_sample_std_deg",
        "twist_min_deg",
        "twist_max_deg",
        "centroid_radius_mean_A",
        "centroid_radius_sample_std_A",
        "centroid_radius_min_A",
        "centroid_radius_max_A",
        "junction_radius_mean_A",
        "junction_radius_sample_std_A",
        "junction_radius_min_A",
        "junction_radius_max_A",
        "outer_ca_radius_mean_A",
        "outer_ca_radius_min_A",
        "outer_ca_radius_max_A",
        "runtime_rise_A",
        "runtime_twist_deg",
        "runtime_scaffold_radius_A",
        "runtime_docking_radius_A",
        "runtime_rise_inside_deposited_range",
        "runtime_twist_inside_deposited_range",
        "runtime_scaffold_radius_inside_outer_ca_range",
        "runtime_docking_radius_inside_outer_ca_range",
        "persistence_length_retrieved",
        "notes",
    }
)


def load_deposited_coordinates() -> dict[str, object]:
    """Return the committed coordinate table. No network call."""
    payload = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    if payload["citation"]["doi"] != "10.1107/S0907444907024353":
        raise ValueError("deposited CTPR table is not the Kajander 2007 coordinate set")
    return payload


def screw_steps() -> list[dict[str, float | str | int]]:
    """One screw step for every pair of consecutive deposited repeats."""
    table = load_deposited_coordinates()
    steps: list[dict[str, float | str | int]] = []
    for entry in table["entries"]:
        repeats = [np.asarray(block, dtype=float) for block in entry["ca_A"]]
        if any(block.shape != (34, 3) for block in repeats):
            raise ValueError(f"{entry['pdb_id']} repeat block is not 34 C-alpha atoms")
        for index in range(len(repeats) - 1):
            rotation, translation = _kabsch(repeats[index], repeats[index + 1])
            angle_deg, rise_A, axis, origin = _screw(rotation, translation)
            centroid = repeats[index].mean(axis=0)
            centroid_radius = _radial_distance(centroid, origin, axis)
            junction = 0.5 * (repeats[index][33] + repeats[index + 1][0])
            junction_radius = _radial_distance(junction, origin, axis)
            outer = max(
                _radial_distance(point, origin, axis) for point in repeats[index]
            )
            steps.append(
                {
                    "pdb_id": str(entry["pdb_id"]),
                    "step_index": index,
                    "twist_deg": angle_deg,
                    "rise_A": rise_A,
                    "centroid_radius_A": centroid_radius,
                    "junction_radius_A": junction_radius,
                    "outer_ca_radius_A": outer,
                }
            )
    if len(steps) < 2:
        raise RuntimeError("deposited CTPR table has fewer than two screw steps")
    return steps


def deposited_summary(
    *,
    runtime_rise_A: float,
    runtime_twist_deg: float,
    runtime_scaffold_radius_A: float,
    runtime_docking_radius_A: float,
) -> dict[str, object]:
    """Compare one runtime screw with the deposited step range.

    ``calibrated`` is false. A match to the deposited range is not a
    wet-lab validation. Persistence length is not in this coordinate set,
    so ``persistence_length_retrieved`` stays false.
    """
    table = load_deposited_coordinates()
    steps = screw_steps()
    rise = _span([float(step["rise_A"]) for step in steps])
    twist = _span([float(step["twist_deg"]) for step in steps])
    centroid = _span([float(step["centroid_radius_A"]) for step in steps])
    junction = _span([float(step["junction_radius_A"]) for step in steps])
    outer = _span([float(step["outer_ca_radius_A"]) for step in steps])
    rise_inside = rise["min"] <= runtime_rise_A <= rise["max"]
    twist_inside = twist["min"] <= runtime_twist_deg <= twist["max"]
    scaffold_inside = outer["min"] <= runtime_scaffold_radius_A <= outer["max"]
    docking_inside = outer["min"] <= runtime_docking_radius_A <= outer["max"]
    notes = [
        (
            "Rise, twist, and radius are a screw fit to deposited C-alpha "
            "coordinates from PDB 2AVP, 2HYZ, and 2FO7. "
            "DOI 10.1107/S0907444907024353. "
            "The article PDF was not open, so no sentence was copied from it."
        ),
        (
            "The asymmetric unit holds 2 or 4 repeats, not a full eight-repeat "
            "superhelix. The step is the transform between consecutive "
            "34-residue blocks in that chain."
        ),
        (
            "Sample standard deviations divide by n-1. They are the scatter of "
            f"{len(steps)} steps, not a standard error printed in the paper."
        ),
        (
            "No persistence length is in this coordinate table. "
            "The open abstract of Synakewicz et al. 2022, ACS Nano, "
            "DOI 10.1021/acsnano.1c09162, also does not state one. "
            "The 15 nm cutoff stays a project cutoff."
        ),
    ]
    if not rise_inside:
        notes.append(
            "The runtime rise is outside the deposited step range. "
            "Coordinates that still use it are not the crystal screw."
        )
    if abs(runtime_scaffold_radius_A - centroid["mean"]) <= 1e-6:
        notes.append(
            "The runtime scaffold radius is the mean repeat-centroid radius. "
            "Payload clash uses the placed C-alpha trace, not a cylinder of this radius."
        )
    elif not scaffold_inside:
        notes.append(
            "The runtime scaffold radius is outside the deposited outer "
            "C-alpha shell. It is not the repeat-centroid radius."
        )
    if abs(runtime_docking_radius_A - junction["mean"]) <= 1e-6:
        notes.append(
            "The runtime docking radius is the mean radial distance of the "
            "inter-repeat junction: the midpoint of C-alpha 34 and C-alpha 1 "
            "of the next 34-residue block. In these entries that junction "
            "follows DPRS. The previous 0.35 nm loop offset is not used."
        )
    return {
        "calibrated": False,
        "doi": table["citation"]["doi"],
        "pdb_ids": [str(entry["pdb_id"]) for entry in table["entries"]],
        "n_steps": len(steps),
        "method": str(table["method"]),
        "rise_mean_A": rise["mean"],
        "rise_sample_std_A": rise["sample_std"],
        "rise_min_A": rise["min"],
        "rise_max_A": rise["max"],
        "twist_mean_deg": twist["mean"],
        "twist_sample_std_deg": twist["sample_std"],
        "twist_min_deg": twist["min"],
        "twist_max_deg": twist["max"],
        "centroid_radius_mean_A": centroid["mean"],
        "centroid_radius_sample_std_A": centroid["sample_std"],
        "centroid_radius_min_A": centroid["min"],
        "centroid_radius_max_A": centroid["max"],
        "junction_radius_mean_A": junction["mean"],
        "junction_radius_sample_std_A": junction["sample_std"],
        "junction_radius_min_A": junction["min"],
        "junction_radius_max_A": junction["max"],
        "outer_ca_radius_mean_A": outer["mean"],
        "outer_ca_radius_min_A": outer["min"],
        "outer_ca_radius_max_A": outer["max"],
        "runtime_rise_A": float(runtime_rise_A),
        "runtime_twist_deg": float(runtime_twist_deg),
        "runtime_scaffold_radius_A": float(runtime_scaffold_radius_A),
        "runtime_docking_radius_A": float(runtime_docking_radius_A),
        "runtime_rise_inside_deposited_range": rise_inside,
        "runtime_twist_inside_deposited_range": twist_inside,
        "runtime_scaffold_radius_inside_outer_ca_range": scaffold_inside,
        "runtime_docking_radius_inside_outer_ca_range": docking_inside,
        "persistence_length_retrieved": False,
        "notes": notes,
    }


def consensus_repeat_ca() -> np.ndarray:
    """Mean 34-residue Cα cloud, with the screw axis on z and the centroid on x.

    Each source repeat is written in the frame of its own screw step, then
    shifted so the repeat centroid has z = 0. The mean of those seven clouds
    is the envelope used for clash. It is not a molecular surface: side chains
    are not in the coordinate table.
    """
    table = load_deposited_coordinates()
    clouds: list[np.ndarray] = []
    for entry in table["entries"]:
        repeats = [np.asarray(block, dtype=float) for block in entry["ca_A"]]
        for index in range(len(repeats) - 1):
            rotation, translation = _kabsch(repeats[index], repeats[index + 1])
            _angle, _rise, axis, origin = _screw(rotation, translation)
            clouds.append(_axis_frame(repeats[index], origin, axis))
    if len(clouds) < 2:
        raise RuntimeError("deposited CTPR table has fewer than two repeats")
    return np.mean(np.stack(clouds, axis=0), axis=0)


def placed_ca_cloud(
    n_repeats: int,
    rise_A: float,
    rotation_rad: float,
) -> np.ndarray:
    """Place one consensus repeat on every step of the runtime screw.

    Returns an (n_repeats * 34, 3) array in Å. Repeat i is the consensus
    cloud rotated by i * rotation about z and translated by i * rise.
    """
    if n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    cloud = consensus_repeat_ca()
    pieces: list[np.ndarray] = []
    for index in range(n_repeats):
        cosine = float(np.cos(index * rotation_rad))
        sine = float(np.sin(index * rotation_rad))
        x = cloud[:, 0]
        y = cloud[:, 1]
        placed = np.column_stack(
            [
                cosine * x - sine * y,
                sine * x + cosine * y,
                cloud[:, 2] + index * rise_A,
            ]
        )
        pieces.append(placed)
    return np.concatenate(pieces, axis=0)


def _axis_frame(block: np.ndarray, origin: np.ndarray, axis: np.ndarray) -> np.ndarray:
    """Cα coordinates with +x through the repeat centroid and z along the screw."""
    centroid = block.mean(axis=0)
    relative = centroid - origin
    radial = relative - float(np.dot(relative, axis)) * axis
    norm = float(np.linalg.norm(radial))
    if norm < 1e-8:
        raise ValueError("repeat centroid lies on the screw axis")
    radial = radial / norm
    tangential = np.cross(axis, radial)
    tangential = tangential / np.linalg.norm(tangential)
    basis = np.column_stack([radial, tangential, axis])
    local = (block - origin) @ basis
    local = np.array(local, copy=True)
    local[:, 2] -= float(local[:, 2].mean())
    return local


def _span(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(array.mean()),
        "sample_std": float(array.std(ddof=1)),
        "min": float(array.min()),
        "max": float(array.max()),
    }


def _kabsch(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rotation and translation that map ``source`` onto ``target``."""
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    covariance = (source - source_center).T @ (target - target_center)
    left, _, right = np.linalg.svd(covariance)
    sign = np.sign(np.linalg.det(right.T @ left.T))
    rotation = right.T @ np.diag([1.0, 1.0, sign]) @ left.T
    translation = target_center - rotation @ source_center
    return rotation, translation


def _screw(
    rotation: np.ndarray,
    translation: np.ndarray,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """Angle in degrees, rise in Å, unit axis, and a point on the axis."""
    cosine = float(np.clip((np.trace(rotation) - 1.0) / 2.0, -1.0, 1.0))
    angle = float(np.arccos(cosine))
    axis = np.array(
        [
            rotation[2, 1] - rotation[1, 2],
            rotation[0, 2] - rotation[2, 0],
            rotation[1, 0] - rotation[0, 1],
        ],
        dtype=float,
    )
    norm = float(np.linalg.norm(axis))
    if norm < 1e-8:
        axis = np.array([0.0, 0.0, 1.0])
    else:
        axis = axis / norm
    if float(np.dot(axis, translation)) < 0.0:
        axis = -axis
        angle = -angle
    rise = float(np.dot(axis, translation))
    perpendicular = translation - rise * axis
    design = np.vstack([np.eye(3) - rotation, axis])
    target = np.concatenate([perpendicular, [0.0]])
    origin, *_ = np.linalg.lstsq(design, target, rcond=None)
    return float(np.degrees(angle)), rise, axis, origin


def _radial_distance(point: np.ndarray, origin: np.ndarray, axis: np.ndarray) -> float:
    relative = point - origin
    radial = relative - np.dot(relative, axis) * axis
    return float(np.linalg.norm(radial))
