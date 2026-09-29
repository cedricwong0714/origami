"""3D export repeats the chassis coordinates and does not invent a sequence."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from origami.physical.deposited import placed_ca_cloud
from origami.physical.geometry import build_ctpr

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "export_ctpr_3d.py"


def _module():
    spec = importlib.util.spec_from_file_location("export_ctpr_3d", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pdb_matches_placed_cloud_and_docking_sites(tmp_path: Path) -> None:
    module = _module()
    paths = module.export_ctpr_3d((8,), tmp_path)
    pdb = next(path for path in paths if path.suffix == ".pdb").read_text(
        encoding="utf-8"
    )
    atoms = [line for line in pdb.splitlines() if line.startswith("ATOM")]
    docs = [line for line in pdb.splitlines() if line.startswith("HETATM")]
    assert len(atoms) == 8 * 34
    assert len(docs) == 8
    assert "UNK" in atoms[0]
    assert "DOC" in docs[0]
    assert "calibrated = false" in pdb
    geom = build_ctpr(8)
    cloud = placed_ca_cloud(8, geom.rise_A, geom.rotation_rad)
    exported = np.array(
        [[float(line[30:38]), float(line[38:46]), float(line[46:54])] for line in atoms]
    )
    assert np.allclose(exported, cloud, atol=5e-4)
    junction = np.array(
        [float(docs[0][30:38]), float(docs[0][38:46]), float(docs[0][46:54])]
    )
    assert np.allclose(junction, geom.sites[0].xyz_A, atol=5e-4)


def test_n_outside_library_is_rejected() -> None:
    module = _module()
    try:
        module.parse_n_list("2")
    except ValueError as exc:
        assert "n must be in" in str(exc)
    else:
        raise AssertionError("n=2 should be rejected")
