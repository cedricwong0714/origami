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
