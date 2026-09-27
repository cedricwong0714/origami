"""Literature engineering priors.

Every numeric biological/structural constant used by the engine lives here.
None of these values are wet-lab measurements from this project. They are
explicit placeholders with uncertainty, to be replaced when assays exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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


# Superhelical CTPR geometry is taken as an engineering prior consistent with
# designed CTPR crystal structures (CTPR8/CTPR20 superhelices; PDB 2AVP, 2HYZ,
# 2FO7; Kajander et al., 2007, Acta Cryst. D 63:800–811). Exact rise/rotation
# were not re-fitted from coordinates in this repository; wide sigma reflects that.
CTPR_RISE_A = Parameter(
    name="ctpr_rise_per_repeat",
    value=9.0,
    units="Å",
    sigma=2.0,
    source="Kajander et al. (2007) Acta Cryst. D 63:800–811; PDB 2AVP/2HYZ (engineering prior, not refit)",
    system="Designed consensus TPR (CTPR) superhelix",
    method="Literature-informed rigid superhelix; not measured in this project",
    notes="Replace with a fit to project crystal/MD or lab-calibrated geometry.",
)

CTPR_ROTATION_RAD = Parameter(
    name="ctpr_rotation_per_repeat",
    value=0.42,  # ~24°, typical TPR solenoid twist; 8 repeats is protein length not pitch
    units="rad",
    sigma=0.12,
    source="Engineering prior informed by designed CTPR superhelices (Kajander et al., 2007)",
    system="CTPR solenoid",
    method="Rigid-body helical repeat; not fitted to this project's structures",
    notes="Uncertainty is intentionally large until a structure-derived twist is stored.",
)

CTPR_RADIUS_A = Parameter(
    name="ctpr_docking_radius",
    value=22.0,
    units="Å",
    sigma=5.0,
    source="Engineering prior: TPR concave/convex face offset on the order of a TPR domain radius",
    system="CTPR scaffold docking-site placement",
    method="Spherical offset from superhelical axis; not payload-specific",
    notes="Does not encode a real fusion terminus until payload structures are reviewed.",
)

CTPR_SCAFFOLD_RADIUS_A = Parameter(
    name="ctpr_scaffold_radius",
    value=12.0,
    units="Å",
    sigma=3.0,
    source="Engineering prior for a helical repeat bundle excluded volume",
    system="CTPR scaffold body",
    method="Cylinder approximation",
    notes="MVP steric model uses a cylinder, not molecular surfaces.",
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
