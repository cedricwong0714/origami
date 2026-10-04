"""Software interchange: team sequences, SBOL, GenBank, SBML, passport."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from origami.api.structural import app
from origami.export.benchmark import run_benchmark
from origami.export.constructs import construct_for_n, load_series
from origami.export.genbank import genbank_for_n
from origami.export.pdb_plugin import describe_pdb
from origami.export.profiles import ProfileError, validate_profile
from origami.export.sbml import sbml_from_kinetics_body
from origami.export.sbol import sbol_for_n

ROOT = Path(__file__).resolve().parents[2]


def test_module_indices_match_team_graft():
    from origami.ssdk.features import module_indices

    assert module_indices(3) == (1, 0, 2)
    assert module_indices(8) == (3, 0, 7)
    assert module_indices(14) == (6, 0, 13)


def test_fusion_kd_stays_secondhand_and_kon_unsourced():
    from origami.priors import (
        FUSION_CAM_M13_CA_KD_M,
        PORUMB_1994_CAM_M13_HYBRID_PCA50_M,
        assumed_recruitment_kon_per_M_s,
        unsourced_cam_m13_peptide_kon_per_M_s,
    )

    assert FUSION_CAM_M13_CA_KD_M.value == 80e-9
    assert FUSION_CAM_M13_CA_KD_M.calibrated is False
    assert "Secondhand" in FUSION_CAM_M13_CA_KD_M.notes
    assert "8e-8" in FUSION_CAM_M13_CA_KD_M.notes
    assert PORUMB_1994_CAM_M13_HYBRID_PCA50_M.value == 500e-9
    assert unsourced_cam_m13_peptide_kon_per_M_s() is None
    assert assumed_recruitment_kon_per_M_s() == 1.0e6


def test_camsol_method_doi_on_series():
    doc = load_series()
    assert doc["camsol_method"]["doi"] == "10.1101/cshperspect.a033845"
    assert doc["calibrated"] is False
    lengths = {row["n_repeats"]: row["length_aa"] for row in doc["constructs"]}
    assert lengths == {3: 413, 8: 603, 14: 787}
    row8 = construct_for_n(8)
    assert row8["cam_on_scaffold"] is False
    assert row8["m13_on_scaffold"] is True
    assert row8["camsol_intrinsic_score"] == 1.127802


def test_genbank_and_sbol_contain_team_sequence():
    seq = construct_for_n(3)["sequence"]
    gb = genbank_for_n(3)
    assert "ORIGIN" in gb and "aa" in gb.splitlines()[0]
    assert seq[:12] in gb.replace(" ", "").replace("\n", "")
    sbol = sbol_for_n(8)
    assert "sbol:Component" in sbol
    assert construct_for_n(8)["sequence"] in sbol


def test_sbml_recruitment_and_spy():
    rec = sbml_from_kinetics_body({"mode": "recruitment_steady", "c_free_M": 1e-6})
    assert "origami_recruitment" in rec
    spy = sbml_from_kinetics_body({"mode": "covalent_timecourse", "tag0_M": 1e-6, "catcher0_M": 1e-6})
    assert "k_on" in spy and "adduct" in spy


def test_profile_rejects_invented_ode():
    try:
        validate_profile({"mode": "custom_hill"})
    except ProfileError as exc:
        assert "will not compile a new ODE" in str(exc)
    else:
        raise AssertionError("custom ODE must be rejected")
    ok = validate_profile({"mode": "recruitment_steady", "c_free_M": 1e-6})
    assert ok["accepted"] is True


def test_pdb_plugin_does_not_claim_screw():
    pdb = (
        "ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00  0.00           C\n"
        "ATOM      2  CA  ALA A   2       3.800   0.000   0.000  1.00  0.00           C\n"
    )
    report = describe_pdb(pdb, "A")
    assert report["replaces_ctpr_screw"] is False
    assert report["n_ca"] == 2
    assert report["calibrated"] is False


def test_benchmark_passes():
    report = run_benchmark()
    assert report["passed"] is True
    assert report["calibrated"] is False


def test_export_api_genbank_and_passport():
    client = TestClient(app)
    gb = client.get("/api/export/genbank/8")
    assert gb.status_code == 200
    assert "CTPRN8" in gb.text
    passport = client.post("/api/export/passport", json={"n_repeats": 8})
    assert passport.status_code == 200
    body = passport.json()
    assert body["calibrated"] is False
    assert body["team_construct"]["length_aa"] == 603


def test_cli_export_genbank():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "-m", "src.ui.cli", "export-genbank", "--n-repeats", "3"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "ORIGIN" in r.stdout
