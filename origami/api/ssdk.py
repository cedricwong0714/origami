"""Active learning over the SSDK library.

``POST /api/ssdk/learn`` scores repeat counts and recommends the next
surrogate measurement. Observations are caller numbers. None are invented.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from origami.ssdk.chassis import ChassisError, evaluate_chassis
from origami.ssdk.learn import SsdkLearnError, learn_ssdk

router = APIRouter()


@router.post("/api/ssdk/chassis")
async def post_ssdk_chassis(request: Request) -> dict[str, Any]:
    """Evaluate structure, stability, docking, and kinetics for one length."""
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    try:
        return evaluate_chassis(body)
    except ChassisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/ssdk/learn")
async def post_ssdk_learn(request: Request) -> dict[str, Any]:
    """Fit the residual model on surrogate rows and recommend a length."""
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    try:
        return learn_ssdk(body)
    except SsdkLearnError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
