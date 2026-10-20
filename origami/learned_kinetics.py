"""Local concentration and locking time after the dry-lab length update.

The crystal screw in ``priors.py`` is the literature distance. It grows
with repeat count. The residual GP is trained on the AMBER end-to-end
column, which does not follow that screw. This module recomputes the
Gaussian-chain local concentration at both distances and turns those
concentrations into a locking half-life.

Gaussian chain (σ² = <R²>, the linker prior, not a measured persistence
length):

    C_eff(r) = (3 / (2 π σ²))^(3/2) exp(-3 r² / (2 σ²))

Irreversible second-order lock with the partner held at C_eff:

    t_1/2 = ln(2) / (k C_eff)

Two rates are kept apart. ``TEAM_KLOCK`` is the wet-lab fit. 
``LITERATURE_SPY_KON`` is the 1.4×10³ M⁻¹ s⁻¹ comparison from the wiki
kinetics page. The rate is the same at every n, so it changes the clock
and does not by itself choose a length. The length choice moves because
the distance moved.

Absolute C_eff depends on the linker width, which this project has not
measured. The comparison (screw distance versus MD posterior) is the
result. Rg is stored on the measured rows and is not substituted for
end-to-end: at n = 3 and n = 8 the end-to-end values match and the Rg
values do not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from origami.dry_lab_md import (
    CALCIUM_HILL_ASSAY,
    EXCLUDED_LITERATURE_KD_NOTE,
    LITERATURE_SPY_KON,
    MD_LENGTH_ROWS,
    TEAM_KLOCK,
)
from origami.engine import EngineResult
from origami.physical.geometry import build_ctpr
from origami.physical.linkers import gaussian_chain_ceff_M
from origami.priors import LINKER_SIGMA_A

_CLASH_LIMIT = 0.85
_LN2 = math.log(2.0)


@dataclass(frozen=True)
class ConditionedLength:
    n_repeats: int
    literature_chord_A: float
    posterior_mean_A: float
    posterior_std_A: float
    observed: bool
    rg_A: float | None
    ceff_literature_M: float
    ceff_posterior_M: float
    half_life_literature_s: float | None
    half_life_distance_only_s: float | None
    half_life_team_s: float | None
    half_life_corner_bounds_s: tuple[float, float] | None
    p_instability: float


@dataclass(frozen=True)
class ConditionedLibrary:
    rows: list[ConditionedLength]
    literature_best_n: int
    assumptions: tuple[str, ...]


def literature_chord_A(n_repeats: int) -> float:
    """Docking-site end-to-end from the literature screw, in Å."""
    geometry = build_ctpr(n_repeats)
    return geometry.end_to_end_A(0, n_repeats - 1)


def _half_life_s(rate_per_M_s: float, ceff_M: float) -> float | None:
    if rate_per_M_s <= 0 or ceff_M <= 0:
        return None
    seconds = _LN2 / (rate_per_M_s * ceff_M)
    if not math.isfinite(seconds):
        return None
    return float(seconds)


def _corner_bounds_s(mean_A: float, std_A: float) -> tuple[float, float] | None:
    """Half-life at the corners of the length interval and the klock fit error.

    The length interval is the GP 95% band. The rate interval is
    klock ± 1.96 times the printed fit uncertainty. C_eff falls as r
    grows, so the fast corner is the short distance with the fast rate
    and the slow corner is the long distance with the slow rate.
    This is not a joint posterior.
    """
    rate = TEAM_KLOCK.value
    rate_pad = 1.96 * TEAM_KLOCK.sigma
    rate_lo = rate - rate_pad
    rate_hi = rate + rate_pad
    if rate_lo <= 0:
        return None
    distance_lo = max(mean_A - 1.96 * std_A, 1e-3)
    distance_hi = max(mean_A + 1.96 * std_A, distance_lo)
    fast = _half_life_s(rate_hi, gaussian_chain_ceff_M(distance_lo))
    slow = _half_life_s(rate_lo, gaussian_chain_ceff_M(distance_hi))
    if fast is None or slow is None:
        return None
    return (min(fast, slow), max(fast, slow))


def condition_on_length_posterior(
    result: EngineResult,
    clash_limit: float = _CLASH_LIMIT,
) -> ConditionedLibrary | None:
    """Build the screw-versus-MD table when every observation is a length in Å.

    Returns None when the posterior is not a length (no rows, or a row in
    other units). A relative-output point must not be read as angstroms.
    """
    if not result.observations:
        return None
    if any(obs.units != "Å" for obs in result.observations):
        return None
    observed = {obs.n_repeats for obs in result.observations}
    rg_by_n = {row.n_repeats: row.rg_A for row in MD_LENGTH_ROWS}
    rows: list[ConditionedLength] = []
    for i, n_repeats in enumerate(result.candidates):
        chord = literature_chord_A(int(n_repeats))
        mean_A = float(result.posterior.mean[i])
        std_A = float(result.posterior.std[i])
        ceff_literature = float(gaussian_chain_ceff_M(chord))
        ceff_posterior = float(gaussian_chain_ceff_M(mean_A))
        rows.append(
            ConditionedLength(
                n_repeats=int(n_repeats),
                literature_chord_A=chord,
                posterior_mean_A=mean_A,
                posterior_std_A=std_A,
                observed=int(n_repeats) in observed,
                rg_A=rg_by_n.get(int(n_repeats)),
                ceff_literature_M=ceff_literature,
                ceff_posterior_M=ceff_posterior,
                half_life_literature_s=_half_life_s(LITERATURE_SPY_KON.value, ceff_literature),
                half_life_distance_only_s=_half_life_s(LITERATURE_SPY_KON.value, ceff_posterior),
                half_life_team_s=_half_life_s(TEAM_KLOCK.value, ceff_posterior),
                half_life_corner_bounds_s=_corner_bounds_s(mean_A, std_A),
                p_instability=float(result.p_instability[i]),
            )
        )
    legal = [row for row in rows if row.p_instability < clash_limit]
    pool = legal or rows
    literature_best = max(pool, key=lambda row: (row.ceff_literature_M, -row.n_repeats))
    return ConditionedLibrary(
        rows=rows,
        literature_best_n=literature_best.n_repeats,
        assumptions=_assumptions(),
    )


def _assumptions() -> tuple[str, ...]:
    return (
        "Literature distance is the docking-site end-to-end of the CTPR screw in priors.py.",
        "Conditioned distance is the GP posterior of the AMBER end-to-end column.",
        (
            f"Linker width is {LINKER_SIGMA_A.value:g} Å ({LINKER_SIGMA_A.name}), "
            "an engineering prior, not a measured persistence length."
        ),
        "Half-life treats the lock as irreversible and second order, with the partner held at C_eff.",
        (
            f"Team rate is {TEAM_KLOCK.value:g} {TEAM_KLOCK.units} "
            f"(printed fit uncertainty ±{TEAM_KLOCK.sigma:g}). "
            f"Literature comparison rate is {LITERATURE_SPY_KON.value:g} {LITERATURE_SPY_KON.units}."
        ),
        (
            "Corner bounds use the length 95% interval and the printed klock fit error. "
            "They are not a joint posterior."
        ),
        EXCLUDED_LITERATURE_KD_NOTE,
        CALCIUM_HILL_ASSAY.notes,
        (
            "Rg is reported on the measured rows and is not used as r. "
            "n = 3 and n = 8 share an end-to-end mean and do not share an Rg."
        ),
    )


def format_time(seconds: float | None) -> str:
    """Short label for a half-life. Very large values are outside this linker model."""
    if seconds is None or not math.isfinite(seconds):
        return "not defined"
    if seconds > 1e12:
        return "outside linker reach"
    if seconds < 1.0:
        return f"{seconds:.2f} s"
    if seconds < 60.0:
        return f"{seconds:.1f} s"
    if seconds < 3600.0:
        return f"{seconds / 60.0:.1f} min"
    if seconds < 86400.0:
        return f"{seconds / 3600.0:.1f} h"
    return f"{seconds / 86400.0:.1f} d"


def explain_shift(library: ConditionedLibrary, next_n: int) -> str:
    """What the screw would build, and what the MD posterior says instead."""
    by_n = {row.n_repeats: row for row in library.rows}
    literature = by_n[library.literature_best_n]
    nxt = by_n[next_n]
    measured = [row for row in library.rows if row.observed]
    printed = [row.end_to_end_A for row in MD_LENGTH_ROWS if any(item.n_repeats == row.n_repeats for item in measured)]
    printed_text = ", ".join(f"{value:.2f}" for value in printed)
    rg_text = ", ".join(f"{row.rg_A:g}" for row in measured if row.rg_A is not None)
    team_on_screw = None
    if literature.half_life_literature_s is not None and LITERATURE_SPY_KON.value > 0:
        team_on_screw = literature.half_life_literature_s * (LITERATURE_SPY_KON.value / TEAM_KLOCK.value)
    bounds = nxt.half_life_corner_bounds_s
    bound_text = (
        f" Corner bounds from the length band and the fit error are "
        f"{format_time(bounds[0])} to {format_time(bounds[1])}."
        if bounds is not None
        else ""
    )
    clash_note = ""
    if literature.p_instability >= 0.5:
        clash_note = (
            f" The sphere model still puts the clash probability of that length at "
            f"{literature.p_instability:.2f}."
        )
    return (
        f"The crystal screw ranks n={literature.n_repeats} first.{clash_note} "
        f"Its docking-site end-to-end is {literature.literature_chord_A:.0f} Å, "
        f"and the linker model gives a locking half-life of "
        f"{format_time(literature.half_life_literature_s)} at the literature rate "
        f"1.4×10³ M⁻¹ s⁻¹. "
        f"Pairing that same screw distance with our fit, {TEAM_KLOCK.value:g} M⁻¹ s⁻¹, "
        f"gives {format_time(team_on_screw)}. "
        f"The AMBER end-to-end means are {printed_text} Å. "
        f"The posterior follows those means. At n={literature.n_repeats} it is "
        f"{literature.posterior_mean_A:.1f} Å, and the half-life at our rate is "
        f"{format_time(literature.half_life_team_s)}. "
        f"The next unmeasured length is n={nxt.n_repeats}, "
        f"with posterior length {nxt.posterior_mean_A:.1f} Å and half-life "
        f"{format_time(nxt.half_life_team_s)}.{bound_text} "
        f"Rg on the same rows is {rg_text} Å. "
        f"The GP learns the end-to-end column. Scaffold size sits in the Rg column. "
        f"The 10 nM, 30 nM, and 28 nM dissociation constants are literature "
        f"and are not in the fit."
    )
