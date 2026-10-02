"""Literature engineering priors.

Every numeric biological/structural constant used by the engine lives here.
None of these values are wet-lab measurements from this project. They are
explicit placeholders with uncertainty, to be replaced when assays exist.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Literal, Optional

from origami.linker_prior import ggggs_linker_rms_A
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
    sigma: float | None
    source: str
    system: str
    method: str
    notes: str
    provenance: Provenance = "literature_placeholder"
    calibrated: bool = False

    def interval_95(self) -> tuple[float, float] | None:
        if self.sigma is None:
            return None
        return (self.value - 1.96 * self.sigma, self.value + 1.96 * self.sigma)


def get_parameter_or_warn(
    name: str,
    value: Optional[float],
    source: Optional[str],
) -> Optional[float]:
    """Return a sourced biological value, or warn and return None if vacant."""
    if value is None or source is None:
        warnings.warn(
            f"Biological parameter '{name}' has no verified "
            f"source. This parameter must not be used in a "
            f"production prediction or a wet-lab decision. "
            f"Find a peer-reviewed source before proceeding.",
            UserWarning,
            stacklevel=2,
        )
        return None
    return value


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

# Sample standard deviations of the seven deposited steps (divisor n-1).
# Locked to origami.physical.deposited by tests. Not recomputed here, so
# this module does not import the physical package.
_JUNCTION_RADIUS_SAMPLE_STD_A = 0.7344357597832961
_CENTROID_RADIUS_SAMPLE_STD_A = 0.5696084155839191


CTPR_RADIUS_A = Parameter(
    name="ctpr_docking_radius",
    value=(CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM) * _NM_TO_A,
    units="Å",
    sigma=_JUNCTION_RADIUS_SAMPLE_STD_A,
    source=(
        "Junction of consecutive 34-residue blocks in PDB 2AVP, 2HYZ, and 2FO7. "
        "Kajander et al. (2007) Acta Crystallogr D Biol Crystallogr 63:800-811, "
        "DOI: 10.1107/S0907444907024353. "
        "The junction is the midpoint of C-alpha 34 and C-alpha 1 of the next block."
    ),
    system="Consensus TPR asymmetric-unit chains",
    method="Mean radial distance of seven inter-repeat junctions",
    notes=(
        "Stored in Å: (CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM) × 10. "
        "That sum is the deposited junction radius. "
        "The previous docking radius was (1.8 + 0.35) nm = 21.5 Å. "
        "sigma is the sample standard deviation of the seven junction radii "
        "(divisor n-1), not a printed standard error."
    ),
    provenance="literature_placeholder",
    calibrated=False,
)

# Repeat-centroid radius. Clash does not use this as a cylinder.
# 1 nm = 10 Å. sigma is the sample standard deviation of the seven centroids.
CTPR_SCAFFOLD_RADIUS_A = Parameter(
    name="ctpr_scaffold_radius",
    value=CTPR_RADIUS_NM * _NM_TO_A,
    units="Å",
    sigma=_CENTROID_RADIUS_SAMPLE_STD_A,
    source=(
        "Repeat-centroid radius of PDB 2AVP, 2HYZ, and 2FO7. "
        "Kajander et al. (2007) Acta Crystallogr D Biol Crystallogr 63:800-811, "
        "DOI: 10.1107/S0907444907024353."
    ),
    system="Consensus TPR asymmetric-unit chains",
    method="Mean radial distance of the 34-residue C-alpha centroid",
    notes=(
        "Backbone helix radius, from CTPR_RADIUS_NM. 1 nm = 10 Å. "
        "The previous cylinder prior was 1.8 nm (18.0 Å). "
        "sigma is the sample standard deviation of the seven centroids. "
        "Payload overlap uses the placed C-alpha trace, not this radius."
    ),
    provenance="literature_placeholder",
    calibrated=False,
)

# Parameter: default payload clash radius
# Value: 22.513126 (2BBM chain A; equals data/structures/payload_radii.json)
# Units: Å
# Source: derived by scripts/derive_payload_radii.py from deposited PDB 2BBM,
#   the CaM-skeletal-MLCK-peptide complex (entry citation not retrieved)
# System: calmodulin in the CaM-M13 complex, the only payload in the lab plan
# Method: sqrt(5/3) x C-alpha radius of gyration, one NMR model set, side chains ignored
# Notes: sigma 4.76 Å is the sample SD (n-1) of the three CaM states in the same
#   file (compact 1PRW 18.9, complex 2BBM 22.5, extended 1CLL 28.3). It is a
#   conformational spread, not a measurement error. Replaces the 25 Å MW-scaling
#   placeholder on 2026-10-02 at the user's instruction that CaM-M13 is the only
#   payload. SpyTag/SpyCatcher and LgBiT/SmBiT are core modules, not payloads.
DEFAULT_PAYLOAD_RADIUS_A = Parameter(
    name="default_payload_radius",
    value=22.513126052270536,
    units="Å",
    sigma=4.763419705374408,
    source="PDB 2BBM via scripts/derive_payload_radii.py; spread from 1PRW, 2BBM, 1CLL",
    system="Calmodulin in CaM-M13 complex",
    method="sqrt(5/3) x C-alpha Rg; side chains ignored; flexible termini inflate it",
    notes="calibrated stays False. Not a hydrodynamic radius.",
)

# σ = sqrt(<R²>) of one (GGGGS)3 chain. See origami.linker_prior.
# No standard error was printed for the persistence length, so sigma is 0.
_LINKER_RMS_A = ggggs_linker_rms_A()
LINKER_SIGMA_A = Parameter(
    name="gaussian_chain_linker_sigma",
    value=_LINKER_RMS_A,
    units="Å",
    sigma=0.0,
    source=(
        "van Rosmalen, Krom, Merkx (2017) Biochemistry 56:6565-6574, "
        "DOI: 10.1021/acs.biochem.7b00902. "
        "b0 = 3.8 Å. G4S2 persistence length = 3.7 Å."
    ),
    system="(GGGGS)3 tether, using the nearest measured G4S2 persistence length",
    method="Kratky-Porod RMS end-to-end of 15 residues",
    notes=(
        "σ is sqrt(<R^2>) for one chain, not the previous 18 Å engineering prior. "
        "(GGGGS) is 80% glycine and G4S2 (GGGGSS) is 67% glycine. "
        "The value was not interpolated. sigma is 0 because the paper does not "
        "print a standard error for 3.7 Å. A pair of tethers adds the variances."
    ),
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

# Parameter: SpyTag–SpyCatcher apparent second-order rate (parental pair)
# Value: 1.4e3
# Units: M^-1 s^-1
# Source: Zakeri et al. (2012) PNAS 109:E690-E697, DOI: 10.1073/pnas.1115485109
# System: SpyTag-MBP + SpyCatcher, 10 μM each, phosphate-citrate, 25 °C
# Method: SDS-PAGE of unreacted SpyCatcher vs time; second-order plot
# Notes: Apparent bimolecular rate of covalent adduct. Not k_on of a
#        reversible complex, not SpyTag003, not this team's fusion.
SPY_K_ON_PER_M_S = Parameter(
    name="spy_k_on_per_M_s",
    value=1.4e3,
    units="M^-1 s^-1",
    sigma=43.0,
    source=(
        "Zakeri et al. (2012) Proc Natl Acad Sci USA 109:E690–E697, "
        "DOI: 10.1073/pnas.1115485109. "
        "Second-order rate constant 1.4 × 10^3 ± 43 M^-1 s^-1 (SD, n = 3)."
    ),
    system=(
        "SpyTag-MBP and SpyCatcher, 10 μM each, phosphate-citrate buffer, "
        "25 °C; covalent product by SDS-PAGE"
    ),
    method=(
        "Partners mixed 1, 3, or 5 min; 95 °C SDS quench; Coomassie band "
        "of unreacted SpyCatcher; 1/[Catcher] vs time slope"
    ),
    notes=(
        "Literature prior for the lumped irreversible bimolecular step in "
        "origami.kinetics.covalent, mapped onto spy_k_on_per_M_s. "
        "Not a three-step (k_on, k_rev, k_bond) decomposition. "
        "Keeble et al. (2017) Angew Chem Int Ed, DOI: 10.1002/anie.201707623, "
        "later report 1.7 ± 0.4 × 10^3 M^-1 s^-1 for the parental pair; "
        "that re-measurement is not the canonical prior. "
        "Do not use models/kinetic_models/covalent_capture.defaults.json "
        "(unsourced relative k_rev=0.05, k_bond=2.0). "
        "Do not use clasp_assembly k_lock=0.003 s^-1; that number is not "
        "printed in Zakeri 2012. calibrated stays false."
    ),
    provenance="literature_placeholder",
    calibrated=False,
)

# Parameter: LgBiT–SmBiT (NanoBiT) intrinsic Kd
# Value: 190e-6
# Units: M
# Source: Dixon et al. (2016) ACS Chem Biol 11:400-408, DOI: 10.1021/acschembio.5b00753
# System: Isolated NanoBiT fragments (not a CLASP fusion)
# Method: Intrinsic affinity of the complementation reporter
NANOBIT_KD_M = Parameter(
    name="nanobit_kd_M",
    value=190e-6,
    units="M",
    sigma=None,
    source=(
        "Dixon et al. (2016) ACS Chem Biol 11:400–408, "
        "DOI: 10.1021/acschembio.5b00753. Intrinsic Kd = 190 μM."
    ),
    system="Untethered LgBiT + SmBiT (NanoBiT) fragments, biochemical assay",
    method="Intrinsic fragment affinity reported in the abstract and main text",
    notes=(
        "No printed sigma in the abstract; sigma stays null (not stored as 0). "
        "The complementation ODE uses k_on and k_off. This printed Kd is "
        "reported beside k_off/k_on and is not substituted. "
        "Not a Hong Kong team fusion measurement."
    ),
    calibrated=False,
)

# Parameter: NanoBiT intrinsic association rate
# Value: 500
# Units: M^-1 s^-1
# Source: Dixon et al. (2016) ACS Chem Biol, DOI: 10.1021/acschembio.5b00753
# System: Isolated NanoBiT fragments
# Method: Intrinsic kon (Figure s12); reported as approximately 500
NANOBIT_K_ON_PER_M_S = Parameter(
    name="nanobit_k_on_per_M_s",
    value=500.0,
    units="M^-1 s^-1",
    sigma=None,
    source=(
        "Dixon et al. (2016) ACS Chem Biol 11:400–408, "
        "DOI: 10.1021/acschembio.5b00753. "
        "Intrinsic kon ≈ 500 M^-1 s^-1 (Figure s12)."
    ),
    system="Untethered LgBiT + SmBiT (NanoBiT) fragments",
    method="Intrinsic association of the complementation reporter",
    notes=(
        "Tilde in the paper; sigma is null, not 0. "
        "nanobit_complementation integrates this rate with k_off. "
        "It is not replaced by k_off / printed Kd."
    ),
    calibrated=False,
)

# Parameter: NanoBiT intrinsic dissociation rate
# Value: 0.2
# Units: s^-1
# Source: Dixon et al. (2016) ACS Chem Biol, DOI: 10.1021/acschembio.5b00753
NANOBIT_K_OFF_PER_S = Parameter(
    name="nanobit_k_off_per_s",
    value=0.2,
    units="s^-1",
    sigma=None,
    source=(
        "Dixon et al. (2016) ACS Chem Biol 11:400–408, "
        "DOI: 10.1021/acschembio.5b00753. Intrinsic koff = 0.2 s^-1."
    ),
    system="Untethered LgBiT + SmBiT (NanoBiT) fragments",
    method="Intrinsic dissociation of the complementation reporter",
    notes=(
        "Not a fusion assay. nanobit_complementation integrates this rate "
        "with k_on. The quotient k_off/k_on is not overwritten by the printed Kd."
    ),
    calibrated=False,
)

# Parameter: Erickson minimal radius of a protein sphere (lower bound, not a payload radius)
# Value: R_min [nm] = 0.066 * M^(1/3), M in Da
# Source: Erickson HP (2009) Biol Proced Online 11:32-51, DOI: 10.1007/s12575-009-9008-x, Eq. 2.2
# Notes: Retrieved from PMC3055910. Smooth unhydrated sphere containing mass M
#        (v2 = 0.73 cm^3/g). Real proteins are larger; do not use as a clash radius.
#        Paper Table 1 lists 2.4 nm at 50 kDa, which this formula reproduces.
_ERICKSON_RMIN_NM_PER_DA_THIRD = 0.066


def erickson_rmin_A(mw_da: float) -> float:
    """Minimal sphere radius in angstroms for a protein of mass ``mw_da`` in Da."""
    if not math.isfinite(mw_da) or mw_da <= 0:
        raise ValueError("mw_da must be finite and > 0")
    return _ERICKSON_RMIN_NM_PER_DA_THIRD * (mw_da ** (1.0 / 3.0)) * _NM_TO_A


# Parameter: recombinant E. coli OtsA mass
# Value: 54700 Da (abstract: "approximately 54.7 kDa")
# Source: Characterization of Escherichia coli OtsA, a trehalose-6-phosphate synthase
#         from glycosyltransferase family 20. Acta Crystallogr D 58:349-351 (2002).
#         Abstract retrieved via web search; DOI not retrieved.
# Notes: Construct-specific (recombinant, pET expression). Approximate.
OTSA_RECOMBINANT_MW_DA = 54700.0

_KHAN_2024 = (
    "Khan RMN et al. (2024) Nat Commun, DOI: 10.1038/s41467-024-48691-6, Table 1"
)


def _enzyme_param(
    name: str, value: float, sigma: float, units: str, source: str, system: str,
    method: str, notes: str,
) -> Parameter:
    return Parameter(
        name=name, value=value, units=units, sigma=sigma, source=source,
        system=system, method=method, notes=notes,
    )


OTSA_KCAT_PER_S = _enzyme_param(
    "otsa_kcat_per_s", 34.0, 1.0, "s^-1",
    _KHAN_2024 + ' (footnote "taken from reference 46": Errey et al. (2010) '
    "Angew Chem Int Ed 49:1234-1237).",
    "E. coli OtsA, UDP-Glc and G6P substrates",
    "Reported as taken from Errey 2010; assay conditions for this value were not retrieved",
    "Printed as 34 +/- 1 for both substrates. Temperature and buffer unknown. "
    "Not measured in this team's lysate or fusion.",
)
OTSA_KM_UDPGLC_M = _enzyme_param(
    "otsa_km_udp_glucose_M", 1.7e-3, 0.3e-3, "M",
    _KHAN_2024 + " (taken from Errey et al. 2010).", "E. coli OtsA",
    "As above; conditions not retrieved", "Printed as 1.7 +/- 0.3 mM.",
)
OTSA_KM_G6P_M = _enzyme_param(
    "otsa_km_g6p_M", 7.3e-3, 0.6e-3, "M",
    _KHAN_2024 + " (taken from Errey et al. 2010).", "E. coli OtsA",
    "As above; conditions not retrieved", "Printed as 7.3 +/- 0.6 mM.",
)
OTSB_KCAT_PER_S = _enzyme_param(
    "otsb_kcat_per_s", 286.0, 34.0, "s^-1", _KHAN_2024 + ".",
    "E. coli OtsB, substrate trehalose-6-phosphate",
    'Table footnote: "continuous 1H NMR assay at 37 C". The Methods text '
    "also mentions a malachite-green assay; the two descriptions were not reconciled.",
    "Printed as 286 +/- 34. Soluble OtsB needed an MBP-His tag per the text. "
    "Not measured in this team's system.",
)
OTSB_KM_T6P_M = _enzyme_param(
    "otsb_km_t6p_M", 3.6e-3, 0.8e-3, "M", _KHAN_2024 + ".",
    "E. coli OtsB, substrate trehalose-6-phosphate", "As OtsB k_cat",
    "Printed as 3.6 +/- 0.8 mM.",
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
        SPY_K_ON_PER_M_S,
        NANOBIT_KD_M,
        NANOBIT_K_ON_PER_M_S,
        NANOBIT_K_OFF_PER_S,
        OTSA_KCAT_PER_S,
        OTSA_KM_UDPGLC_M,
        OTSA_KM_G6P_M,
        OTSB_KCAT_PER_S,
        OTSB_KM_T6P_M,
    )
