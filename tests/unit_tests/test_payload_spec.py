"""DesignSpec PayloadSpec expansion and legacy payload_ids sync."""

from src.core.schema import (
    DesignSpec,
    MechanismType,
    PayloadRole,
    PayloadSpec,
    ScaffoldSpec,
)
from src.profiles import get_profile


def _scaffold() -> ScaffoldSpec:
    return ScaffoldSpec(scaffold_id="CTPR5", repeat_count=5, docking_positions=[1, 3])


def test_legacy_payload_ids_infer_roles():
    spec = DesignSpec(
        design_id="P1",
        chassis="E_coli",
        mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
        scaffold=_scaffold(),
        payload_ids=["OtsA", "OtsB"],
    )
    assert len(spec.payloads) == 2
    assert spec.payloads[0].role == PayloadRole.UPSTREAM_ENZYME
    assert spec.payloads[1].role == PayloadRole.DOWNSTREAM_ENZYME
    assert spec.role_map() == {"OtsA": "upstream_enzyme", "OtsB": "downstream_enzyme"}


def test_explicit_payloads_sync_ids():
    spec = DesignSpec(
        design_id="P2",
        chassis="cell_free",
        mechanism_type=MechanismType.TARGET_COMPLEMENTATION,
        scaffold=_scaffold(),
        operating_mode="target_triggered",
        payloads=[
            PayloadSpec(payload_id="aptamer_binder", role=PayloadRole.RECOGNITION_COMPONENT),
            PayloadSpec(payload_id="SmBiT", role=PayloadRole.REPORTER_FRAGMENT, fusion_terminus="N"),
        ],
    )
    assert spec.payload_ids == ["aptamer_binder", "SmBiT"]
    errors = get_profile(MechanismType.TARGET_COMPLEMENTATION).validate_inputs(spec)
    assert errors == []


def test_wrong_roles_fail_profile_validation():
    spec = DesignSpec(
        design_id="P3",
        chassis="E_coli",
        mechanism_type=MechanismType.REDOX_TRANSFER,
        scaffold=_scaffold(),
        payloads=[
            PayloadSpec(payload_id="A", role=PayloadRole.UPSTREAM_ENZYME),
            PayloadSpec(payload_id="B", role=PayloadRole.DOWNSTREAM_ENZYME),
        ],
    )
    errors = get_profile(MechanismType.REDOX_TRANSFER).validate_inputs(spec)
    assert any("redox_donor" in e for e in errors)
