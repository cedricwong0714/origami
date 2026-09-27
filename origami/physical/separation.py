"""Repeat separation on one CTPR screw.

The length scan asks how many repeats the scaffold has. This scan asks
how many repeats sit between two payloads on a scaffold that is already
chosen. ``delta_i`` is the partner index minus the anchor index.

Chord, phase, and facing come from ``structural_report``. Clash,
effective concentration, and the physics score come from
``physics_report``. Both use the canonical screw. No rise, twist, or
radius is introduced here.

Ranking uses the existing residual GP and ``recommend``. The GP is not
fit. Repeat-count observations are a different coordinate and are not
accepted. With no fit, the posterior mean equals the physics score and
the posterior variance is flat, so UCB ranks that score. ``recommend``
still applies its own clash limit, including its fall-through when every
separation exceeds that limit.

If the scaffold thermal state is not ``pass`` and not ``not_scored``,
the candidates are still reported and ``next_delta_i`` stays None. A
separation is not recommended on a scaffold the thermal gate did not pass.
"""

from __future__ import annotations

import math

import numpy as np

from origami.design_engine.active_learning import recommend
from origami.design_engine.gp import ResidualGP
from origami.physical.geometry import build_ctpr
from origami.physical.score import physics_report
from origami.physical.structure import structural_report

_ACTIVE_PROCESS = "unfitted_residual_gp_plus_recommend"
_RANKABLE_THERMAL = frozenset({"pass", "not_scored"})
_THERMAL_STATES = _RANKABLE_THERMAL | frozenset({"fail", "extrapolated", "omitted"})

SEPARATION_KEYS = frozenset(
    {
        "calibrated",
        "gp_fitted",
        "active_process",
        "n_repeats",
        "anchor_index",
        "radius_anchor_A",
        "radius_partner_A",
        "design_delta_i",
        "thermal_state",
        "one_turn_n",
        "acquisition_name",
        "next_delta_i",
        "candidates",
        "notes",
    }
)
SEPARATION_CANDIDATE_KEYS = frozenset(
    {
        "delta_i",
        "partner_index",
        "phase_rad",
        "facing_cosine",
        "chord_A",
        "chord_sigma_A",
        "axial_A",
        "p_clash",
        "p_instability",
        "c_eff_M",
        "physics_score",
        "posterior_mean",
        "posterior_std",
        "on_integer_turn",
    }
)


def separation_library(
    n_repeats: int,
    *,
    anchor_index: int = 0,
    radius_anchor_A: float,
    radius_partner_A: float,
    thermal_state: str,
    design_delta_i: int | None = None,
) -> dict[str, object]:
    """Scan Δi on one scaffold, then rank it with the unfitted GP.

    The structural fields are filled before ``ResidualGP.predict`` and
    ``recommend`` run. ``design_delta_i`` is the separation already
    chosen for this design, recorded beside the scan. It is not a target
    the acquisition is trained to return.
    """
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise TypeError("n_repeats must be an integer")
    if isinstance(anchor_index, bool) or not isinstance(anchor_index, int):
        raise TypeError("anchor_index must be an integer")
    if n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    if anchor_index < 0 or anchor_index >= n_repeats:
        raise ValueError(f"anchor_index {anchor_index} is outside 0..{n_repeats - 1}")
    if thermal_state not in _THERMAL_STATES:
        raise ValueError(f"thermal_state {thermal_state!r} is not a separation state")
    radius_anchor = _positive_radius("radius_anchor_A", radius_anchor_A)
    radius_partner = _positive_radius("radius_partner_A", radius_partner_A)
    recorded_delta = _design_delta(design_delta_i)

    geom = build_ctpr(n_repeats)
    # Empty index list: screw invariants only. None would score every pair.
    screw = structural_report(geom, [])
    one_turn_n = _integer_turn(screw.repeats_per_turn)
    rows = _structural_rows(
        n_repeats=n_repeats,
        anchor_index=anchor_index,
        radius_anchor_A=radius_anchor,
        radius_partner_A=radius_partner,
        one_turn_n=one_turn_n,
    )
    ranked, acquisition_name, next_delta_i = _rank(rows, thermal_state)
    notes = _notes(
        thermal_state=thermal_state,
        one_turn_n=one_turn_n,
        next_delta_i=next_delta_i,
        acquisition_name=acquisition_name,
        n_candidates=len(ranked),
    )
    return {
        "calibrated": False,
        "gp_fitted": False,
        "active_process": _ACTIVE_PROCESS,
        "n_repeats": int(n_repeats),
        "anchor_index": int(anchor_index),
        "radius_anchor_A": radius_anchor,
        "radius_partner_A": radius_partner,
        "design_delta_i": recorded_delta,
        "thermal_state": thermal_state,
        "one_turn_n": one_turn_n,
        "acquisition_name": acquisition_name,
        "next_delta_i": next_delta_i,
        "candidates": ranked,
        "notes": notes,
    }


