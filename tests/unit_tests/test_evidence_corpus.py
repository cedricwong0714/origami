"""Curated evidence corpus integrity checks (no network)."""

from src.evidence_engine.corpus import DEFAULT_EVIDENCE_STORE, corpus_size
from src.ui.explore_mode import ExploreMode


def test_corpus_has_core_clasp_parameters():
    assert corpus_size() >= 10
    required = {
        "k_cat_OtsA",
        "cam_m13_kd_ca_sat_M",
        "nanobit_intrinsic_kd_M",
        "nanobit_max_distance_nm",
        "inter_m13_spacing_3_repeats_nm",
        "ctpr_rise_per_repeat_nm",
    }
    assert required.issubset(DEFAULT_EVIDENCE_STORE.keys())


def test_every_entry_has_doi_citation():
    for key, entry in DEFAULT_EVIDENCE_STORE.items():
        assert entry.citation.doi, f"{key} missing DOI"
        assert entry.citation.year >= 1990
        assert 0.0 < entry.confidence_score <= 1.0


def test_explore_classifies_literature_vs_assay():
    mode = ExploreMode()
    otsa = mode.ask("k_cat_OtsA")
    assert otsa["status"] == "OK"
    assert otsa["evidence_class"] == "direct_evidence"

    kd = mode.ask("cam_m13_kd_ca_sat_M")
    assert kd["status"] == "OK"
    assert kd["evidence_class"] == "model_inference"
    assert kd.get("inference_note")
