import numpy as np

from origami.physical.linkers import gaussian_chain_ceff_M
from origami.physical.score import physics_report


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
