"""Export endpoints: SBOL, GenBank, SBML, passport, batch, PDB, benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from origami.export.batch import batch_chassis_csv
from origami.export.benchmark import run_benchmark
from origami.export.constructs import ConstructError
from origami.export.genbank import genbank_for_n
from origami.export.passport import chassis_passport
from origami.export.pdb_plugin import PdbPluginError, describe_pdb
from origami.export.profiles import ProfileError, validate_profile
from origami.export.report import freeze_report_markdown
from origami.export.sbol import sbol_for_n
from origami.export.sbml import sbml_from_kinetics_body
from origami.export.synthetic import synthetic_learn_rows
from origami.kinetics.simulate import KineticsSimError
from origami.literature.fetch import LiteratureFetchError, fetch_and_store, search_crossref
from origami.lab.freeze_compare import FreezeCompareError, compare_plate_csv
from origami.ssdk.chassis import ChassisError

router = APIRouter()
_TOOLTIPS = Path(__file__).resolve().parents[2] / "docs" / "tooltips.json"


@router.get("/api/export/tooltips")
def get_tooltips() -> dict[str, Any]:
    import json

    return {"calibrated": False, "tooltips": json.loads(_TOOLTIPS.read_text(encoding="utf-8"))}


@router.get("/api/export/genbank/{n_repeats}", response_class=PlainTextResponse)
def get_genbank(n_repeats: int) -> str:
    try:
        return genbank_for_n(n_repeats)
    except ConstructError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/export/sbol/{n_repeats}", response_class=PlainTextResponse)
def get_sbol(n_repeats: int) -> str:
    try:
        return sbol_for_n(n_repeats)
    except ConstructError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/export/sbml", response_class=PlainTextResponse)
async def post_sbml(request: Request) -> str:
    try:
        body = await request.json()
        return sbml_from_kinetics_body(body)
    except (KineticsSimError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/export/passport")
async def post_passport(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
        return chassis_passport(body)
    except ChassisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/export/batch")
async def post_batch(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
        return batch_chassis_csv(str(body.get("csv_text", "")), body.get("extra"))
    except ChassisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/export/pdb")
async def post_pdb(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
        return describe_pdb(str(body.get("pdb_text", "")), body.get("chain"))
    except PdbPluginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/export/profile")
async def post_profile(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
        return validate_profile(body)
    except ProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/export/benchmark")
def get_benchmark() -> dict[str, Any]:
    return run_benchmark()


@router.post("/api/export/synthetic")
async def post_synthetic(request: Request) -> dict[str, Any]:
    body = await request.json()
    n_values = body.get("n_values", [3, 8, 14])
    return synthetic_learn_rows(
        [int(n) for n in n_values],
        seed=int(body.get("seed", 0)),
        noise_sd=float(body.get("noise_sd", 0.05)),
    )


@router.post("/api/export/plate-report", response_class=PlainTextResponse)
async def post_plate_report(request: Request) -> str:
    try:
        body = await request.json()
        report = compare_plate_csv(str(body["csv_text"]), source=str(body.get("source", "plate.csv")))
        return freeze_report_markdown(report)
    except (FreezeCompareError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/literature/doi")
async def post_literature_doi(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
        return fetch_and_store(str(body["doi"]))
    except (LiteratureFetchError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/literature/search")
async def post_literature_search(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
        hits = search_crossref(str(body["query"]), rows=int(body.get("rows", 5)))
    except (LiteratureFetchError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "calibrated": False,
        "usable_as_prior": False,
        "hits": hits,
        "note": "Search hits are not installed as rates or Kd values.",
    }
