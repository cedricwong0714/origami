"""Payload size scales derived from deposited C-alpha coordinates.

Values come from ``data/structures/payload_radii.json``, written by
``scripts/derive_payload_radii.py`` from RCSB PDB files. The clash radius is
the radius of a uniform solid sphere with the same C-alpha radius of
gyration, sqrt(5/3) * Rg. It ignores side chains and is inflated by flexible
termini. It is not a hydrodynamic radius. ``sd_between_copies`` is the spread
between chains or models in one entry and understates real uncertainty.
``calibrated`` is always false.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from origami.priors import erickson_rmin_A

_DATA = Path(__file__).resolve().parents[2] / "data" / "structures" / "payload_radii.json"

# Parameter: E. coli OtsB mass
# Value: 29175 Da (UniProt P31678, 266 aa, retrieved via rest.uniprot.org)
# Notes: No PDB entry exists for E. coli OtsB (RCSB search on P31678 returned none).
#        PDB 1U02 is the Thermoplasma acidophilum enzyme and must not be used for it.
OTSB_ECOLI_MW_DA = 29175.0
# Parameter: E. coli OtsA mass from sequence, UniProt P31677, 474 aa
OTSA_ECOLI_SEQUENCE_MW_DA = 53611.0


class PayloadRadiusError(KeyError):
    """The payload has no structure-derived radius."""


@dataclass(frozen=True)
class PayloadRadius:
    key: str
    pdb_id: str
    chains: tuple[str, ...]
    description: str
    note: str
    n_samples: int
    n_ca: int
    clash_radius_A: float
    sd_between_copies_A: float | None
    r_max_A: float
    rg_A: float
    calibrated: bool = False
    is_proxy: bool = False


def _load() -> dict[str, Any]:
    return json.loads(_DATA.read_text())["entries"]


def available_payloads() -> list[str]:
    return sorted(_load())


def payload_radius(key: str) -> PayloadRadius:
    entries = _load()
    if key not in entries:
        raise PayloadRadiusError(
            f"no structure-derived radius for {key!r}; available: {sorted(entries)}"
        )
    e = entries[key]
    return PayloadRadius(
        key=key, pdb_id=e["pdb_id"], chains=tuple(e["chains"]),
        description=e["description"], note=e["note"], n_samples=e["n_samples"],
        n_ca=e["n_ca_first"], clash_radius_A=float(e["r_sphere_A"]["mean"]),
        sd_between_copies_A=e["r_sphere_A"]["sample_sd"],
        r_max_A=float(e["r_max_A"]["mean"]), rg_A=float(e["rg_A"]["mean"]),
        is_proxy="proxy" in key or "PROXY" in e["note"],
    )


def radii_for(names: list[str]) -> list[float]:
    """Clash radii in angstroms for two named payloads."""
    if len(names) != 2:
        raise ValueError("exactly two payload names are required")
    return [payload_radius(n).clash_radius_A for n in names]


def otsb_lower_bound_A() -> dict[str, Any]:
    """OtsB has no structure on file. Return only the Erickson lower bound."""
    value = erickson_rmin_A(OTSB_ECOLI_MW_DA)
    if not math.isfinite(value):
        raise ValueError("non-finite lower bound")
    return {
        "key": "otsb_ecoli", "r_min_lower_bound_A": value, "usable_as_clash_radius": False,
        "calibrated": False,
        "note": "Lower bound from mass (UniProt P31678). No PDB entry for E. coli OtsB; "
        "supply a radius or leave it unset.",
    }
