"""Export deterministic CTPR screw coordinates for a 3D viewer.

This script does not call a language model and does not invent a sequence,
a payload radius, or a graft site. Coordinates come from the same chassis
as the structural-analysis API: the deposited Cα consensus placed on the
runtime screw.

Open the ``.pdb`` in PyMOL or ChimeraX. Chain A is Cα only (residue name
UNK, because this file does not copy a sequence). Chain B is one
pseudoatom per docking site (residue name DOC). DOC is not an amino acid.

``calibrated`` stays false. The file is not a crystal structure of the fusion.

Usage
-----
From the repository root::

    python scripts/export_ctpr_3d.py
    python scripts/export_ctpr_3d.py --n 3,8,14 --out data/exports/ctpr_3d
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from origami.physical.backbone import backbone_constructs, m13_graft_index
from origami.physical.deposited import placed_ca_cloud
from origami.physical.geometry import build_ctpr
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN

_RESIDUES_PER_REPEAT = 34


def parse_n_list(raw: str) -> tuple[int, ...]:
    """Parse a comma-separated repeat list inside the library bounds."""
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if not parts:
        raise ValueError("n list is empty")
    values: list[int] = []
    for part in parts:
        n_repeats = int(part)
        if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
            raise ValueError(
                f"n must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}], got {n_repeats}"
            )
        if n_repeats not in values:
            values.append(n_repeats)
    return tuple(values)


def _atom_line(
    record: str,
    serial: int,
    atom_name: str,
    resname: str,
    chain: str,
    resseq: int,
    xyz: np.ndarray,
    element: str,
) -> str:
    x, y, z = (float(xyz[0]), float(xyz[1]), float(xyz[2]))
    return (
        f"{record:<6s}{serial:5d} {atom_name:4s} {resname:>3s} {chain}"
        f"{resseq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}{1.00:6.2f}{0.00:6.2f}"
        f"          {element:>2s}"
    )


def scaffold_pdb(n_repeats: int) -> str:
    """PDB text for one CTPR screw. Cα on chain A, docking sites on chain B."""
    geom = build_ctpr(n_repeats)
    cloud = placed_ca_cloud(n_repeats, geom.rise_A, geom.rotation_rad)
    if cloud.shape != (n_repeats * _RESIDUES_PER_REPEAT, 3):
        raise RuntimeError("Cα cloud length does not match 34 residues per repeat")
    lines = [
        "REMARK   1 COMPUTATIONAL CTPR SCREW. NOT A DEPOSITED CRYSTAL.",
        "REMARK   1 calibrated = false. Side chains are absent.",
        "REMARK   1 Chain A: consensus C-alpha, residue name UNK (no sequence copied).",
        "REMARK   1 Chain B: docking-site pseudoatoms. DOC is not an amino acid.",
        "REMARK   1 Residue name M13 marks the team-supplied graft site.",
        "REMARK   1 SpyCatcher, flx, and LgBiT lengths are not in this file.",
        f"REMARK   1 n_repeats = {n_repeats}",
    ]
    graft_index = m13_graft_index(n_repeats)
    if graft_index is None:
        lines.append("REMARK   1 No m13 graft was named for this n.")
    else:
        lines.append(
            f"REMARK   1 m13 graft is 1-based repeat {graft_index + 1}, index {graft_index}."
        )
    serial = 1
    for index, xyz in enumerate(cloud):
        repeat = index // _RESIDUES_PER_REPEAT
        residue = index % _RESIDUES_PER_REPEAT
        resseq = repeat * _RESIDUES_PER_REPEAT + residue + 1
        lines.append(_atom_line("ATOM", serial, " CA ", "UNK", "A", resseq, xyz, "C"))
        serial += 1
    lines.append("TER")
    for site in geom.sites:
        resname = (
            "M13"
            if graft_index is not None and int(site.index) == graft_index
            else "DOC"
        )
        lines.append(
            _atom_line(
                "HETATM",
                serial,
                " CA ",
                resname,
                "B",
                int(site.index) + 1,
                site.xyz_A,
                "C",
            )
        )
        serial += 1
    lines.append("TER")
    lines.append("END")
    return "\n".join(lines) + "\n"


def scaffold_record(n_repeats: int, row: dict) -> dict:
    """JSON sidecar: coordinates plus the distances the chassis already computed."""
    geom = build_ctpr(n_repeats)
    cloud = placed_ca_cloud(n_repeats, geom.rise_A, geom.rotation_rad)
    end = row["end_junction"]
    graft = row.get("m13_graft")
    return {
        "calibrated": False,
        "payloads": False,
        "m13_graft_repeat_index": None
        if row.get("m13_graft") is None
        else int(row["m13_graft"]["repeat_index"]),
        "m13_graft_repeat_1based": None
        if row.get("m13_graft") is None
        else int(row["m13_graft"]["repeat_1based"]),
        "n_repeats": int(n_repeats),
        "units": "Å",
        "residues_per_repeat": _RESIDUES_PER_REPEAT,
        "sequence_copied": False,
        "ca_A": np.round(cloud, 3).tolist(),
        "docking_sites_A": [
            {
                "repeat_index": int(site.index),
                "x_A": round(float(site.xyz_A[0]), 3),
                "y_A": round(float(site.xyz_A[1]), 3),
                "z_A": round(float(site.xyz_A[2]), 3),
            }
            for site in geom.sites
        ],
        "graft_to_n_chord_A": None if graft is None else float(graft["to_n_end"]["chord_A"]),
        "graft_to_c_chord_A": None if graft is None else float(graft["to_c_end"]["chord_A"]),
        "end_chord_A": float(end["chord_A"]),
        "end_chord_95_low_A": float(end["chord_95_low_A"]),
        "end_chord_95_high_A": float(end["chord_95_high_A"]),
        "axial_span_A": float(row["axial_span_A"]),
        "phase_deg": float(end["phase_deg"]),
        "facing_cosine": float(end["facing_cosine"]),
        "notes": [
            "Coordinates are the runtime screw. This is not a crystal of the fusion.",
            "Chain B in the PDB is the docking site, not a payload center.",
        ],
    }


def export_ctpr_3d(n_values: tuple[int, ...], out_dir: Path) -> list[Path]:
    """Write one PDB and one JSON per n, plus a manifest. Return written paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = backbone_constructs(n_values)
    by_n = {int(row["n_repeats"]): row for row in bundle["constructs"]}
    written: list[Path] = []
    manifest_rows = []
    for n_repeats in n_values:
        pdb_path = out_dir / f"ctpr_n{n_repeats}.pdb"
        json_path = out_dir / f"ctpr_n{n_repeats}.json"
        pdb_path.write_text(scaffold_pdb(n_repeats), encoding="utf-8")
        record = scaffold_record(n_repeats, by_n[n_repeats])
        json_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        written.extend([pdb_path, json_path])
        manifest_rows.append(
            {
                "n_repeats": n_repeats,
                "pdb": pdb_path.name,
                "json": json_path.name,
                "end_chord_A": record["end_chord_A"],
                "calibrated": False,
            }
        )
    manifest = out_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "calibrated": False,
                "source": "origami.physical backbone screw",
                "files": manifest_rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(manifest)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", default="3,8,14", help="Comma-separated repeat counts")
    parser.add_argument(
        "--out",
        default="data/exports/ctpr_3d",
        help="Output directory, relative to the repository root unless absolute",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    paths = export_ctpr_3d(parse_n_list(args.n), out_dir)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
