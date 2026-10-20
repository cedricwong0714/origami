"""Dry-lab rows and team measurements the learner is allowed to use.

Length table: PCGEM26 wiki, kinetic modelling, stage 2.
AMBER trajectories, MATLAB averages, for CTPR3-NanoLuc, CTPR8-NanoLuc,
and CTPR14-NanoLuc. These are in-silico dry-lab outputs. They are not
wet-lab assays and they do not set calibrated=True.

The length target is end-to-end because that column is reported for every
construct. Rg, RMSD, and relaxation time stay on the same row so the fit
can be traced back to the table. n = 3 and n = 8 are both printed as
48.51 Å. That shared mean is kept as printed. Rg at those two rows is not
the same, so a flat end-to-end is not a claim that the scaffold size is flat.

The locking rate below is the team's wet-lab fit. The 1.4×10³ M⁻¹ s⁻¹
figure is the literature comparison printed on the wiki kinetics page.
The 10 / 30 / 28 nM dissociation constants in wiki section 6 are not
loaded: that section says they come from literature and the team did not
measure them.
"""

from __future__ import annotations

from dataclasses import dataclass

from origami.engine import Observation
from origami.priors import Parameter

DRY_LAB_MD_SOURCE = "dry_lab_md"
DRY_LAB_MD_NOTE = (
    "AMBER MD end-to-end length, MATLAB average, PCGEM26 wiki stage 2. "
    "In silico. Not a wet-lab assay."
)


@dataclass(frozen=True)
class MdLengthRow:
    n_repeats: int
    construct: str
    end_to_end_A: float
    end_to_end_sd_A: float
    rg_A: float
    rg_sd_A: float
    rmsd_A: float
    rmsd_sd_A: float
    tau_frames: float


# Printed means and standard deviations. Tau has no printed SD.
MD_LENGTH_ROWS: tuple[MdLengthRow, ...] = (
    MdLengthRow(3, "CTPR3-NanoLuc", 48.51, 0.73, 13.93, 0.09, 1.17, 0.26, 8.84),
    MdLengthRow(8, "CTPR8-NanoLuc", 48.51, 0.72, 33.46, 0.49, 3.43, 1.11, 10.62),
    MdLengthRow(14, "CTPR14-NanoLuc", 52.04, 0.63, 30.75, 0.12, 1.11, 0.25, 1.99),
)


# Parameter: SpyTag–SpyCatcher locking rate, team fit
# Value: 249.4
# Units: M^-1 s^-1
# Source: PCGEM26 wiki section 7, time-resolved covalent-locking fit
# System: team SpyTag–SpyCatcher wet-lab time course
# Method: second-order fit, R^2 = 0.9798
# Notes: printed uncertainty ±42.57. The wiki notes a local-minimum warning.
#         The wiki states the team measured this value and used it as an ODE input.
TEAM_KLOCK = Parameter(
    name="team_spytag_spycatcher_klock",
    value=249.4,
    units="M^-1 s^-1",
    sigma=42.57,
    source=(
        "PCGEM26 wiki section 7, SpyTag–SpyCatcher time-resolved covalent-locking fit. "
        "Printed value 249.4 M^-1 s^-1 (±42.57), R^2=0.9798."
    ),
    system="Team SpyTag–SpyCatcher wet-lab time course",
    method="Second-order kinetic fit. Source notes a local-minimum warning.",
    notes=(
        "The wiki states this rate was measured by the team. "
        "The ±42.57 is the fit uncertainty printed there, not a re-derived standard error. "
        "This does not replace any constant in priors.py."
    ),
    provenance="wet_lab",
    calibrated=False,
)

# Parameter: SpyTag–SpyCatcher on-rate used only as a literature comparison
# Value: 1.4e3
# Units: M^-1 s^-1
# Source: PCGEM26 wiki kinetics page, quoting the Zakeri et al. 2012 mix
# System: the 10 μM SpyTag–SpyCatcher mix described on that page
# Method: not re-fit here; the page states the on-rate
# Notes: no uncertainty is printed next to this number, so sigma is 0.
#         Do not treat sigma=0 as a measured error of zero.
LITERATURE_SPY_KON = Parameter(
    name="literature_spytag_spycatcher_kon_comparison",
    value=1.4e3,
    units="M^-1 s^-1",
    sigma=0.0,
    source=(
        "PCGEM26 wiki kinetics page: the Spy page uses the 10 μM mix in "
        "Zakeri et al. 2012 and an on-rate of 1.4×10^3 M^-1 s^-1."
    ),
    system="Literature comparison quoted on the team kinetics page, not a team fit",
    method="Point value as printed. Not refit in this repository.",
    notes=(
        "Comparison baseline only. The page does not print an uncertainty, "
        "so sigma is 0 and must not be read as a measured error."
    ),
    provenance="literature_placeholder",
    calibrated=False,
)

EXCLUDED_LITERATURE_KD_NOTE = (
    "Wiki section 6 lists CaM–M13 Kd = 10 nM, LgBiT–SmBiT Kd = 30 nM, "
    "and SpyTag–SpyCatcher Kd = 28 nM, then states that these values come "
    "from literature and the team did not measure them. They are not "
    "training rows and they do not replace CAM_M13_KD_M."
)


@dataclass(frozen=True)
class CalciumHillAssay:
    """One in-vitro dose-response. It is not indexed by repeat count."""

    ec50_uM: float
    ec50_ci95_low_uM: float
    ec50_ci95_high_uM: float
    hill_coefficient: float
    bottom_rlu: float
    top_rlu: float
    r_squared: float
    source: str
    notes: str


# Printed Hill fit, wiki section 9. One construct, so it cannot rank n.
CALCIUM_HILL_ASSAY = CalciumHillAssay(
    ec50_uM=0.47,
    ec50_ci95_low_uM=0.405,
    ec50_ci95_high_uM=0.535,
    hill_coefficient=1.684,
    bottom_rlu=1723.32,
    top_rlu=112869.80,
    r_squared=0.9984,
    source=(
        "PCGEM26 wiki section 9, calcium dose-response luminescence, Hill fit. "
        "EC50 = 0.47 μM, 95% CI [0.405, 0.535] μM, nH = 1.684, R^2 = 0.9984."
    ),
    notes=(
        "In-vitro proof-of-concept for one construct. "
        "Not a function of CTPR repeat count, so the length GP does not train on it."
    ),
)


def md_end_to_end_observations(
    n_min: int | None = None,
    n_max: int | None = None,
) -> list[Observation]:
    """End-to-end lengths the GP treats as y, with the printed SD as sigma."""
    rows: list[Observation] = []
    for row in MD_LENGTH_ROWS:
        if n_min is not None and row.n_repeats < n_min:
            continue
        if n_max is not None and row.n_repeats > n_max:
            continue
        rows.append(
            Observation(
                n_repeats=row.n_repeats,
                y=row.end_to_end_A,
                sigma=row.end_to_end_sd_A,
                source=DRY_LAB_MD_SOURCE,
                units="Å",
                notes=(
                    f"{row.construct}. {DRY_LAB_MD_NOTE} "
                    f"Rg={row.rg_A}±{row.rg_sd_A} Å, "
                    f"RMSD={row.rmsd_A}±{row.rmsd_sd_A} Å, "
                    f"tau={row.tau_frames} frames."
                ),
            )
        )
    return rows
