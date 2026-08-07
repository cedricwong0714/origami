"""Export helpers for Design Mode wiki / judging artifacts."""

from src.ui.export_utils import (
    interaction_class_to_mechanism,
    passport_json_bytes,
    wiki_markdown_snippet,
)
from src.core.schema import DesignSpec, MechanismType, ScaffoldSpec
from src.scaffold_optimizer import InteractionClass


def test_interaction_class_maps_to_mechanism():
    assert interaction_class_to_mechanism(InteractionClass.METABOLIC) == (
        MechanismType.INTERMEDIATE_TRANSFER
    )
    assert interaction_class_to_mechanism(InteractionClass.BINDING) == (
        MechanismType.TARGET_COMPLEMENTATION
    )


def test_passport_json_includes_honesty_note():
    blob = passport_json_bytes(
        {
            "design_id": "T1",
            "status": "SUCCESS",
            "passport": {"mechanism_profile": "trehalose_synthesis"},
        }
    )
    text = blob.decode("utf-8")
    assert "T1" in text
    assert "Not wet-lab validation" in text


def test_wiki_snippet_includes_uncertainty_disclaimer():
    spec = DesignSpec(
        design_id="W1",
        chassis="E_coli",
        mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
        ),
        payload_ids=["OtsA", "OtsB"],
    )
    md = wiki_markdown_snippet(
        {
            "passport": {
                "mechanism_profile": "trehalose_synthesis",
                "evidence_maturity": "Tier 2",
                "biosecurity_review_state": "pass_allowlist",
                "steric_feasible": True,
            },
            "prediction": {
                "primary_metric_name": "channeling_index",
                "primary_metric_value": 0.42,
                "unit": "relative",
                "uncertainty_95ci": [0.3, 0.55],
            },
        },
        spec=spec,
    )
    assert "CTPR5" in md
    assert "95% CI" in md
    assert "not experimental validation" in md.lower() or "Not wet-lab" in md or "software checks" in md
