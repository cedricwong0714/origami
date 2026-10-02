"""Pass/fail rules, cost-weighted EI and the frozen prediction table.

Rule (approved): an output passes iff  mu - 1.96*sigma >= threshold.
Overall status is PASS only if every output passes. Thresholds, CVs and costs
come from data/config/active_learning_config.json and are placeholders until
their status is 'measured'. Frozen tables are never overwritten.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np

from origami.acquisition_core import expected_improvement_core

CONFIG_PATH = Path(__file__).resolve().parents[2] / "data/config/active_learning_config.json"
OUTPUTS = ("luminescence", "locking_fraction", "expression", "solubility", "purity")
THRESHOLDED = ("luminescence", "locking_fraction", "solubility", "purity")
Z95 = 1.96


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def unmeasured_items(cfg: dict[str, Any]) -> list[str]:
    """Names of thresholds/CVs/costs that are still placeholders."""
    out = [f"threshold:{k}" for k, v in cfg["thresholds"].items() if v["status"] != "measured"]
    out += [f"cv:{k}" for k, v in cfg["assay_cvs"].items() if v["status"] != "measured"]
    if cfg["costs"]["status"] != "measured":
        out.append("costs")
    return out


def passes(mu: float, sigma: float, threshold: float) -> bool:
    """Lower 95% bound must clear the threshold."""
    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    return bool(mu - Z95 * sigma >= threshold)


def evaluate_pass_fail(
    predictions: dict[str, tuple[float, float]], cfg: dict[str, Any]
) -> dict[str, Any]:
    """predictions: output -> (mu, sigma). Missing thresholded outputs -> FAIL."""
    res: dict[str, Any] = {}
    for name in THRESHOLDED:
        if name not in predictions:
            res[f"pass_{name}"] = False
            continue
        mu, sd = predictions[name]
        res[f"pass_{name}"] = passes(mu, sd, cfg["thresholds"][name]["value"])
    res["overall_status"] = "PASS" if all(res[f"pass_{n}"] for n in THRESHOLDED) else "FAIL"
    res["threshold_status"] = {
        n: cfg["thresholds"][n]["status"] for n in THRESHOLDED
    }
    return res


def cost_weighted_ei(
    mean: np.ndarray,
    std: np.ndarray,
    best: float,
    evaluation_type: str | list[str],
    cfg: dict[str, Any],
    xi: float = 0.0,
) -> np.ndarray:
    """alpha(x) = EI(x) / c(evaluation_type(x))."""
    costs = cfg["costs"]["values"]
    mean = np.atleast_1d(mean)
    types = [evaluation_type] * len(mean) if isinstance(evaluation_type, str) else evaluation_type
    c = np.array([costs[t] for t in types], dtype=float)
    if np.any(c <= 0):
        raise ValueError("costs must be positive")
    ei = np.atleast_1d(
        expected_improvement_core(mean, np.atleast_1d(std), best, xi=xi, std_floor=1e-12)
    )
    return ei / c


FROZEN_COLUMNS = (
    ["scaffold_id", "model_version", "geometry_group", "architecture_group",
     "application_group", "bo_round", "features_used", "fidelity_mix"]
    + [f"{p}_{o}" for o in OUTPUTS for p in ("mu", "sigma")]
    + [f"pass_{o}" for o in THRESHOLDED]
    + ["overall_status"]
    + [f"assay_CV_{o}" for o in OUTPUTS]
    + ["cost_dry", "cost_wet_partial", "cost_wet_full", "acquisition_score",
       "selected_fidelity_next", "placeholders_unmeasured", "notes"]
)


def build_frozen_row(
    scaffold_id: str,
    model_version: str,
    groups: dict[str, Any],
    features_used: str,
    fidelity_mix: str,
    predictions: dict[str, tuple[float, float]],
    cfg: dict[str, Any],
    acquisition_score: float,
    selected_fidelity_next: str,
    notes: str = "",
) -> dict[str, Any]:
    """One row with every schema column; unmeasured placeholders listed."""
    if selected_fidelity_next not in ("dry", "wet"):
        raise ValueError("selected_fidelity_next must be 'dry' or 'wet'")
    row: dict[str, Any] = {c: None for c in FROZEN_COLUMNS}
    row.update(
        scaffold_id=scaffold_id,
        model_version=model_version,
        geometry_group=groups.get("geometry_group"),
        architecture_group=groups.get("architecture_group"),
        application_group=groups.get("application_group"),
        bo_round=groups.get("bo_round"),
        features_used=features_used,
        fidelity_mix=fidelity_mix,
        acquisition_score=float(acquisition_score),
        selected_fidelity_next=selected_fidelity_next,
        notes=notes,
    )
    for o, (mu, sd) in predictions.items():
        row[f"mu_{o}"], row[f"sigma_{o}"] = float(mu), float(sd)
    row.update(evaluate_pass_fail(predictions, cfg))
    row.pop("threshold_status", None)
    for o in OUTPUTS:
        row[f"assay_CV_{o}"] = cfg["assay_cvs"][o]["value"]
    v = cfg["costs"]["values"]
    row["cost_dry"] = v["dry_docking"]
    row["cost_wet_partial"] = v["wet_NanoBiT"]
    row["cost_wet_full"] = v["wet_full_panel"]
    row["placeholders_unmeasured"] = unmeasured_items(cfg)
    if row["placeholders_unmeasured"]:
        warnings.warn(
            "Frozen row uses unmeasured placeholder thresholds/CVs/costs: "
            f"{row['placeholders_unmeasured']}. Not a wet-lab decision.",
            UserWarning,
            stacklevel=2,
        )
    return row


def write_frozen_table(rows: list[dict[str, Any]], path: Path) -> Path:
    """Write once. Refuses to overwrite: a frozen table never changes."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(
            f"{path} exists. Frozen tables are immutable; write a new model version."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, default=str))
    return path