def _positive_radius(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number of angstroms")
    radius = float(value)
    if not math.isfinite(radius) or radius <= 0.0:
        raise ValueError(f"{name} must be > 0")
    return radius


def _design_delta(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("design_delta_i must be an integer or None")
    if value < 1:
        raise ValueError("design_delta_i must be >= 1 when set")
    return int(value)


def _integer_turn(repeats_per_turn: float) -> int | None:
    nearest = round(repeats_per_turn)
    if nearest < 1 or abs(repeats_per_turn - nearest) > 1e-6:
        return None
    return int(nearest)


def _structural_rows(
    *,
    n_repeats: int,
    anchor_index: int,
    radius_anchor_A: float,
    radius_partner_A: float,
    one_turn_n: int | None,
) -> list[dict[str, object]]:
    """Docking geometry and physics score for each partner. No GP yet."""
    rows: list[dict[str, object]] = []
    for partner in range(anchor_index + 1, n_repeats):
        delta_i = partner - anchor_index
        scored = physics_report(
            n_repeats,
            payload_indices=[anchor_index, partner],
            radii_A=[radius_anchor_A, radius_partner_A],
        )
        pair = structural_report(scored.geometry, [anchor_index, partner]).pairs[0]
        if pair.delta_repeats != delta_i:
            raise RuntimeError("structural Δi does not match the partner index")
        if len(scored.steric.pairs) != 1:
            raise RuntimeError("a two-site separation must have one clash pair")
        ceff = scored.ceff.get((anchor_index, partner))
        if ceff is None:
            raise RuntimeError("effective concentration was not scored for this separation")
        on_turn = one_turn_n is not None and delta_i % one_turn_n == 0
        rows.append(
            {
                "delta_i": int(delta_i),
                "partner_index": int(partner),
                "phase_rad": float(pair.phase_rad),
                "facing_cosine": float(pair.facing_cosine),
                "chord_A": float(pair.chord_A),
                "chord_sigma_A": float(pair.chord_sigma_A),
                "axial_A": float(pair.axial_A),
                "p_clash": float(scored.steric.pairs[0].p_clash),
                "p_instability": float(scored.steric.p_any_instability),
                "c_eff_M": float(ceff.C_eff_M),
                "physics_score": float(scored.physics_score),
                "on_integer_turn": bool(on_turn),
            }
        )
    return rows


def _rank(
    rows: list[dict[str, object]],
    thermal_state: str,
) -> tuple[list[dict[str, object]], str, int | None]:
    """Predict with a new unfitted residual GP, then optionally acquire.

    A new ``ResidualGP`` is constructed here so a fit stored on the
    repeat-count learner cannot leak into Δi.
    """
    if not rows:
        return [], "no partner site on this scaffold", None

    x_values = np.array([[int(row["delta_i"])] for row in rows], dtype=float)
    scores = np.array([float(row["physics_score"]) for row in rows], dtype=float)
    gp = ResidualGP()
    posterior = gp.predict(x_values, scores)
    if gp.fitted or gp.alpha != 1.0 or gp.beta != 0.0:
        raise RuntimeError("separation ranking fitted or shifted the residual GP")

    ranked: list[dict[str, object]] = []
    for row, mean, std in zip(rows, posterior.mean, posterior.std):
        completed = dict(row)
        completed["posterior_mean"] = float(mean)
        completed["posterior_std"] = float(std)
        ranked.append(completed)

    if thermal_state not in _RANKABLE_THERMAL:
        return (
            ranked,
            f"withheld: scaffold thermal state is {thermal_state}",
            None,
        )

    instability = np.array([float(row["p_instability"]) for row in ranked], dtype=float)
    choice = recommend(
        x_values,
        posterior,
        scores,
        instability,
        observed=set(),
        acquisition="ucb",
    )
    return ranked, choice.acquisition_name, int(choice.n_repeats)


def _notes(
    *,
    thermal_state: str,
    one_turn_n: int | None,
    next_delta_i: int | None,
    acquisition_name: str,
    n_candidates: int,
) -> list[str]:
    notes = [
        (
            "delta_i is the repeat separation of two payloads on this scaffold. "
            "It is not the total repeat count n."
        ),
        (
            "The residual GP was not fit. Its posterior mean equals the physics "
            "score and its variance is flat. Repeat-count observations were not used."
        ),
        (
            "next_delta_i is that untrained acquisition. It is not a team length "
            "and it is not trained toward 14."
        ),
        (
            "Effective concentration comes from physics_report. Each payload "
            "stands off by one (GGGGS)3 RMS, and the pair width is the "
            "hypotenuse of two of those widths. A payload linker_sigma_A on "
            "the design is not substituted. "
            "The residual GP stays unfitted: the retrieved literature has "
            "geometry and linker mechanics, not an assay y for this score."
        ),
    ]
    if one_turn_n is not None:
        notes.append(
            f"A separation that is a multiple of {one_turn_n} repeats puts the "
            "docking sites on the same face again. Pair clash can rise there."
        )
    if n_candidates == 0:
        notes.append("The anchor is the last repeat, so there is no partner site.")
    elif thermal_state not in _RANKABLE_THERMAL:
        notes.append(
            f"Scaffold thermal state is {thermal_state}. Candidates are reported "
            "and no separation was recommended."
        )
    elif "exceed steric threshold" in acquisition_name:
        notes.append(
            "Every separation exceeds recommend()'s clash limit. "
            "The acquisition fell through to the least-unstable unused separation."
        )
    if next_delta_i is not None:
        notes.append(
            f"Untrained acquisition selected delta_i={next_delta_i}. "
            "calibrated is false."
        )
    return notes
