"""HTTP surface for the lab chassis.

``GET /api/lab/schema`` lists empty measurement slots.
``POST /api/lab/run`` evaluates only the sections present in the body.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from origami.lab.run import LabRunError, run_lab
from origami.lab.schema import lab_schema

router = APIRouter()


@router.get("/api/lab/schema")
def get_lab_schema() -> dict[str, Any]:
    """Vacant slots for the experiments this team is running."""
    return lab_schema()


@router.post("/api/lab/run")
async def post_lab_run(request: Request) -> dict[str, Any]:
    """Run prep, assay window, calcium, lock, and bridging."""
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    try:
        return run_lab(body)
    except LabRunError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/lab/plate")
async def post_lab_plate(request: Request) -> dict[str, Any]:
    """Blank-correct plate-reader CSV text into observation rows.

    Body: ``{"csv_text": "...", "source": "plate1.csv"}``. Nothing is stored.
    """
    from origami.lab.plate_reader import PlateReaderError, parse_plate_csv

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict) or not isinstance(body.get("csv_text"), str):
        raise HTTPException(status_code=400, detail="csv_text (string) is required")
    source = body.get("source")
    if not isinstance(source, str) or not source.strip():
        source = "uploaded.csv"
    import hashlib

    digest = hashlib.sha256(body["csv_text"].encode("utf-8")).hexdigest()
    try:
        return parse_plate_csv(body["csv_text"], source=source.strip(), sha256=digest)
    except PlateReaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/lab/plate-vs-frozen")
async def post_plate_vs_frozen(request: Request) -> dict[str, Any]:
    """Score plate CSV text against scaffold-n3, scaffold-n8, and scaffold-n14.

    Body: ``{"csv_text": "...", "source": "plate1.csv"}``. A row is compared
    only when ``calcium_uM`` matches a frozen luminescence key. Nothing is stored.
    """
    import hashlib

    from origami.lab.freeze_compare import FreezeCompareError, compare_plate_csv
    from origami.lab.plate_reader import PlateReaderError

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict) or not isinstance(body.get("csv_text"), str):
        raise HTTPException(status_code=400, detail="csv_text (string) is required")
    source = body.get("source")
    if not isinstance(source, str) or not source.strip():
        source = "uploaded.csv"
    digest = hashlib.sha256(body["csv_text"].encode("utf-8")).hexdigest()
    try:
        return compare_plate_csv(body["csv_text"], source=source.strip(), sha256=digest)
    except (PlateReaderError, FreezeCompareError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/lab/ablation")
async def post_lab_ablation(request: Request) -> dict[str, Any]:
    """Grouped leave-one-group-out ablation of physics, GP and XGBoost."""
    import numpy as np

    from src.gp_model.ablation import grouped_ablation

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    try:
        return grouped_ablation(
            np.asarray(body["X"], dtype=float),
            np.asarray(body["y_obs"], dtype=float),
            np.asarray(body["y_mech"], dtype=float),
            list(body["groups"]),
            body.get("feature_names"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid ablation input: {exc!r}") from exc
