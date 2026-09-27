"""Worm-like-chain width of one (GGGGS)3 tether.

van Rosmalen, Krom, and Merkx, Biochemistry 56:6565–6574 (2017),
DOI 10.1021/acs.biochem.7b00902, state that one residue is 3.8 Å and
that a G4S2 linker (GGGGSS) has persistence length 3.7 Å after
conformations with chromophore separation below 22 Å are excluded.
They also state that a long chain has lp = C∞ × b0 / 2.

(GGGGS)n is 80% glycine. G4S2 is 67% glycine. 3.7 Å is the nearest
measured Gly/Ser series in that paper. It is not interpolated to
(GGGGS), and the paper does not print a standard error for 3.7 Å.

The mean-square end-to-end is the Kratky–Porod expression. Its long-chain
limit is 2 × lp × lc, which is the limit implied by lp = C∞ × b0 / 2
together with ⟨R²⟩ = C∞ × n × b0².
"""

from __future__ import annotations

import math

# Parameter: virtual residue length
# Value: 3.8
# Units: Å
# Source: van Rosmalen, Krom, Merkx (2017) Biochemistry 56:6565-6574,
#   DOI: 10.1021/acs.biochem.7b00902
# System: Gly/Ser peptide linkers between ECFP and EYFP
# Method: contour length = n residues × b0, as stated in that paper
# Notes: No standard error is printed for 3.8 Å.
RESIDUE_LENGTH_A = 3.8

# Parameter: G4S2 persistence length
# Value: 3.7
# Units: Å
# Source: van Rosmalen, Krom, Merkx (2017) Biochemistry 56:6565-6574,
#   DOI: 10.1021/acs.biochem.7b00902
# System: ECFP-(GGGGSS)n-EYFP
# Method: worm-like chain fit to FRET, excluding rc < 22 Å
# Notes: The same series was previously reported at 4.5 Å before that
#   exclusion (Evers et al. 2006, DOI 10.1021/bi061288t). The 4.5 Å
#   figure is a different analysis, not a standard error on 3.7 Å.
#   (GGGGS) is not GGGGSS. calibrated stays false.
G4S2_PERSISTENCE_LENGTH_A = 3.7

GGGGS_RESIDUES_PER_COPY = 5
DEFAULT_GGGGS_COPIES = 3


def kratky_porod_mean_square_A(
    n_residues: int,
    persistence_length_A: float = G4S2_PERSISTENCE_LENGTH_A,
    residue_length_A: float = RESIDUE_LENGTH_A,
) -> float:
    """⟨R²⟩ in Å² for a worm-like chain of ``n_residues`` residues."""
    if isinstance(n_residues, bool) or not isinstance(n_residues, int):
        raise TypeError("n_residues must be an integer")
    if n_residues < 1:
        raise ValueError("n_residues must be >= 1")
    if persistence_length_A <= 0.0 or residue_length_A <= 0.0:
        raise ValueError("persistence length and residue length must be > 0")
    contour_A = n_residues * residue_length_A
    ratio = persistence_length_A / contour_A
    return float(
        2.0
        * persistence_length_A
        * contour_A
        * (1.0 - ratio * (1.0 - math.exp(-1.0 / ratio)))
    )


def ggggs_linker_rms_A(copies: int = DEFAULT_GGGGS_COPIES) -> float:
    """RMS end-to-end, in Å, of one (GGGGS)n chain. Default n is 3."""
    if isinstance(copies, bool) or not isinstance(copies, int) or copies < 1:
        raise ValueError("copies must be an integer >= 1")
    mean_square = kratky_porod_mean_square_A(copies * GGGGS_RESIDUES_PER_COPY)
    return float(math.sqrt(mean_square))
