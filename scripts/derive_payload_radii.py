"""Derive payload size scales from deposited C-alpha coordinates.

Network script. Run once; the result is checked in as
data/structures/payload_radii.json so the engine never needs the network.

For each chain (and each NMR model) the script computes, from C-alpha atoms
only:
  rg_A          radius of gyration about the C-alpha centroid
  r_sphere_A    sqrt(5/3) * rg, radius of a uniform solid sphere with that Rg
  r_max_A       largest C-alpha distance from the centroid
These are geometric descriptors of the deposited coordinates. They are not
hydrodynamic radii, they ignore side chains, and flexible termini inflate them.
"""

from __future__ import annotations

import json
import math
import statistics
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "structures" / "payload_radii.json"

# (key, pdb_id, chains, description of what the entry is, role note)
ENTRIES = [
    ("spycatcher", "4MLI", ["A", "C"], "SpyCatcher (S. pyogenes FbaB-derived), complex with SpyTag",
     "Li et al. (2014) J Mol Biol, DOI 10.1016/j.jmb.2013.10.021"),
    ("nanoluc_proxy_for_lgbit", "5IBO", ["A", "B"], "NanoLuc luciferase (full, unsplit)",
     "PROXY ONLY: no LgBiT or NanoBiT structure was found; LgBiT is an engineered NanoLuc fragment"),
    ("lgbit", "7SNY", ["A"], "NanoBiT large subunit LgBiT alone, 2.10 A",
     "Verified title and resolution via RCSB core API; citation not retrieved"),
    ("lgbit_in_nanobit_complex", "7SNX", ["A"], "LgBiT chain of LgBiT-SmBiT complex, 1.70 A",
     "Verified title and resolution via RCSB core API; entity map checked via RCSB: chain A LgBiT, chain B the 11-mer SmBiT peptide"),
    ("calmodulin_compact", "1PRW", ["A"], "Bovine Ca2+-calmodulin, compact form",
     "Fallon and Quiocho (2003) Structure, DOI 10.1016/j.str.2003.09.004"),
    ("calmodulin_extended", "1CLL", ["A"], "Ca2+-calmodulin, extended dumbbell form",
     "Chattopadhyaya et al. 1992 entry; citation not retrieved"),
    ("calmodulin_m13_complex", "2BBM", ["A"], "Calmodulin chain of CaM-skeletal-MLCK-peptide NMR complex",
     "Ikura et al. 1992 entry; citation not retrieved; peptide chain excluded"),
    ("otsa_ecoli", "1GZ5", ["A", "B", "C", "D"], "E. coli OtsA monomer",
     "Gibson et al. (2002) Chem Biol, DOI 10.1016/S1074-5521(02)00292-2"),
]


def fetch_pdb(pdb_id: str) -> str:
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode()


def ca_by_model(text: str, chain: str) -> list[list[tuple[float, float, float]]]:
    models: list[list[tuple[float, float, float]]] = [[]]
    for line in text.splitlines():
        if line.startswith("ENDMDL"):
            models.append([])
        elif line.startswith("ATOM") and line[12:16].strip() == "CA":
            if line[21] != chain or line[16] not in (" ", "A"):
                continue
            models[-1].append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
    return [m for m in models if m]


def descriptors(coords: list[tuple[float, float, float]]) -> dict[str, float]:
    n = len(coords)
    cx = sum(c[0] for c in coords) / n
    cy = sum(c[1] for c in coords) / n
    cz = sum(c[2] for c in coords) / n
    d2 = [(c[0] - cx) ** 2 + (c[1] - cy) ** 2 + (c[2] - cz) ** 2 for c in coords]
    rg = math.sqrt(sum(d2) / n)
    return {"n_ca": n, "rg_A": rg, "r_sphere_A": math.sqrt(5.0 / 3.0) * rg,
            "r_max_A": math.sqrt(max(d2))}


def main() -> None:
    result = {"method": __doc__.strip(), "entries": {}}
    for key, pdb_id, chains, what, note in ENTRIES:
        text = fetch_pdb(pdb_id)
        samples = []
        for chain in chains:
            for model in ca_by_model(text, chain):
                samples.append(descriptors(model))
        if not samples:
            raise SystemExit(f"{pdb_id}: no C-alpha atoms for chains {chains}")

        def agg(field: str) -> dict[str, float | None]:
            vals = [s[field] for s in samples]
            return {"mean": statistics.fmean(vals),
                    "sample_sd": statistics.stdev(vals) if len(vals) > 1 else None,
                    "min": min(vals), "max": max(vals)}

        result["entries"][key] = {
            "pdb_id": pdb_id, "chains": chains, "description": what, "note": note,
            "n_samples": len(samples), "n_ca_first": samples[0]["n_ca"],
            "rg_A": agg("rg_A"), "r_sphere_A": agg("r_sphere_A"), "r_max_A": agg("r_max_A"),
        }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
