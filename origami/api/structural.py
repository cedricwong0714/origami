"""Structural-analysis prediction API.

Scaffold geometry only. No payload spheres, clash, or C_eff.
``calibrated`` is always false.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from origami.linker_prior import ggggs_linker_rms_A
from origami.physical.backbone import (
    CONSTRUCT_N_TO_C,
    CONSTRUCT_N_VALUES,
    backbone_constructs,
    backbone_library,
)
from origami.physical.deposited import placed_ca_cloud, screw_steps
from origami.physical.geometry import build_ctpr
from origami.physical.structure import structural_report
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN

APP_TITLE = "ORIGAMI structural analysis"
APP_VERSION = "0.1.0"
STATIC_DIR = Path(__file__).resolve().parents[2] / "web" / "structural" / "out"

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "CTPR screw measurements for wiki figures and dry-lab work. "
        "This is not a crystal structure and not a wet-lab distance."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_n_list(raw: str | None) -> tuple[int, ...]:
    if raw is None or raw.strip() == "":
        return CONSTRUCT_N_VALUES
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if not parts:
        raise HTTPException(status_code=400, detail="n list is empty")
    values: list[int] = []
    for part in parts:
        try:
            n_repeats = int(part)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"n must be an integer, got {part!r}"
            ) from exc
        if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
            raise HTTPException(
                status_code=400,
                detail=f"n must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]",
            )
        if n_repeats in values:
            continue
        values.append(n_repeats)
    return tuple(values)


def _helix_trace(n_repeats: int) -> dict[str, Any]:
    geom = build_ctpr(n_repeats)
    cloud = placed_ca_cloud(n_repeats, geom.rise_A, geom.rotation_rad)
    stride = 2 if n_repeats <= 10 else 4
    ca = cloud[::stride]
    return {
        "n_repeats": int(n_repeats),
        "sites": [
            {
                "index": int(site.index),
                "x_A": float(site.xyz_A[0]),
                "y_A": float(site.xyz_A[1]),
                "z_A": float(site.xyz_A[2]),
            }
            for site in geom.sites
        ],
        "ca_stride": int(stride),
        "ca_A": [
            [round(float(p[0]), 3), round(float(p[1]), 3), round(float(p[2]), 3)]
            for p in ca
        ],
    }


def _reach_notes(construct: dict[str, Any], linker_rms_A: float) -> dict[str, Any]:
    """Compare C-end chords with the existing (GGGGS)3 RMS.

    Twice the RMS is a Gaussian-chain comparison, not a measured reach.
    """
    n_repeats = int(construct["n_repeats"])
    last = n_repeats - 1
    window = 2.0 * linker_rms_A
    near_n: list[int] = []
    near_c: list[int] = []
    for pair in construct["pairs"]:
        if pair["i"] == 0 and pair["chord_A"] <= window:
            near_n.append(int(pair["j"]))
        if pair["j"] == last and pair["chord_A"] <= window:
            near_c.append(int(pair["i"]))
    near_n = [0] + near_n
    near_c = near_c + [last]
    overlap = sorted(set(near_n) & set(near_c))
    end = construct["end_junction"]
    axial = float(construct["axial_span_A"])
    chord = float(end["chord_A"])
    bow = chord - axial
    bow_frac = bow / chord if chord > 0 else 0.0
    return {
        "linker_rms_A": float(linker_rms_A),
        "comparison_window_A": float(window),
        "comparison_window_definition": "2 * (GGGGS)3 Kratky-Porod RMS",
        "repeats_near_n_end": near_n,
        "repeats_near_c_end": near_c,
        "repeats_near_both_ends": overlap,
        "end_bow_A": float(bow),
        "end_bow_fraction_of_chord": float(bow_frac),
        "notes": [
            "Near-end lists use twice the (GGGGS)3 RMS as a comparison, not a wet-lab reach.",
            "SpyCatcher, flx, and LgBiT lengths are not in these chords.",
        ],
    }


def _reading(construct: dict[str, Any], reach: dict[str, Any]) -> list[str]:
    n_repeats = int(construct["n_repeats"])
    end = construct["end_junction"]
    phase = float(end["phase_deg"]) % 360.0
    face = float(end["facing_cosine"])
    lines = [
        (
            f"n = {n_repeats} is a rigid screw. Contour is "
            f"{construct['contour_nm']:.3f} nm, under the 15 nm project cutoff."
        ),
        (
            f"The end chord (repeat 0 to {n_repeats - 1}) is "
            f"{end['chord_A']:.2f} Å "
            f"(95% band {end['chord_95_low_A']:.1f}–{end['chord_95_high_A']:.1f} Å). "
            f"The helical bow is {reach['end_bow_A']:.2f} Å "
            f"({100 * reach['end_bow_fraction_of_chord']:.1f}% of the chord)."
        ),
        (
            f"Ends sit {phase:.1f}° apart on the cylinder "
            f"(facing cosine {face:.3f}). "
            "Δi = 8 would stack on the same face; that is not the last repeat of an 8-mer."
        ),
    ]
    if reach["repeats_near_both_ends"]:
        lines.append(
            "On this length, at least one repeat sits within the "
            "(GGGGS)3 comparison window of both ends."
        )
    else:
        lines.append(
            "On this length, no repeat sits within the (GGGGS)3 comparison "
            "window of both ends. One m13 graft cannot sit next to both stations "
            "on that tether comparison."
        )
    lines.append(
        "Passing this prediction is not scientific validation. calibrated stays false."
    )
    return lines


def predict_payload(n_values: tuple[int, ...]) -> dict[str, Any]:
    constructs = backbone_constructs(n_values)
    linker_rms = ggggs_linker_rms_A()
    library = backbone_library()
    library_by_n = {
        int(row["n_repeats"]): row
        for row in library["by_n"]
        if int(row["n_repeats"]) in n_values
    }
    scenes = []
    readings = []
    for row in constructs["constructs"]:
        reach = _reach_notes(row, linker_rms)
        scenes.append(_helix_trace(int(row["n_repeats"])))
        readings.append(
            {
                "n_repeats": int(row["n_repeats"]),
                "reach": reach,
                "reading": _reading(row, reach),
            }
        )
    return {
        "calibrated": False,
        "payloads": False,
        "tool": APP_TITLE,
        "version": APP_VERSION,
        "n_to_c": list(CONSTRUCT_N_TO_C),
        "measured_block": "CTPR",
        "constructs": constructs["constructs"],
        "screw": constructs["screw"],
        "deposited": library["deposited"],
        "deposited_steps": screw_steps(),
        "library_rows": [library_by_n[n] for n in n_values if n in library_by_n],
        "scenes": scenes,
        "readings": readings,
        "notes": list(constructs["notes"])
        + [
            "Wiki figures from this tool are computational screw measurements.",
            "Do not caption them as crystal structures of the fusion.",
        ],
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "calibrated": False, "tool": APP_TITLE}


@app.get("/api/sa/meta")
def meta() -> dict[str, Any]:
    return {
        "calibrated": False,
        "n_min": N_REPEATS_MIN,
        "n_max": N_REPEATS_MAX,
        "default_n": list(CONSTRUCT_N_VALUES),
        "n_to_c": list(CONSTRUCT_N_TO_C),
        "measured_block": "CTPR",
        "payloads": False,
    }


@app.get("/api/sa/predict")
def predict(
    n: str | None = Query(
        default=None,
        description="Comma-separated repeat counts, e.g. 3,8,14",
    ),
) -> dict[str, Any]:
    return predict_payload(_parse_n_list(n))


@app.get("/api/sa/library")
def library() -> dict[str, Any]:
    return backbone_library()


@app.get("/api/sa/scaffold/{n_repeats}")
def scaffold(n_repeats: int) -> dict[str, Any]:
    if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"n must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]",
        )
    geom = build_ctpr(n_repeats)
    report = structural_report(geom, list(range(n_repeats)))
    payload = predict_payload((n_repeats,))
    payload["structural_report"] = report.to_dict()
    payload["scene"] = _helix_trace(n_repeats)
    return payload


if STATIC_DIR.is_dir():
    app.mount("/assets-static", StaticFiles(directory=STATIC_DIR), name="sa-static")

    @app.get("/")
    def wiki_index() -> FileResponse:
        index = STATIC_DIR / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404, detail="frontend build missing")
        return FileResponse(index)
