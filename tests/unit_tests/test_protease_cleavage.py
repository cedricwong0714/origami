"""Protease–substrate cleavage profile tests."""

import numpy as np
import pytest

from src.core.schema import DesignSpec, MechanismType, ScaffoldSpec
from src.ode_model.solver import run_system_simulation
from src.profiles import get_profile
from src.profiles.protease_cleavage import ProteaseCleavageProfile


def _spec() -> DesignSpec:
    return DesignSpec(
        design_id="PROT_TEST_001",
        chassis="E_coli",
        mechanism_type=MechanismType.PROTEASE_CLEAVAGE,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
        ),
        payload_ids=["protease_effector", "cleavage_target"],
        operating_mode="reversible",
    )


def test_protease_cleavage_enum_registered():
    assert MechanismType.PROTEASE_CLEAVAGE.value == "protease_cleavage"
    profile = get_profile(MechanismType.PROTEASE_CLEAVAGE)
    assert isinstance(profile, ProteaseCleavageProfile)
    assert profile.profile_id == "protease_cleavage"


def test_protease_cleavage_ode_runs_and_conserves_mass():
    t, concs = run_system_simulation(
        {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0},
        mechanism_type=MechanismType.PROTEASE_CLEAVAGE,
        num_points=50,
    )
    assert len(t) == 50
    substrate = np.asarray(concs["S"])
    complex_ = np.asarray(concs["ES"])
    product = np.asarray(concs["P"])
    inventory = substrate + complex_ + product
    assert np.allclose(inventory, inventory[0], atol=1e-3)
    assert np.all(substrate >= -1e-9)
    assert np.all(product >= -1e-9)


def test_protease_cleavage_prediction_carries_uncertainty_and_tier():
    profile = get_profile(MechanismType.PROTEASE_CLEAVAGE)
    pred = profile.predict(_spec())
    assert pred.primary_metric_name == "cleaved_fraction"
    assert 0.0 <= pred.primary_metric_value <= 1.0
    lo, hi = pred.uncertainty_95ci
    assert lo <= pred.primary_metric_value <= hi
    assert pred.evidence_maturity.value.startswith("Tier 3")
    assert pred.details["enrichment_v_prox_over_v_basal"] >= 0.0
    assert "Tier-3" in pred.assumptions[0]


def test_protease_cleavage_rejects_missing_target_role():
    from src.core.schema_payloads import PayloadSpec, PayloadRole

    spec = DesignSpec(
        design_id="PROT_BAD_001",
        chassis="E_coli",
        mechanism_type=MechanismType.PROTEASE_CLEAVAGE,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
        ),
        payloads=[
            PayloadSpec(payload_id="p1", role=PayloadRole.PROTEASE_EFFECTOR),
            PayloadSpec(payload_id="p2", role=PayloadRole.PROTEASE_EFFECTOR),
        ],
        operating_mode="reversible",
    )
    profile = get_profile(MechanismType.PROTEASE_CLEAVAGE)
    errors = profile.validate_inputs(spec)
    assert any("cleavage_target" in e for e in errors)


def test_protease_cleavage_rejects_single_docking_site():
    spec = DesignSpec(
        design_id="PROT_BAD_002",
        chassis="E_coli",
        mechanism_type=MechanismType.PROTEASE_CLEAVAGE,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR3",
            repeat_count=3,
            docking_positions=[1],
        ),
        payload_ids=["protease_effector", "cleavage_target"],
        operating_mode="reversible",
    )
    profile = get_profile(MechanismType.PROTEASE_CLEAVAGE)
    errors = profile.validate_inputs(spec)
    assert any("≥2" in e or "docking" in e for e in errors)


def test_protease_cleavage_required_controls_and_measurements():
    profile = get_profile(MechanismType.PROTEASE_CLEAVAGE)
    control = profile.required_controls(_spec())
    assert "Catalytic-Dead" in control.mandatory_control_type
    measurements = profile.required_measurements(_spec())
    assert any("cleav" in m.lower() for m in measurements)
    assert any("EGTA" in m or "Ca" in m for m in measurements)


def test_protease_payload_roles_exist():
    from src.core.schema_payloads import PayloadRole

    assert PayloadRole.PROTEASE_EFFECTOR.value == "protease_effector"
    assert PayloadRole.CLEAVAGE_TARGET.value == "cleavage_target"


def test_protease_defaults_json_loadable():
    from src.core.asset_paths import load_kinetic_defaults

    payload = load_kinetic_defaults("protease_cleavage")
    assert payload["mechanism_type"] == "protease_cleavage"
    assert "k_cat_prox" in payload["params"]
    assert "Tier 3" in payload["evidence_maturity_default"]
