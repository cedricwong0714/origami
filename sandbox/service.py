"""Run one ORIGAMI design from sandbox form values.

This module does not score biology itself. It validates the form, calls
``origami.engine.run_design``, and returns that report plus a process
log of the steps ``run_design`` already performs.
"""

from __future__ import annotations

from typing import Any

from origami.engine import Observation, run_design
from origami.io.payloads import PayloadRecord, load_payloads
from origami.physical.erickson_size import payload_size_note
from origami.priors import (
    DEFAULT_PAYLOAD_RADIUS_A,
    LINKER_SIGMA_A,
    N_REPEATS_MAX,
    N_REPEATS_MIN,
)
from origami.stability.series import (
    DEFAULT_OPERATING_TEMPERATURE_C,
    PHILLIPS_2012_CTPRA_DSC,
)

PROCESS_STEPS = (
    "build_ctpr: canonical deposited screw (rise mean, 45° twist)",
    "structural_report: pitch, phase, deposited comparison",
    "steric_report: payload spheres vs placed C-alpha envelope",
    "pair C_eff: worm-like-chain width from the (GGGGS)3 prior or caller sigmas",
    "occupancy: default CaM-M13 Kd unless a signal pair is supplied",
    "ClaspDesignEngine.run: physics library 3–24, residual GP, thermal gate",
    "separation_library: Δi scan on this scaffold with a new unfitted GP",
    "assemble_report: calibrated stays false",
)

_ALLOWED_OBS_SOURCES = frozenset({"user_entered", "wet_lab"})


def run_sandbox(request: dict[str, Any]) -> dict[str, Any]:
    """Validate a sandbox request and return process plus design data.

    Required keys: ``design_id`` (non-empty string), ``n_repeats`` (int).
    Optional: ``payloads``, ``thermal_prior``, ``t_assay_C``, ``observations``.
    Damköhler rates are not accepted here; they stay omitted.
    """
    if not isinstance(request, dict):
        raise TypeError("sandbox request must be a dict")
    design_id = request.get("design_id")
    if not isinstance(design_id, str) or design_id.strip() == "":
        raise ValueError("design_id must be a non-empty string")
    n_repeats = request.get("n_repeats")
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise ValueError("n_repeats must be an integer")
    if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
        raise ValueError(
            f"n_repeats must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]"
        )

    payloads = _payloads(request.get("payloads"), n_repeats)
    thermal_prior = request.get("thermal_prior", True)
    if type(thermal_prior) is not bool:
        raise TypeError("thermal_prior must be a bool")
    t_assay = request.get("t_assay_C")
    if t_assay is not None:
        if isinstance(t_assay, bool) or not isinstance(t_assay, (int, float)):
            raise TypeError("t_assay_C must be a number")
        t_assay = float(t_assay)
    observations = _observations(request.get("observations"))

    notes: list[str] = [
        "This sandbox calls run_design. It does not invent sequences or citations.",
        "calibrated stays false until a wet-lab claim is attached in code.",
        "next_n and next_delta_i are acquisition outputs, not team optima.",
    ]
    if payloads is None:
        notes.append(
            "No payloads were supplied. run_design places the default "
            f"{DEFAULT_PAYLOAD_RADIUS_A.value} Å heuristic radius on each end "
            "repeat. That radius is not a measured OtsA/OtsB size."
        )
        notes.append(
            f"Default linker width is {LINKER_SIGMA_A.value:.6f} Å "
            "(GGGGS)3 Kratky-Porod RMS."
        )

    size_notes = []
    if payloads is not None:
        for record in payloads:
            if record.mw_Da is None:
                continue
            size_notes.append(
                {
                    "payload_id": record.payload_id,
                    "mw_source": record.mw_source,
                    "sequence_checksum": record.sequence_checksum,
                    "residue_count": (
                        None
                        if record.protein_sequence is None
                        else len(record.protein_sequence)
                    ),
                    **payload_size_note(record.mw_Da, record.radius_A),
                }
            )

    report = run_design(
        design_id.strip(),
        n_repeats,
        payloads=payloads,
        observations=observations,
        thermal_prior=thermal_prior,
        t_assay_C=t_assay,
    )
    payload = report.to_dict()
    library_n = list(range(N_REPEATS_MIN, N_REPEATS_MAX + 1))
    if len(payload["gp_mean"]) != len(library_n):
        raise RuntimeError("posterior length does not match the n library")
    return {
        "input": {
            "design_id": design_id.strip(),
            "n_repeats": n_repeats,
            "payload_count": 0 if payloads is None else len(payloads),
            "thermal_prior": thermal_prior,
            "t_assay_C": (
                None
                if not thermal_prior
                else (
                    t_assay
                    if t_assay is not None
                    else DEFAULT_OPERATING_TEMPERATURE_C
                )
            ),
            "thermal_series": (
                PHILLIPS_2012_CTPRA_DSC if thermal_prior else None
            ),
            "observation_count": 0 if observations is None else len(observations),
            "observation_sources": (
                []
                if observations is None
                else sorted({obs.source for obs in observations})
            ),
        },
        "process": {
            "steps": list(PROCESS_STEPS),
            "notes": notes,
        },
        "result": payload,
        "payload_size": size_notes,
        "library": {
            "n_repeats": library_n,
            "gp_mean": payload["gp_mean"],
            "gp_std": payload["gp_std"],
        },
    }


def _payloads(
    rows: object,
    n_repeats: int,
) -> list[PayloadRecord] | None:
    if rows is None:
        return None
    if not isinstance(rows, list):
        raise TypeError("payloads must be a list or omitted")
    if len(rows) == 0:
        return None
    records = load_payloads(rows)
    for record in records:
        if record.repeat_index < 0 or record.repeat_index >= n_repeats:
            raise ValueError(
                f"payload {record.payload_id} repeat_index is outside the scaffold"
            )
    return records


def _observations(rows: object) -> list[Observation] | None:
    if rows is None:
        return None
    if not isinstance(rows, list):
        raise TypeError("observations must be a list or omitted")
    if len(rows) == 0:
        return None
    out: list[Observation] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f"observations[{index}] must be a dict")
        n_repeats = row.get("n_repeats")
        y = row.get("y")
        source = row.get("source", "user_entered")
        if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
            raise ValueError(f"observations[{index}].n_repeats must be an integer")
        if isinstance(y, bool) or not isinstance(y, (int, float)):
            raise ValueError(f"observations[{index}].y must be a number")
        if source not in _ALLOWED_OBS_SOURCES:
            raise ValueError(
                "observation source must be user_entered or wet_lab"
            )
        if source == "wet_lab":
            notes = "Caller labeled this wet_lab. The sandbox does not verify the assay."
        else:
            notes = "Sandbox form entry. Not a wet-lab record."
        out.append(
            Observation(
                n_repeats=n_repeats,
                y=float(y),
                source=source,
                notes=notes,
            )
        )
    return out
