"""Spoonfed design report.

This module packages numbers the caller already computed. It does not
evaluate CTPR geometry, steric clash, linker effective concentration,
recruitment occupancy, Damköhler capture, or the residual Gaussian process.

There is intentionally no theta(t) field. A steady-state occupancy can be
recorded without a time course. A missing time course is the absence of a
series, not a synthetic one.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import InitVar, dataclass, field
from typing import Any

import numpy as np

from origami.physical.registers import (
    REGISTER_KEYS,
    TEAM_BIOMARKER_N,
    TEAM_CHANNELING_N,
    TEAM_LOWER_N,
    TEAM_UPPER_N,
)
from origami.physical.structure import PAIR_STRUCTURE_KEYS, STRUCTURE_KEYS

_WET_LAB = "wet_lab"

# Gate states from origami.stability.gate.thermal_gate. The tier is the
# evidence class of that state, not a second temperature model.
_STABILITY_STATES = ("pass", "fail", "extrapolated", "omitted")
_STABILITY_TIERS = ("omitted", "literature_prior", "extrapolated")
_TIER_FOR_STATE = {
    "omitted": "omitted",
    "extrapolated": "extrapolated",
    "pass": "literature_prior",
    "fail": "literature_prior",
}

_CALIBRATED_REFUSAL = (
    "calibrated=True requires evidence_source='wet_lab'. "
    "The default evidence_source is 'none', so calibrated must remain False. "
    "This assembler does not treat literature placeholders as wet-lab data."
)


class _WetLabClaim:
    """Sentinel passed only when assemble_report saw evidence_source='wet_lab'."""


_WET_LAB_CLAIM = _WetLabClaim()


def _reject_bool(name: str, value: object) -> None:
    if type(value) is bool or isinstance(value, np.bool_):
        raise TypeError(f"{name} must be a real number, not a bool")


def _as_float(name: str, value: object) -> float:
    """Coerce a caller-supplied scalar to a builtin float.

    Numpy scalars are accepted and converted so to_dict() can be serialized
    with the standard library json module. Arrays are not scalars.
    """
    _reject_bool(name, value)
    if isinstance(value, np.ndarray):
        raise TypeError(f"{name} must be a scalar, not an array")
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
    else:
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _as_int(name: str, value: object) -> int:
    _reject_bool(name, value)
    if isinstance(value, np.ndarray):
        raise TypeError(f"{name} must be an int, not an array")
    if isinstance(value, (int, np.integer)):
        return int(value)
    raise TypeError(f"{name} must be an int")


def _identifier(name: str, value: object) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _string_list(name: str, value: object) -> list[str]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a list of strings")
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise TypeError(f"{name}[{index}] must be a string")
        items.append(item)
    return items


def _float_list(name: str, value: object, *, minimum: float | None = None) -> list[float]:
    if (
        isinstance(value, (str, bytes, Mapping))
        or not isinstance(value, Sequence)
    ):
        raise TypeError(f"{name} must be a sequence of numbers")
    numbers: list[float] = []
    for index, item in enumerate(value):
        number = _as_float(f"{name}[{index}]", item)
        if minimum is not None and number < minimum:
            raise ValueError(f"{name}[{index}] must be >= {minimum}")
        numbers.append(number)
    return numbers


def _float_map(
    name: str,
    value: object,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> dict[str, float]:
    """Copy a string-keyed map onto builtin floats.

    Keys stay strings because JSON objects cannot use tuple keys. This
    function does not rename pairs or fill missing pairs.
    """
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping of string keys to numbers")
    copied: dict[str, float] = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{name} keys must be strings")
        number = _as_float(f"{name}[{key!r}]", raw)
        if minimum is not None and number < minimum:
            raise ValueError(f"{name}[{key!r}] must be >= {minimum}")
        if maximum is not None and number > maximum:
            raise ValueError(f"{name}[{key!r}] must be <= {maximum}")
        copied[key] = number
    return copied


def _optional_float(name: str, value: object) -> float | None:
    if value is None:
        return None
    return _as_float(name, value)


def _unit_interval(name: str, value: object) -> float | None:
    if value is None:
        return None
    number = _as_float(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError(f"{name}={number} is outside [0, 1]")
    return number


@dataclass
class DesignReport:
    """Recorded design summary.

    Every numeric field is a value the caller already computed. Nothing
    here is a new physical prediction.

    Units, as supplied by the caller:
    - pair_distances_A: angstrom
    - p_clash: probability
    - c_eff_M: molar
    - theta_*: site-occupancy fraction
    - da: dimensionless Damköhler number
    - p_capture: probability
    - gp_mean, gp_std: posterior mean and standard deviation in the caller's units
    - next_n: recommended repeat count
    - tm_C, tm_interval_low, tm_interval_high: degrees Celsius, as returned
      by the thermal gate. This assembler does not estimate a melting temperature.
    - stability_state: pass, fail, extrapolated, or omitted
    - stability_tier: omitted, literature_prior, or extrapolated
    - stability_omitted: names of thermal inputs that were not used
    - delta_g*: unfolding free energy already looked up for this design's n
    - highest_cited_delta_g_*: the feasible length with the largest printed
      unfolding ΔG in that same column. Not a second recommendation.
    - structure: screw invariants from origami.physical.structure, or None
      when that report was not computed. calibrated inside it stays false.
    - registers: team lengths 2, 3, 14, and 20 checked against this scan.
      They stay labeled as team choices. calibrated inside it stays false.
    """

    design_id: str
    prior_geometry_id: str
    prior_kd_id: str
    n_repeats: int
    pair_distances_A: dict[str, float]
    p_clash: dict[str, float]
    c_eff_M: dict[str, float]
    theta_ss: float | None
    theta_95_lower: float | None
    theta_95_upper: float | None
    da: float | None
    p_capture: float | None
    gp_mean: list[float]
    gp_std: list[float]
    next_n: int | None
    calibrated: bool
    warnings: list[str]
    omitted: list[str]
    tm_C: float | None = None
    tm_interval_low: float | None = None
    tm_interval_high: float | None = None
    stability_state: str = "omitted"
    stability_tier: str = "omitted"
    stability_omitted: list[str] = field(default_factory=list)
    delta_g: float | None = None
    delta_g_units: str | None = None
    delta_g_uncertainty: float | None = None
    highest_cited_delta_g_n: int | None = None
    highest_cited_delta_g: float | None = None
    highest_cited_delta_g_units: str | None = None
    highest_cited_delta_g_uncertainty: float | None = None
    structure: dict[str, Any] | None = None
    registers: dict[str, Any] | None = None
    calibration_claim: InitVar[object | None] = None

    def __post_init__(self, calibration_claim: object | None) -> None:
        if type(self.calibrated) is not bool:
            raise TypeError("calibrated must be a bool")
        if self.calibrated and calibration_claim is not _WET_LAB_CLAIM:
            raise ValueError(_CALIBRATED_REFUSAL)

        self.design_id = _identifier("design_id", self.design_id)
        self.prior_geometry_id = _identifier("prior_geometry_id", self.prior_geometry_id)
        self.prior_kd_id = _identifier("prior_kd_id", self.prior_kd_id)

        n_repeats = _as_int("n_repeats", self.n_repeats)
        if n_repeats < 1:
            raise ValueError("n_repeats must be >= 1")
        self.n_repeats = n_repeats

        self.pair_distances_A = _float_map("pair_distances_A", self.pair_distances_A, minimum=0.0)
        self.p_clash = _float_map("p_clash", self.p_clash, minimum=0.0, maximum=1.0)
        self.c_eff_M = _float_map("c_eff_M", self.c_eff_M, minimum=0.0)

        self.theta_ss = _unit_interval("theta_ss", self.theta_ss)
        self.theta_95_lower = _unit_interval("theta_95_lower", self.theta_95_lower)
        self.theta_95_upper = _unit_interval("theta_95_upper", self.theta_95_upper)
        _check_theta_interval(self.theta_ss, self.theta_95_lower, self.theta_95_upper)

        self.da = _optional_float("da", self.da)
        if self.da is not None and self.da < 0.0:
            raise ValueError("da cannot be negative")
        self.p_capture = _unit_interval("p_capture", self.p_capture)

        self.warnings = _string_list("warnings", self.warnings)
        self.omitted = _string_list("omitted", self.omitted)
        _check_capture_omission(self.da, self.p_capture, self.omitted)

        self.tm_C = _optional_float("tm_C", self.tm_C)
        self.tm_interval_low = _optional_float("tm_interval_low", self.tm_interval_low)
        self.tm_interval_high = _optional_float("tm_interval_high", self.tm_interval_high)
        self.stability_state = _stability_label(
            "stability_state", self.stability_state, _STABILITY_STATES
        )
        self.stability_tier = _stability_label(
            "stability_tier", self.stability_tier, _STABILITY_TIERS
        )
        self.stability_omitted = _string_list("stability_omitted", self.stability_omitted)
        self.delta_g = _optional_float("delta_g", self.delta_g)
        self.delta_g_uncertainty = _optional_float(
            "delta_g_uncertainty", self.delta_g_uncertainty
        )
        if self.delta_g is None:
            if self.delta_g_units not in (None, ""):
                raise ValueError("delta_g_units must be empty when delta_g is None")
            if self.delta_g_uncertainty is not None:
                raise ValueError("delta_g_uncertainty must be None when delta_g is None")
            self.delta_g_units = None
        else:
            if not isinstance(self.delta_g_units, str) or self.delta_g_units.strip() == "":
                raise ValueError("delta_g_units is required when delta_g is set")
        self.highest_cited_delta_g_n = _optional_repeat_count(
            "highest_cited_delta_g_n", self.highest_cited_delta_g_n
        )
        self.highest_cited_delta_g = _optional_float(
            "highest_cited_delta_g", self.highest_cited_delta_g
        )
        self.highest_cited_delta_g_uncertainty = _optional_float(
            "highest_cited_delta_g_uncertainty", self.highest_cited_delta_g_uncertainty
        )
        _check_highest_cited_delta_g(
            self.highest_cited_delta_g_n,
            self.highest_cited_delta_g,
            self.highest_cited_delta_g_units,
            self.highest_cited_delta_g_uncertainty,
        )
        if self.highest_cited_delta_g is None:
            self.highest_cited_delta_g_units = None
        self.structure = _check_structure(self.structure)
        self.registers = _check_registers(self.registers)
        _check_stability(
            self.stability_state,
            self.stability_tier,
            self.tm_C,
            self.tm_interval_low,
            self.tm_interval_high,
        )

        self.gp_mean = _float_list("gp_mean", self.gp_mean)
        self.gp_std = _float_list("gp_std", self.gp_std, minimum=0.0)
        if len(self.gp_mean) != len(self.gp_std):
            raise ValueError("gp_mean and gp_std must have the same length")

        if self.next_n is None:
            self.next_n = None
        else:
            next_n = _as_int("next_n", self.next_n)
            if next_n < 1:
                raise ValueError("next_n must be >= 1")
            self.next_n = next_n

    def to_dict(self) -> dict[str, Any]:
        """Return builtin JSON values only: str, int, float, bool, list, dict, None.

        Numpy scalars are converted. No time-course key is included.
        """
        return {
            "design_id": self.design_id,
            "prior_geometry_id": self.prior_geometry_id,
            "prior_kd_id": self.prior_kd_id,
            "n_repeats": int(self.n_repeats),
            "pair_distances_A": {key: float(value) for key, value in self.pair_distances_A.items()},
            "p_clash": {key: float(value) for key, value in self.p_clash.items()},
            "c_eff_M": {key: float(value) for key, value in self.c_eff_M.items()},
            "theta_ss": None if self.theta_ss is None else float(self.theta_ss),
            "theta_95_lower": None if self.theta_95_lower is None else float(self.theta_95_lower),
            "theta_95_upper": None if self.theta_95_upper is None else float(self.theta_95_upper),
            "da": None if self.da is None else float(self.da),
            "p_capture": None if self.p_capture is None else float(self.p_capture),
            "gp_mean": [float(value) for value in self.gp_mean],
            "gp_std": [float(value) for value in self.gp_std],
            "next_n": None if self.next_n is None else int(self.next_n),
            "calibrated": True if self.calibrated else False,
            "warnings": list(self.warnings),
            "omitted": list(self.omitted),
            "tm_C": None if self.tm_C is None else float(self.tm_C),
            "tm_interval_low": (
                None if self.tm_interval_low is None else float(self.tm_interval_low)
            ),
            "tm_interval_high": (
                None if self.tm_interval_high is None else float(self.tm_interval_high)
            ),
            "delta_g": None if self.delta_g is None else float(self.delta_g),
            "delta_g_units": self.delta_g_units,
            "delta_g_uncertainty": (
                None if self.delta_g_uncertainty is None else float(self.delta_g_uncertainty)
            ),
            "highest_cited_delta_g_n": (
                None
                if self.highest_cited_delta_g_n is None
                else int(self.highest_cited_delta_g_n)
            ),
            "highest_cited_delta_g": (
                None if self.highest_cited_delta_g is None else float(self.highest_cited_delta_g)
            ),
            "highest_cited_delta_g_units": self.highest_cited_delta_g_units,
            "highest_cited_delta_g_uncertainty": (
                None
                if self.highest_cited_delta_g_uncertainty is None
                else float(self.highest_cited_delta_g_uncertainty)
            ),
            "structure": self.structure,
            "registers": self.registers,
            "stability_state": self.stability_state,
            "stability_tier": self.stability_tier,
            "stability_omitted": list(self.stability_omitted),
        }


def _check_theta_interval(
    theta_ss: float | None,
    lower: float | None,
    upper: float | None,
) -> None:
    if theta_ss is None and (lower is not None or upper is not None):
        raise ValueError("theta bounds require theta_ss; refusing to invent occupancy")
    if lower is None or upper is None:
        return
    if lower > upper:
        raise ValueError("theta 95% interval is inverted")
    if theta_ss is not None and not (lower <= theta_ss <= upper):
        raise ValueError("theta_ss lies outside the supplied 95% interval")


def _check_capture_omission(
    da: float | None,
    p_capture: float | None,
    omitted: list[str],
) -> None:
    """Keep capture unset when the caller did not supply Da.

    P(capture) is not computed here. If Da is missing, the caller must say
    which rate was omitted: k_escape or k_capture.
    """
    if da is not None:
        return
    if p_capture is not None:
        raise ValueError("p_capture must be None when da is None")
    if "k_escape" not in omitted and "k_capture" not in omitted:
        raise ValueError(
            "When da is None, omitted must include 'k_escape' or 'k_capture'"
        )


def _stability_label(name: str, value: object, allowed: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{name} must be one of {list(allowed)}")
    return value


def _check_stability(
    state: str,
    tier: str,
    tm_C: float | None,
    interval_low: float | None,
    interval_high: float | None,
) -> None:
    """Keep the packaged tier and Tm consistent with the thermal-gate state.

    pass and fail both used a matched Tm, so the tier is literature_prior.
    extrapolated and omitted do not invent a Tm to fill the hole.
    """
    expected_tier = _TIER_FOR_STATE[state]
    if tier != expected_tier:
        raise ValueError(
            f"stability_tier {tier!r} does not match stability_state {state!r}. "
            f"Expected {expected_tier!r}."
        )
    if state in ("omitted", "extrapolated"):
        if tm_C is not None or interval_low is not None or interval_high is not None:
            raise ValueError(
                f"stability_state {state!r} does not report a Tm. "
                "tm_C and its interval must be None."
            )
        return
    if tm_C is None:
        raise ValueError("stability_state 'pass' or 'fail' requires tm_C")
    if (interval_low is None) != (interval_high is None):
        raise ValueError("tm interval bounds must both be present or both be absent")
    if interval_low is None or interval_high is None:
        return
    if interval_low > interval_high:
        raise ValueError("tm interval is inverted")
    if not (interval_low <= tm_C <= interval_high):
        raise ValueError("tm_C lies outside the supplied interval")


def _optional_repeat_count(name: str, value: object) -> int | None:
    if value is None:
        return None
    count = _as_int(name, value)
    if count < 1:
        raise ValueError(f"{name} must be >= 1")
    return count


def _check_highest_cited_delta_g(
    n_repeats: int | None,
    value: float | None,
    units: str | None,
    uncertainty: float | None,
) -> None:
    """The ranked length, its value, and its units travel together.

    A missing rank stores none of them. A present rank needs the repeat
    count, the printed value, and the units from that row. Uncertainty
    may stay empty when the source row has none.
    """
    if value is None:
        if n_repeats is not None:
            raise ValueError(
                "highest_cited_delta_g_n must be empty when highest_cited_delta_g is None"
            )
        if units not in (None, ""):
            raise ValueError(
                "highest_cited_delta_g_units must be empty when highest_cited_delta_g is None"
            )
        if uncertainty is not None:
            raise ValueError(
                "highest_cited_delta_g_uncertainty must be None when "
                "highest_cited_delta_g is None"
            )
        return
    if n_repeats is None:
        raise ValueError("highest_cited_delta_g_n is required when highest_cited_delta_g is set")
    if not isinstance(units, str) or units.strip() == "":
        raise ValueError("highest_cited_delta_g_units is required when highest_cited_delta_g is set")


def _json_number(name: str, value: object) -> float:
    number = _as_float(name, value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _check_structure(value: object) -> dict[str, Any] | None:
    """Keep a structural report JSON-shaped and uncalibrated.

    None means the screw report was not computed. A dict must be the
    key set produced by ``StructuralReport.to_dict``. ``calibrated``
    inside that dict must be false. This checker does not recompute
    pitch, phase, or the worm-like chain.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("structure must be a dict or None")
    if set(value) != STRUCTURE_KEYS:
        missing = sorted(STRUCTURE_KEYS - set(value))
        extra = sorted(set(value) - STRUCTURE_KEYS)
        raise ValueError(f"structure keys mismatch. missing={missing} extra={extra}")
    if value["calibrated"] is not False:
        raise ValueError("structure.calibrated must be false")
    if not isinstance(value["provenance"], str) or value["provenance"].strip() == "":
        raise ValueError("structure.provenance must be a non-empty string")
    if value["contour_definition"] != "n_repeats * rise_per_repeat":
        raise ValueError("structure.contour_definition is not the screw contour")
    if value["uncertainty_model"] != "delta_method_on_jacobian_engineering_widths":
        raise ValueError("structure.uncertainty_model is not the Jacobian delta method")
    if type(value["rigid_screw"]) is not bool:
        raise TypeError("structure.rigid_screw must be a bool")
    copied: dict[str, Any] = dict(value)
    for name in (
        "n_repeats",
        "rise_A",
        "twist_rad",
        "docking_radius_A",
        "scaffold_radius_A",
        "pitch_A",
        "repeats_per_turn",
        "axial_span_A",
        "contour_A",
        "contour_nm",
        "persistence_length_nm",
        "persistence_length_A",
        "wlc_end_to_end_rms_A",
        "wlc_end_to_end_rms_nm",
        "docking_curvature_per_A",
        "docking_torsion_per_A",
        "backbone_curvature_per_A",
        "backbone_torsion_per_A",
    ):
        copied[name] = _json_number(f"structure.{name}", value[name])
    n_repeats = _as_int("structure.n_repeats", value["n_repeats"])
    if n_repeats < 1:
        raise ValueError("structure.n_repeats must be >= 1")
    copied["n_repeats"] = n_repeats
    copied["warnings"] = _string_list("structure.warnings", value["warnings"])
    pairs = value["pairs"]
    if not isinstance(pairs, list):
        raise TypeError("structure.pairs must be a list")
    copied_pairs: list[dict[str, Any]] = []
    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict) or set(pair) != PAIR_STRUCTURE_KEYS:
            raise ValueError(f"structure.pairs[{index}] keys do not match the pair report")
        if type(pair["linearization_crosses_zero"]) is not bool:
            raise TypeError(f"structure.pairs[{index}].linearization_crosses_zero must be a bool")
        row = {
            "i": _as_int(f"structure.pairs[{index}].i", pair["i"]),
            "j": _as_int(f"structure.pairs[{index}].j", pair["j"]),
            "delta_repeats": _as_int(
                f"structure.pairs[{index}].delta_repeats", pair["delta_repeats"]
            ),
            "linearization_crosses_zero": pair["linearization_crosses_zero"],
        }
        for name in (
            "phase_rad",
            "facing_cosine",
            "chord_A",
            "axial_A",
            "chord_sigma_A",
            "chord_95_low_A",
            "chord_95_high_A",
        ):
            row[name] = _json_number(f"structure.pairs[{index}].{name}", pair[name])
        copied_pairs.append(row)
    copied["pairs"] = copied_pairs
    copied["calibrated"] = False
    return copied


