"""
CTPR scaffold spacing optimizer.

Ranks docking-repeat spacings (Δi) with cylindrical-screw distances from
``src.core.ctpr_geometry`` (rise 1.1 nm, twist 45°, docking on helix radius).
Scoring heuristics are **Tier-3 computational rankings** for design triage —
not wet-lab validated Φ scores.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field

from src.core.ctpr_geometry import (
    CTPR_RADIUS_NM,
    CTPR_RISE_NM,
    CTPR_TWIST_DEG,
    DOCKING_LOOP_OFFSET_NM,
    generate_scaffold_geometry,
    helical_chord_distance_nm,
)
from src.core.schema import ScaffoldSpec

NM_TO_A = 10.0
A_TO_NM = 0.1


class InteractionClass(str, Enum):
    METABOLIC = "Metabolic"
    BINDING = "Binding"
    KINASE = "Kinase"
    ELECTRON = "Electron"


class SpacingCandidate(BaseModel):
    delta_i: int = Field(..., ge=1)
    docking_pair: tuple[int, int]
    d_center_A: float
    d_active_A: float
    p_steric: float = Field(..., ge=0.0, le=1.0)
    c_local_M: Optional[float] = None
    score: float = Field(..., ge=0.0)
    state: str


class OptimizationResult(BaseModel):
    interaction_class: InteractionClass
    anchor_repeat: int
    optimal_delta_i: int
    recommended_scaffold_repeats: int
    best_score: float
    candidates: list[SpacingCandidate]
    geometry_constants: dict[str, Any]
    ascii_map: str
    honesty_note: str


def _steric_probability(d_center_A: float, r_clash_A: float, w_clash_A: float = 5.0) -> float:
    lo = r_clash_A - w_clash_A
    hi = r_clash_A + w_clash_A
    if d_center_A <= lo:
        return 1.0
    if d_center_A >= hi:
        return 0.0
    return float(0.5 * (1.0 + np.cos(np.pi * (d_center_A - lo) / (2.0 * w_clash_A))))


def _score_candidate(
    *,
    interaction: InteractionClass,
    d_center_A: float,
    d_active_A: float,
    p_steric: float,
    r_clash_A: float,
    km_M: float,
    linker_len_A: float = 28.5,
    r_pocket_A: float = 8.0,
) -> tuple[float, Optional[float]]:
    if interaction == InteractionClass.METABOLIC:
        d_m = max(d_active_A, 1e-6) * 1e-10
        v_sphere = (4.0 / 3.0) * np.pi * d_m**3
        c_local = 1.0 / (6.02214076e23 * v_sphere * 1000.0)
        p_capture = (c_local / (km_M + c_local)) * (1.0 - (r_pocket_A / (2.0 * max(d_active_A, 1e-6))))
        return float(max(0.0, p_capture * (1.0 - p_steric))), float(c_local)

    if interaction == InteractionClass.BINDING:
        if d_center_A <= (r_clash_A + linker_len_A):
            dist_diff = abs(d_center_A - r_clash_A)
            score = np.exp(-(dist_diff**2) / (2.0 * (linker_len_A / 2.0) ** 2)) * (1.0 - p_steric)
            return float(max(0.0, score)), None
        return 0.0, None

    if interaction == InteractionClass.KINASE:
        excess = max(0.0, d_active_A - linker_len_A)
        sigma = 15.0
        score = np.exp(-(excess**2) / (2.0 * sigma**2)) * (1.0 - p_steric)
        return float(max(0.0, score)), None

    # Electron transfer ranking (distance-decay heuristic)
    beta = 1.4
    gap = max(0.0, d_center_A - r_clash_A)
    score = np.exp(-beta * gap) * (1.0 - p_steric)
    return float(max(0.0, score)), None


def _ascii_map(
    *,
    i_a: int,
    i_b: int,
    n_recommended: int,
    d_active_A: float,
    delta_i: int,
    p_steric: float,
) -> str:
    parts = ["[N-CAP]"]
    for r in range(1, n_recommended + 1):
        if r == i_a:
            parts.append(f"[R{r}: PAYLOAD_A]")
        elif r == i_b:
            parts.append(f"[R{r}: PAYLOAD_B]")
        elif r == n_recommended:
            parts.append(f"[R{r}: C-CAP]")
        else:
            parts.append(f"[R{r}]")
    chain = " = ".join(parts) + " -> [LgBiT]"
    twist = delta_i * CTPR_TWIST_DEG
    return (
        "CTPR SCAFFOLD SUPERHELIX CONFIGURATION:\n"
        "--------------------------------------------------------\n"
        f"{chain}\n"
        "--------------------------------------------------------\n"
        f"Active-site estimate (d_active) : {d_active_A:.2f} Å\n"
        f"Superhelical rotation           : {twist:.1f}° "
        f"({twist % 360:.1f}° offset)\n"
        f"Steric clearance estimate       : {(100.0 - p_steric * 100.0):.1f}%\n"
        f"Geometry priors                 : rise={CTPR_RISE_NM} nm/repeat, "
        f"twist={CTPR_TWIST_DEG}°/repeat (ORIGAMI invariants)"
    )


def optimize_ctpr_spacing(
    radius_a_A: float,
    radius_b_A: float,
    interaction_class: InteractionClass | str = InteractionClass.METABOLIC,
    km_M: float = 1e-4,
    *,
    anchor_repeat: int = 2,
    delta_i_min: int = 1,
    delta_i_max: int = 6,
    com_radial_extra_nm: float = 0.0,
) -> OptimizationResult:
    """
    Rank Δi spacings for two payloads on a CTPR scaffold.

    Payload radii are in Ångströms (UI convention). Geometry uses cylindrical
    screw distances from ``generate_scaffold_geometry`` (rise 1.1 nm, twist 45°).

    ``com_radial_extra_nm`` optionally extends docking COM beyond scaffold+loop
    (e.g. sensor domain). Default 0.
    """
    if radius_a_A <= 0 or radius_b_A <= 0:
        raise ValueError("Payload radii must be positive")
    if km_M <= 0:
        raise ValueError("K_m must be positive")
    if anchor_repeat < 1:
        raise ValueError("anchor_repeat must be ≥ 1")
    if com_radial_extra_nm < 0:
        raise ValueError("com_radial_extra_nm must be ≥ 0")

    interaction = InteractionClass(interaction_class)
    r_a_nm = radius_a_A * A_TO_NM
    r_b_nm = radius_b_A * A_TO_NM
    r_clash_A = radius_a_A + radius_b_A
    docking_radius_nm = CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM + com_radial_extra_nm

    candidates: list[SpacingCandidate] = []
    best_delta = delta_i_min
    best_score = -1.0

    for delta_i in range(delta_i_min, delta_i_max + 1):
        i_b = anchor_repeat + delta_i
        n_repeats = i_b + 1  # C-terminal cap slot
        geo = generate_scaffold_geometry(
            ScaffoldSpec(
                scaffold_id=f"CTPR{n_repeats}_opt",
                repeat_count=n_repeats,
                docking_positions=[anchor_repeat, i_b],
            ),
            com_radial_extra_nm=com_radial_extra_nm,
        )
        site_a = next(s for s in geo.docking_sites if s.repeat_index == anchor_repeat)
        site_b = next(s for s in geo.docking_sites if s.repeat_index == i_b)
        d_center_nm = float(
            np.linalg.norm(np.array(site_a.position_nm) - np.array(site_b.position_nm))
        )
        # Cross-check against closed-form cylindrical screw chord
        d_formula = helical_chord_distance_nm(delta_i, docking_radius_nm)
        if abs(d_center_nm - d_formula) > 1e-9:
            raise RuntimeError(
                f"Screw distance mismatch at Δi={delta_i}: "
                f"geometry={d_center_nm:.6f} nm vs formula={d_formula:.6f} nm"
            )

        d_active_nm = geo.get_active_site_estimate_nm(0, 1, r_a_nm, r_b_nm)
        d_center_A = d_center_nm * NM_TO_A
        d_active_A = d_active_nm * NM_TO_A
        p_steric = _steric_probability(d_center_A, r_clash_A)
        score, c_local = _score_candidate(
            interaction=interaction,
            d_center_A=d_center_A,
            d_active_A=d_active_A,
            p_steric=p_steric,
            r_clash_A=r_clash_A,
            km_M=km_M,
        )

        if p_steric > 0.5:
            state = "Clash Risk"
        elif score >= best_score:
            state = "Optimal"
        else:
            state = "Sub-optimal"

        candidates.append(
            SpacingCandidate(
                delta_i=delta_i,
                docking_pair=(anchor_repeat, i_b),
                d_center_A=d_center_A,
                d_active_A=d_active_A,
                p_steric=p_steric,
                c_local_M=c_local,
                score=score,
                state=state,
            )
        )
        if score > best_score:
            best_score = score
            best_delta = delta_i

    # Relabel states against final optimum
    for c in candidates:
        if c.p_steric > 0.5:
            c.state = "Clash Risk"
        elif c.delta_i == best_delta:
            c.state = "Optimal"
        else:
            c.state = "Sub-optimal"

    i_b_opt = anchor_repeat + best_delta
    n_recommended = i_b_opt + 1
    best = next(c for c in candidates if c.delta_i == best_delta)

    return OptimizationResult(
        interaction_class=interaction,
        anchor_repeat=anchor_repeat,
        optimal_delta_i=best_delta,
        recommended_scaffold_repeats=n_recommended,
        best_score=float(best_score),
        candidates=candidates,
        geometry_constants={
            "CTPR_RISE_NM": CTPR_RISE_NM,
            "CTPR_TWIST_DEG": CTPR_TWIST_DEG,
            "CTPR_RADIUS_NM": CTPR_RADIUS_NM,
            "DOCKING_LOOP_OFFSET_NM": DOCKING_LOOP_OFFSET_NM,
            "docking_radius_nm": docking_radius_nm,
            "com_radial_extra_nm": com_radial_extra_nm,
            "kinematics": "cylindrical_screw",
            "rise_A_per_repeat": CTPR_RISE_NM * NM_TO_A,
            "source": "src.core.ctpr_geometry (ORIGAMI invariants)",
        },
        ascii_map=_ascii_map(
            i_a=anchor_repeat,
            i_b=i_b_opt,
            n_recommended=n_recommended,
            d_active_A=best.d_active_A,
            delta_i=best_delta,
            p_steric=best.p_steric,
        ),
        honesty_note=(
            "Φ scores are computational ranking heuristics (Tier 3), not experimentally "
            "calibrated fitness. Distances use cylindrical-screw CTPR priors "
            f"(rise {CTPR_RISE_NM} nm, twist {CTPR_TWIST_DEG}°, "
            f"docking radius {docking_radius_nm:.3f} nm). "
            "d_active is a payload-surface estimate, not a crystallographic active-site vector."
        ),
    )
