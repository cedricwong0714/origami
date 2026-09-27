import math

import pytest

from origami.linker_prior import (
    G4S2_PERSISTENCE_LENGTH_A,
    RESIDUE_LENGTH_A,
    ggggs_linker_rms_A,
    kratky_porod_mean_square_A,
)
from origami.physical.linkers import gaussian_chain_ceff_M
from origami.physical.score import physics_report
from origami.priors import LINKER_SIGMA_A


def test_default_linker_is_the_ggggs3_wormlike_chain():
    """(GGGGS)3 RMS replaces the unsourced 18 Å width.

    Scientific basis: van Rosmalen et al. 2017, DOI 10.1021/acs.biochem.7b00902,
    b0 = 3.8 Å and G4S2 lp = 3.7 Å. Failure mode: a fixed 18 Å width is not
    that chain, so C_eff is not the published linker.
    """
    n_residues = 15
    expected = math.sqrt(
        kratky_porod_mean_square_A(
            n_residues,
            persistence_length_A=G4S2_PERSISTENCE_LENGTH_A,
            residue_length_A=RESIDUE_LENGTH_A,
        )
    )
    assert G4S2_PERSISTENCE_LENGTH_A == pytest.approx(3.7)
    assert RESIDUE_LENGTH_A == pytest.approx(3.8)
    assert ggggs_linker_rms_A() == pytest.approx(expected)
    assert LINKER_SIGMA_A.value == pytest.approx(expected)
    assert LINKER_SIGMA_A.value != pytest.approx(18.0)
    assert LINKER_SIGMA_A.sigma == 0.0
    assert "10.1021/acs.biochem.7b00902" in LINKER_SIGMA_A.source


def test_ceff_decreases_with_separation():
    close = gaussian_chain_ceff_M(15.0, sigma_A=18.0)
    far = gaussian_chain_ceff_M(80.0, sigma_A=18.0)
    assert close > far > 0


def test_physics_score_penalizes_clash():
    crowded = physics_report(4, payload_indices=[0, 1], radii_A=[28.0, 28.0])
    spaced = physics_report(16, payload_indices=[0, 15], radii_A=[12.0, 12.0])
    assert crowded.steric.p_any_payload_clash > spaced.steric.p_any_payload_clash
    assert crowded.warnings
    assert crowded.calibrated is False
