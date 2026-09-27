"""Literature engineering priors.

Every numeric biological/structural constant used by the engine lives here.
None of these values are wet-lab measurements from this project. They are
explicit placeholders with uncertainty, to be replaced when assays exist.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from src.core.ctpr_geometry import (
    CTPR_RADIUS_NM,
    CTPR_RISE_NM,
    CTPR_TWIST_DEG,
    DOCKING_LOOP_OFFSET_NM,
)

# 1 nm = 10 Å. src.core.ctpr_geometry is in nanometres; values below are ångströms.
_NM_TO_A = 10.0

Provenance = Literal["literature_placeholder", "wet_lab", "user_entered"]


@dataclass(frozen=True)
class Parameter:
    name: str
    value: float
    units: str
    sigma: float
    source: str
    system: str
    method: str
    notes: str
    provenance: Provenance = "literature_placeholder"
    calibrated: bool = False

    def interval_95(self) -> tuple[float, float]:
        return (self.value - 1.96 * self.sigma, self.value + 1.96 * self.sigma)


# Canonical screw geometry from src.core.ctpr_geometry, stored in Å and radians.
# 1 nm = 10 Å. Twist is converted from degrees to radians (45° = π/4).
# calibrated stays False. Rise and its sigma are the mean and sample
# standard deviation of the deposited screw fit, not a wet-lab fit and not
# a number printed in the Kajander PDF.
CTPR_RISE_A = Parameter(
    name="ctpr_rise_per_repeat",
    value=CTPR_RISE_NM * _NM_TO_A,
    units="Å",
    sigma=0.4760507886412968,
    source=(
        "Screw fit to PDB 2AVP, 2HYZ, and 2FO7. "
        "Kajander et al. (2007) Acta Crystallogr D Biol Crystallogr 63:800-811, "
        "DOI: 10.1107/S0907444907024353. "
        "Coordinates from RCSB mmCIF; the article PDF was not open."
    ),
    system="Consensus TPR asymmetric-unit chains, 34-residue repeats",
    method="Kabsch fit of successive repeats, screw decomposition, mean of 7 steps",
    notes=(
        "Stored in Å: CTPR_RISE_NM × 10. "
        "The previous CLASP prior was 1.1 nm (11.0 Å). "
        "sigma is the sample standard deviation of the 7 deposited steps "
        "(divisor n-1), not a standard error printed in the paper. "
        "1 nm = 10 Å."
    ),
    provenance="literature_placeholder",
    calibrated=False,
)

CTPR_ROTATION_RAD = Parameter(
    name="ctpr_rotation_per_repeat",
    value=math.radians(CTPR_TWIST_DEG),  # 45 deg = π/4 rad
    units="rad",
    sigma=0.04096380633913714,
    source=(
        "Kajander et al. (2007) Acta Crystallogr D Biol Crystallogr 63:800–811, "
        "DOI: 10.1107/S0907444907024353, PMID: 17582171 "
        "(CTPR8: eight tandem repeats complete one superhelical turn → 360°/8 = 45°). "
        "Bismut et al. (2025) Protein Science 34:e70150, DOI: 10.1002/pro.70150"
    ),
    system="Designed consensus TPR arrays (CTPR8 / CTPR20), crystal lattice",
    method="X-ray crystallography of CTPR superhelices (PDB 2AVP / 2FO7 / 2HYZ)",
    notes=(
        "Superhelical twist between successive repeats, not ~24° A/B tilt. "
        "Stored in radians: CTPR_TWIST_DEG 45 degrees = π/4 rad. "
        "45° is inside the deposited twist range and keeps eight repeats "
        "per turn. The deposited mean twist is not exactly 45°. "
        "sigma is that sample standard deviation converted from degrees "
        "to radians, not the previous 0.12 rad engineering width."
    ),
    provenance="literature_placeholder",
    calibrated=False,
)

CTPR_RADIUS_A = Parameter(
    name="ctpr_docking_radius",
    value=(CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM) * _NM_TO_A,
    units="Å",
    sigma=5.0,
    source=(
        "Scaffold cylinder: CLASP Docs §2.4 / steric_checker scaffold cylinder "
        "(CTPR_RADIUS_NM = 1.8 nm). "
        "Docking-loop radial offset: CLASP geometry prior "
        "(loop graft extension beyond cylinder) "
        "(DOCKING_LOOP_OFFSET_NM = 0.35 nm)."
    ),
    system="CTPR scaffold docking-site placement",
    method="Docking radius = scaffold cylinder radius + docking-loop offset",
    notes=(
        "Stored in Å after explicit conversion: 1 nm = 10 Å. "
        "(CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM) × 10 "
        "= (1.8 + 0.35) × 10 = 21.5 Å. "
        "sigma is the existing Jacobian engineering width, not a standard "
        "deviation quoted from the source above."
    ),
    provenance="literature_placeholder",
    calibrated=False,
)

# Scaffold excluded-volume cylinder.
# src.core.ctpr_geometry.CTPR_RADIUS_NM is 1.8 nm (repeat-center radial distance).
# 1 nm = 10 Å, so the value stored here is 1.8 nm × 10 = 18.0 Å.
# Source text is copied from the CTPR_RADIUS_NM comment in src/core/ctpr_geometry.py.
# That module does not define a numeric sigma for CTPR_RADIUS_NM, so sigma stays
# the existing Jacobian width already stored on this Parameter.
CTPR_SCAFFOLD_RADIUS_A = Parameter(
    name="ctpr_scaffold_radius",
    value=CTPR_RADIUS_NM * _NM_TO_A,  # 1.8 nm × 10 = 18.0 Å; 1 nm = 10 Å
    units="Å",
    sigma=3.0,
    source="CLASP Docs §2.4 / steric_checker scaffold cylinder",
    system="Consensus TPR (CTPR) scaffold cylinder",
    method="Cylinder approximation of the scaffold excluded volume",
    notes=(
        "Excluded-volume radius of the scaffold cylinder, from CTPR_RADIUS_NM "
        "(repeat-center radial distance). 1 nm = 10 Å, so 1.8 nm × 10 = 18.0 Å. "
        "Docking-site coordinates use CTPR_RADIUS_A, which adds DOCKING_LOOP_OFFSET_NM "
        "before the same nm-to-Å conversion. "
        "sigma is the existing Jacobian engineering width on this Parameter. "
        "src.core.ctpr_geometry does not define a numeric sigma for CTPR_RADIUS_NM. "
        "The steric model uses a cylinder, not molecular surfaces."
    ),
    provenance="literature_placeholder",
    calibrated=False,
)

# Globular-protein size scale, not a measured OtsA/OtsB radius.
DEFAULT_PAYLOAD_RADIUS_A = Parameter(
    name="default_payload_radius",
    value=25.0,
    units="Å",
    sigma=8.0,
    source="Order-of-magnitude hydrodynamic radius for a ~40–60 kDa globular enzyme",
    system="Unspecified globular payload",
    method="MW scaling heuristic, not scattering or structure of CLASP payloads",
    notes="Per-payload radii should replace this when structures exist.",
)

# Gaussian chain uses σ² = <R²> = N b² (mean-square end-to-end), not the
# per-axis variance Nb²/3. See linkers.py.
LINKER_SIGMA_A = Parameter(
    name="gaussian_chain_linker_sigma",
    value=18.0,
    units="Å",
    sigma=6.0,
    source="Flexible-fusion Gaussian-chain engineering prior (not a measured persistence length)",
    system="Unspecified peptide linker between fusion terminus and functional site",
    method="Gaussian-chain C_eff; worm-like chain not yet used",
    notes="σ is sqrt(<R^2>), RMS end-to-end. Not a measured persistence length.",
)

# Kd only. Association rate is not in this paper; do not invent kon.
CAM_M13_KD_M = Parameter(
    name="cam_m13_kd",
    value=0.19e-9,
    units="M",
    sigma=0.09e-9,
    source=(
        "Biochemistry 2006, 45(41):12547-12559, DOI 10.1021/bi060857u. "
        "WT CaM + WT M13, fluorescence competition, Kd = 0.19 ± 0.09 nM."
    ),
    system="Ca2+-saturated calmodulin and skeletal MLCK M13 peptide, in vitro titration",
    method="Fluorescence competition vs dansyl probe",
    notes=(
        "Peptide Kd, not a CLASP fusion and not this project's assay. "
        "kon is not reported; recruitment time course requires a user-supplied kon."
    ),
)

N_REPEATS_MIN = 3
N_REPEATS_MAX = 24


def all_priors() -> tuple[Parameter, ...]:
    return (
        CTPR_RISE_A,
        CTPR_ROTATION_RAD,
        CTPR_RADIUS_A,
        CTPR_SCAFFOLD_RADIUS_A,
        DEFAULT_PAYLOAD_RADIUS_A,
        LINKER_SIGMA_A,
        CAM_M13_KD_M,
    )
