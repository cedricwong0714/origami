"""Four-tube bridging ratios for the streptavidin luminescence assay.

The protocol reads four tubes:

- tube 1, no target (background)
- tube 2, bridging streptavidin
- tube 3, streptavidin pre-blocked with free biotin
- tube 4, streptavidin at the hook-effect concentration

The reported numbers are tube2/tube1, tube3/tube2, and tube4/tube2.
A first-order sigma is attached only when both replicate sigmas were
supplied. The sign pattern the protocol is built to show is tube 2
above tube 1, tube 3 below tube 2, and tube 4 below tube 2. There is
no fold-change cutoff.

Streptavidin concentrations are the caller's setpoints. They are not a
fitted dissociation constant. Payload radii are not computed.

``calibrated`` stays false.
"""

from __future__ import annotations

from typing import Any

from origami.assay.uncertainty import Z95, finite_number, optional_sigma, quotient
from origami.assay.window import _result

# Protocol setpoints from the team's Phase 4 bridging assay. They are
# experimental design choices, not a measured streptavidin Kd.
PROTOCOL_BRIDGE_M = 50e-9
PROTOCOL_HOOK_M = 1e-6
MODEL_NAME = "bridging_ratios"
MODEL_VERSION = "1"


def _bridge_result(**kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("model_name", MODEL_NAME)
    kwargs.setdefault("model_version", MODEL_VERSION)
    return _result(**kwargs)


def bridging_ratios(body: dict[str, Any]) -> dict[str, Any]:
    """Compute the three ratios from the four tube RLU values."""
    if not isinstance(body, dict):
        return _bridge_result(
            computable=False, missing=["bridging body must be an object"], warnings=[]
        )
    required = ("tube1_rlu", "tube2_rlu", "tube3_rlu", "tube4_rlu")
    missing = [name for name in required if body.get(name) is None]
    if missing:
        return _bridge_result(
            computable=False,
            missing=[f"missing {name}" for name in missing],
            warnings=[],
        )
    try:
        tubes = {name: finite_number(name, body[name]) for name in required}
        sigmas = {
            name: optional_sigma(f"{name}_sigma", body.get(f"{name}_sigma"))
            for name in required
        }
        bridge_M = _setpoint(
            "streptavidin_bridge_M",
            body.get("streptavidin_bridge_M"),
            PROTOCOL_BRIDGE_M,
        )
        hook_M = _setpoint(
            "streptavidin_hook_M", body.get("streptavidin_hook_M"), PROTOCOL_HOOK_M
        )
    except ValueError as exc:
        return _bridge_result(computable=False, missing=[str(exc)], warnings=[])
    if tubes["tube1_rlu"] == 0.0 or tubes["tube2_rlu"] == 0.0:
        return _bridge_result(
            computable=False,
            missing=["tube 1 and tube 2 RLU must be non-zero"],
            warnings=[],
        )
    if bridge_M <= 0 or hook_M <= 0:
        return _bridge_result(
            computable=False,
            missing=["streptavidin concentrations must be > 0"],
            warnings=[],
        )

    signal, signal_sigma = quotient(
        tubes["tube2_rlu"], tubes["tube1_rlu"], sigmas["tube2_rlu"], sigmas["tube1_rlu"]
    )
    competition, competition_sigma = quotient(
        tubes["tube3_rlu"], tubes["tube2_rlu"], sigmas["tube3_rlu"], sigmas["tube2_rlu"]
    )
    hook, hook_sigma = quotient(
        tubes["tube4_rlu"], tubes["tube2_rlu"], sigmas["tube4_rlu"], sigmas["tube2_rlu"]
    )
    pattern = (
        tubes["tube2_rlu"] > tubes["tube1_rlu"]
        and tubes["tube3_rlu"] < tubes["tube2_rlu"]
        and tubes["tube4_rlu"] < tubes["tube2_rlu"]
    )
    return _bridge_result(
        computable=True,
        missing=[],
        warnings=[
            "These ratios are the four-tube readout. They are not a docking radius and not an enzyme flux.",
            "There is no fold-change cutoff.",
        ],
        signal_over_background=_ratio(signal, signal_sigma),
        competition_over_bridge=_ratio(competition, competition_sigma),
        hook_over_bridge=_ratio(hook, hook_sigma),
        pattern_holds=pattern,
        pattern_definition="tube2 > tube1 and tube3 < tube2 and tube4 < tube2",
        streptavidin_bridge_M=bridge_M,
        streptavidin_hook_M=hook_M,
        streptavidin_concentrations_are_setpoints=True,
    )


def _setpoint(name: str, value: object, default: float) -> float:
    if value is None:
        return default
    return finite_number(name, value)


def _ratio(value: float, sigma: float | None) -> dict[str, float | None]:
    low = None if sigma is None else value - Z95 * sigma
    high = None if sigma is None else value + Z95 * sigma
    return {
        "value": value,
        "sigma": sigma,
        "interval_95_lower": low,
        "interval_95_upper": high,
    }
