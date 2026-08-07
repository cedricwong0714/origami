"""Resolve repo-relative paths for models/, data/, and golden references."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "models"
DATA_DIR = REPO_ROOT / "data"
GOLDEN_DIR = REPO_ROOT / "tests" / "golden_references"
KINETIC_MODELS_DIR = MODELS_DIR / "kinetic_models"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=16)
def load_kinetic_defaults(mechanism_type: str) -> dict[str, Any]:
    """
    Load tracked kinetic priors for a mechanism_type string
    (e.g. 'intermediate_transfer').
    """
    path = KINETIC_MODELS_DIR / f"{mechanism_type}.defaults.json"
    if not path.is_file():
        raise FileNotFoundError(f"No kinetic defaults at {path}")
    return load_json(path)


def kinetic_params(mechanism_type: str) -> dict[str, float]:
    payload = load_kinetic_defaults(mechanism_type)
    return {k: float(v) for k, v in payload.get("params", {}).items()}