def _check_registers(value: object) -> dict[str, Any] | None:
    """Keep the team-length register uncalibrated and internally consistent.

    The four lengths are the team choices. ``channeling_candidate_is_steric_minimum``
    must match ``shortest_end_pair_n``. This checker does not rescore clash.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("registers must be a dict or None")
    if set(value) != REGISTER_KEYS:
        missing = sorted(REGISTER_KEYS - set(value))
        extra = sorted(set(value) - REGISTER_KEYS)
        raise ValueError(f"registers keys mismatch. missing={missing} extra={extra}")
    if value["calibrated"] is not False:
        raise ValueError("registers.calibrated must be false")
    copied: dict[str, Any] = dict(value)
    expected_n = {
        "lower_extrema_n": TEAM_LOWER_N,
        "upper_extrema_n": TEAM_UPPER_N,
        "biomarker_n": TEAM_BIOMARKER_N,
        "channeling_candidate_n": TEAM_CHANNELING_N,
    }
    for name, expected in expected_n.items():
        found = _as_int(f"registers.{name}", value[name])
        if found != expected:
            raise ValueError(f"registers.{name} must stay {expected}")
        copied[name] = found
    if value["one_turn_n"] is None:
        copied["one_turn_n"] = None
    else:
        copied["one_turn_n"] = _as_int("registers.one_turn_n", value["one_turn_n"])
    for name in (
        "lower_bound_in_phillips2012_ctpra_dsc",
        "upper_bound_in_phillips2012_ctpra_dsc",
        "channeling_candidate_in_phillips2012_ctpra_dsc",
        "biomarker_n_is_library_minimum",
        "channeling_candidate_is_steric_minimum",
    ):
        if type(value[name]) is not bool:
            raise TypeError(f"registers.{name} must be a bool")
    if value["shortest_end_pair_n"] is None:
        copied["shortest_end_pair_n"] = None
    else:
        copied["shortest_end_pair_n"] = _as_int(
            "registers.shortest_end_pair_n", value["shortest_end_pair_n"]
        )
    if value["active_learner_next_n"] is None:
        copied["active_learner_next_n"] = None
    else:
        copied["active_learner_next_n"] = _as_int(
            "registers.active_learner_next_n", value["active_learner_next_n"]
        )
    flag = copied["channeling_candidate_is_steric_minimum"]
    if flag != (copied["shortest_end_pair_n"] == TEAM_CHANNELING_N):
        raise ValueError(
            "channeling_candidate_is_steric_minimum must match shortest_end_pair_n"
        )
    copied["notes"] = _string_list("registers.notes", value["notes"])
    pairs = value["end_pairs"]
    if not isinstance(pairs, list):
        raise TypeError("registers.end_pairs must be a list")
    copied_pairs: list[dict[str, Any]] = []
    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            raise TypeError(f"registers.end_pairs[{index}] must be an object")
        copied_pairs.append(
            {
                "n": _as_int(f"registers.end_pairs[{index}].n", pair["n"]),
                "end_pair_p_clash": _json_number(
                    f"registers.end_pairs[{index}].end_pair_p_clash",
                    pair["end_pair_p_clash"],
                ),
                "p_instability": _json_number(
                    f"registers.end_pairs[{index}].p_instability",
                    pair["p_instability"],
                ),
                "thermal_state": _identifier(
                    f"registers.end_pairs[{index}].thermal_state",
                    pair["thermal_state"],
                ),
            }
        )
    copied["end_pairs"] = copied_pairs
    copied["calibrated"] = False
    return copied


def assemble_report(
    *,
    design_id: str,
    prior_geometry_id: str,
    prior_kd_id: str,
    n_repeats: int,
    pair_distances_A: Mapping[str, float],
    p_clash: Mapping[str, float],
    c_eff_M: Mapping[str, float],
    theta_ss: float | None = None,
    theta_95_lower: float | None = None,
    theta_95_upper: float | None = None,
    da: float | None = None,
    p_capture: float | None = None,
    gp_mean: Sequence[float] | None = None,
    gp_std: Sequence[float] | None = None,
    next_n: int | None = None,
    calibrated: bool = False,
    warnings: Sequence[str] | None = None,
    omitted: Sequence[str] | None = None,
    evidence_source: str = "none",
    tm_C: float | None = None,
    tm_interval_low: float | None = None,
    tm_interval_high: float | None = None,
    stability_state: str = "omitted",
    stability_tier: str = "omitted",
    stability_omitted: Sequence[str] | None = None,
    delta_g: float | None = None,
    delta_g_units: str | None = None,
    delta_g_uncertainty: float | None = None,
    highest_cited_delta_g_n: int | None = None,
    highest_cited_delta_g: float | None = None,
    highest_cited_delta_g_units: str | None = None,
    highest_cited_delta_g_uncertainty: float | None = None,
    structure: dict[str, Any] | None = None,
    registers: dict[str, Any] | None = None,
) -> DesignReport:
    """Package an already-computed design summary.

    calibrated is stored exactly as passed. Passing calibrated=True raises
    ValueError unless evidence_source == "wet_lab". The default
    evidence_source is "none".

    This function does not call the physics, mechanism, or GP modules. It
    does not fill p_capture from da, and it does not add a theta time course.
    It does not estimate Tm. Pass the thermal-gate numbers in, or leave the
    stability fields at their omitted defaults.

    stability_tier must match stability_state: omitted stays omitted,
    extrapolated stays extrapolated, and pass or fail is literature_prior.
    calibrated is still False unless evidence_source == "wet_lab". A
    literature_prior tier is not a wet-lab calibration.
    """
    if not isinstance(evidence_source, str):
        raise TypeError("evidence_source must be a str")
    if type(calibrated) is not bool:
        raise TypeError("calibrated must be a bool")
    if calibrated and evidence_source != _WET_LAB:
        raise ValueError(_CALIBRATED_REFUSAL)

    if (gp_mean is None) != (gp_std is None):
        raise ValueError("gp_mean and gp_std must both be provided or both omitted")

    claim: object | None = _WET_LAB_CLAIM if evidence_source == _WET_LAB else None
    return DesignReport(
        design_id=design_id,
        prior_geometry_id=prior_geometry_id,
        prior_kd_id=prior_kd_id,
        n_repeats=n_repeats,
        pair_distances_A=dict(pair_distances_A),
        p_clash=dict(p_clash),
        c_eff_M=dict(c_eff_M),
        theta_ss=theta_ss,
        theta_95_lower=theta_95_lower,
        theta_95_upper=theta_95_upper,
        da=da,
        p_capture=p_capture,
        gp_mean=[] if gp_mean is None else list(gp_mean),
        gp_std=[] if gp_std is None else list(gp_std),
        next_n=next_n,
        calibrated=calibrated,
        warnings=[] if warnings is None else list(warnings),
        omitted=[] if omitted is None else list(omitted),
        tm_C=tm_C,
        tm_interval_low=tm_interval_low,
        tm_interval_high=tm_interval_high,
        stability_state=stability_state,
        stability_tier=stability_tier,
        stability_omitted=[] if stability_omitted is None else list(stability_omitted),
        delta_g=delta_g,
        delta_g_units=delta_g_units,
        delta_g_uncertainty=delta_g_uncertainty,
        highest_cited_delta_g_n=highest_cited_delta_g_n,
        highest_cited_delta_g=highest_cited_delta_g,
        highest_cited_delta_g_units=highest_cited_delta_g_units,
        highest_cited_delta_g_uncertainty=highest_cited_delta_g_uncertainty,
        structure=structure,
        registers=registers,
        calibration_claim=claim,
    )
