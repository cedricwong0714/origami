"""HTTP surface for docking geometry and the affinity check.

The affinity route compares a caller Kd or Ka with the local effective
concentration. It does not invent a dissociation constant.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from origami.docking.affinity import AffinityError, docking_geometry, evaluate_affinity

router = APIRouter()


@router.post("/api/docking/affinity")
async def post_docking_affinity(request: Request) -> dict[str, Any]:
    """Kd or Ka versus local concentration, then LgBiT–SmBiT and Spy."""
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    try:
        return evaluate_affinity(
            _integer(body.get("n_repeats"), "n_repeats"),
            affinity=str(body.get("affinity", "")),
            value=_number(body.get("value"), "value"),
            unit=str(body.get("unit", "")),
            indices=_indices(body.get("indices")),
            radii_A=_radii(body.get("radii_A")),
        )
    except AffinityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/docking/geometry")
def get_docking_geometry(
    n: int = Query(..., ge=3, le=24, description="Repeat count."),
) -> dict[str, Any]:
    """Chord, clash, and effective concentration at one length."""
    try:
        return docking_geometry(n)
    except AffinityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AffinityError(f"{name} must be an integer")
    return value


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AffinityError(f"{name} must be a number")
    return float(value)


def _indices(value: object) -> list[int] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise AffinityError("indices must be two integers or omitted")
    parsed: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise AffinityError("each index must be an integer")
        parsed.append(item)
    return parsed


def _radii(value: object) -> list[float] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise AffinityError("radii_A must be two numbers or omitted")
    return [_number(value[0], "radii_A[0]"), _number(value[1], "radii_A[1]")]
