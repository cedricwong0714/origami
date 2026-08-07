"""Trans-activation / phosphorylation-transfer profile tests."""

import numpy as np
import pytest

from src.core.schema import DesignSpec, MechanismType, ScaffoldSpec
from src.ode_model.solver import run_system_simulation
from src.profiles import get_profile
from src.profiles.trans_activation import TransActivationProfile


def _spec() -> DesignSpec:
    return DesignSpec(
        design_id="TRANS_TEST_001",
        chassis="E_coli",
        mechanism_type=MechanismType.TRANS_ACTIVATION,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
        ),
        payload_ids=["kinase_donor", "kinase_acceptor"],
        operating_mode="reversible",
    )


def test_trans_activation_enum_registered():
    assert MechanismType.TRANS_ACTIVATION.value == "trans_activation"
    profile = get_profile(MechanismType.TRANS_ACTIVATION)
    assert isinstance(profile, TransActivationProfile)
    assert profile.profile_id == "trans_activation"


def test_trans_activation_ode_runs_and_conserves_mass():
    t, concs = run_system_simulation(
        {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0},
        mechanism_type=MechanismType.TRANS_ACTIVATION,
        num_points=50,
    )
    assert len(t) == 50
    substrate = np.asarray(concs["S"])
    kinase = np.asarray(concs["E"])
    complex_ = np.asarray(concs["ES"])
    product = np.asarray(concs["P"])
    # Mass conservation: S + ES + P should be ~constant (substrate inventory)
    inventory = substrate + complex_ + product
    assert np.allclose(inventory, inventory[0], atol=1e-3)


def test_trans_activation_prediction_carries_uncertainty_and_tier():
    profile = get_profile(MechanismType.TRANS_ACTIVATION)
    pred = profile.predict(_spec())
    assert pred.primary_metric_name == "phosphorylation_fraction"
    assert 0.0 <= pred.primary_metric_value <= 1.0
    lo, hi = pred.uncertainty_95ci
    assert lo <= pred.primary_metric_value <= hi
    assert pred.evidence_maturity.value.startswith("Tier 3")
    assert pred.details["activation_factor_v_prox_over_v_basal"] >= 0.0
    assert "Tier-3" in pred.assumptions[0]


def test_trans_activation_rejects_missing_kinase_role():
    from src.core.schema_payloads import PayloadSpec, PayloadRole

    spec = DesignSpec(
        design_id="TRANS_BAD_001",
        chassis="E_coli",
        mechanism_type=MechanismType.TRANS_ACTIVATION,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
        ),
        payloads=[
            PayloadSpec(payload_id="k1", role=PayloadRole.KINASE_DONOR),
            PayloadSpec(payload_id="k2", role=PayloadRole.KINASE_DONOR),  # no acceptor
        ],
        operating_mode="reversible",
    )
    profile = get_profile(MechanismType.TRANS_ACTIVATION)
    errors = profile.validate_inputs(spec)
    assert any("kinase_acceptor" in e for e in errors)


def test_trans_activation_rejects_single_docking_site():
    spec = DesignSpec(
        design_id="TRANS_BAD_002",
        chassis="E_coli",
        mechanism_type=MechanismType.TRANS_ACTIVATION,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR3",
            repeat_count=3,
            docking_positions=[1],
        ),
        payload_ids=["kinase_donor", "kinase_acceptor"],
        operating_mode="reversible",
    )
    profile = get_profile(MechanismType.TRANS_ACTIVATION)
    errors = profile.validate_inputs(spec)
    assert any("≥2" in e or "docking" in e for e in errors)


def test_trans_activation_required_controls_and_measurements():
    profile = get_profile(MechanismType.TRANS_ACTIVATION)
    control = profile.required_controls(_spec())
    assert "Kinase-Dead" in control.mandatory_control_type
    measurements = profile.required_measurements(_spec())
    assert any("Phos-tag" in m or "phospho" in m.lower() for m in measurements)
    assert any("EGTA" in m or "Ca" in m for m in measurements)


def test_trans_activation_failure_conditions_documented():
    profile = get_profile(MechanismType.TRANS_ACTIVATION)
    conditions = profile.failure_conditions(_spec())
    assert any("Phosphatase" in c for c in conditions)
    assert any("allowlist" in c.lower() for c in conditions)


def test_kinase_payload_roles_exist():
    from src.core.schema_payloads import PayloadRole

    assert PayloadRole.KINASE_DONOR.value == "kinase_donor"
    assert PayloadRole.KINASE_ACCEPTOR.value == "kinase_acceptor"


def test_kinase_defaults_json_loadable():
    from src.core.asset_paths import load_kinetic_defaults

    payload = load_kinetic_defaults("trans_activation")
    assert payload["mechanism_type"] == "trans_activation"
    assert "k_cat_trans" in payload["params"]
    assert "Tier 3" in payload["evidence_maturity_default"]
