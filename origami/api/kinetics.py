"""HTTP surfaces for stage-1 scaffold kinetics."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from origami.kinetics.scaffold_sweep import scaffold_kinetic_sweep
from origami.kinetics.schema import kinetics_schema
from origami.kinetics.simulate import KineticsSimError, simulate_kinetics

router = APIRouter()


@router.get("/api/kinetics/schema")
def get_kinetics_schema() -> dict[str, Any]:
    """Vacant vs literature rate slots and supported simulate modes."""
    return kinetics_schema()


@router.get("/api/kinetics/scaffold")
def get_scaffold_kinetics() -> dict[str, Any]:
    """Occupancy and tethered half-life at every CTPR length."""
    return scaffold_kinetic_sweep()


@router.post("/api/kinetics/simulate")
async def post_kinetics_simulate(request: Request) -> dict[str, Any]:
    """Run recruitment steady state or a covalent time course.

    Default covalent uses the Zakeri 2012 literature k_on (lumped path).
    Clearing that prior without a lab rate returns HTTP 400.
    """
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    try:
        return simulate_kinetics(body)
    except KineticsSimError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
