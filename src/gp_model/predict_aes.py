"""Placeholder AES (Assembly Efficiency Score) — uncalibrated, not validated."""

from __future__ import annotations

import hashlib
import math
import struct

_MODEL_NAME = "aes_placeholder_linear_hash"
_MODEL_VERSION = "placeholder-0"
_WARNING = (
    "UNCALIBRATED: AES is a deterministic placeholder combination of input "
    "features. It is not wet-lab calibrated and must not be used as a "
    "validated prediction."
)


def _stable_feature_weight(name: str) -> float:
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    # Map 8 bytes to [0, 1) then to a small weight; no biological meaning.
    raw = struct.unpack(">Q", digest[:8])[0]
    return (raw / float(2**64)) * 0.1


def predict_aes(features: dict[str, float]) -> dict:
    """Return an uncalibrated AES placeholder from numeric features.

    Score is a clipped linear combination of feature values with
    hash-derived weights (deterministic, not a scientific model).

    Always ``confidence_tier='hypothesis_only'``. ``is_extrapolation`` is True
    because this module has no in-domain calibration set; even if a separate
    OOD check later reports in-domain features, this remains hypothesis-only.
    """
    names = sorted(features.keys())
    raw = 0.0
    for name in names:
        value = float(features[name])
        raw += _stable_feature_weight(name) * value

    # Map unbounded linear sum to (0, 1) without claiming a physical unit scale.
    predicted = 1.0 / (1.0 + math.exp(-raw))
    # Wide interval: placeholder uncertainty, not a statistical CI.
    half_width = 0.25
    lower = max(0.0, predicted - half_width)
    upper = min(1.0, predicted + half_width)

    return {
        "predicted_value": predicted,
        "units": "AES",
        "uncertainty_95_lower": lower,
        "uncertainty_95_upper": upper,
        "confidence_tier": "hypothesis_only",
        "is_extrapolation": True,
        "model_name": _MODEL_NAME,
        "model_version": _MODEL_VERSION,
        "parameter_sources": [],
        "assumptions": [
            "Deterministic hash-weighted linear combination of caller-supplied features.",
            "No experimental calibration dataset is used.",
        ],
        "warnings": [_WARNING],
        "human_review_required": True,
        "most_sensitive_parameter": names[0] if names else None,
    }
