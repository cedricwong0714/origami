"""Caller-supplied signal, binder, and partner pairs.

Each pair records the dissociation constant in molar and the source of that
Kd. An optional ``kd_sigma_M`` is the caller's uncertainty on that Kd. It is
not filled in from the CaM–M13 error bar. The CaM–M13 example, including its
published sigma, is available only from ``default_cam_m13_pair``.
``load_signal_pairs`` does not fill in a missing Kd. Association rate is
optional and is never invented: the 2006 CaM–M13 paper does not report kon.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from origami.priors import CAM_M13_KD_M


@dataclass(frozen=True)
class SignalPair:
    """One signal-gated binder–partner interaction.

    ``kd_M`` is the dissociation constant in molar. ``kd_source`` is the
    caller-supplied citation or note for that number. ``kd_sigma_M`` is the
    standard deviation of that Kd in molar when the caller has one. None
    means the uncertainty was not reported, not that the CaM–M13 sigma
    applies. ``kon_per_M_s`` is the association rate in per molar per second
    when the caller has one. None means the rate is unknown, not that a
    default rate should be assumed.
    """

    signal_id: str
    binder_id: str
    partner_id: str
    kd_M: float
    kd_source: str
    kd_sigma_M: float | None = None
    kon_per_M_s: float | None = None

    def __post_init__(self) -> None:
        for field in ("signal_id", "binder_id", "partner_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or value.strip() == "":
                raise ValueError(f"{field} must be a non-empty string")
        if not isinstance(self.kd_source, str) or self.kd_source.strip() == "":
            raise ValueError("kd_source must be a non-empty string")
        _require_positive_number("kd_M", self.kd_M)
        if self.kd_sigma_M is not None:
            _require_nonnegative_number("kd_sigma_M", self.kd_sigma_M)
        if self.kon_per_M_s is not None:
            _require_positive_number("kon_per_M_s", self.kon_per_M_s)


def default_cam_m13_pair() -> SignalPair:
    """Example pair: calcium, calmodulin, and the M13 peptide.

    Kd, ``kd_sigma_M``, and ``kd_source`` are taken from ``CAM_M13_KD_M``
    (Biochemistry 2006, DOI 10.1021/bi060857u; Kd = 0.19 ± 0.09 nM). That
    paper does not report kon, so ``kon_per_M_s`` is None.
    """
    return SignalPair(
        signal_id="Ca2+",
        binder_id="CaM",
        partner_id="M13",
        kd_M=CAM_M13_KD_M.value,
        kd_source=CAM_M13_KD_M.source,
        kd_sigma_M=CAM_M13_KD_M.sigma,
        kon_per_M_s=None,
    )


def load_signal_pairs(rows: list[dict]) -> list[SignalPair]:
    """Build signal pairs from row dicts.

    Each row must include ``signal_id``, ``binder_id``, ``partner_id``,
    ``kd_M``, and ``kd_source``. ``kd_sigma_M`` and ``kon_per_M_s`` are
    optional.

    A missing or null ``kd_M``, an empty ``kd_source``, or a Kd that is not
    strictly positive raises ``ValueError``. Kd is not replaced with the
    CaM–M13 value. A missing ``kd_sigma_M`` stays None and is not replaced
    with the CaM–M13 sigma. A present ``kd_sigma_M`` must be >= 0. A missing
    ``kon_per_M_s`` stays None.
    """
    if not isinstance(rows, list):
        raise ValueError("signal pair rows must be a list of objects")
    return [_pair_from_row(index, row) for index, row in enumerate(rows)]


def _pair_from_row(index: int, row: object) -> SignalPair:
    if not isinstance(row, dict):
        raise ValueError(f"signal pair row {index} must be an object")
    signal_id = _identifier(index, row, "signal_id")
    binder_id = _identifier(index, row, "binder_id")
    partner_id = _identifier(index, row, "partner_id")
    return SignalPair(
        signal_id=signal_id,
        binder_id=binder_id,
        partner_id=partner_id,
        kd_M=_kd_M(signal_id, row),
        kd_source=_kd_source(signal_id, row),
        kd_sigma_M=_kd_sigma(signal_id, row),
        kon_per_M_s=_kon(signal_id, row),
    )


def _identifier(index: int, row: dict, field: str) -> str:
    if field not in row or row[field] is None:
        raise ValueError(f"signal pair row {index}: missing required field {field}")
    value = row[field]
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(
            f"signal pair row {index}: {field} must be a non-empty string"
        )
    return value


def _kd_M(signal_id: str, row: dict) -> float:
    if "kd_M" not in row or row["kd_M"] is None:
        raise ValueError(
            f"signal pair {signal_id}: missing required field kd_M. "
            "Kd is not defaulted."
        )
    return _require_positive_number("kd_M", row["kd_M"], signal_id=signal_id)


def _kd_source(signal_id: str, row: dict) -> str:
    if "kd_source" not in row or row["kd_source"] is None:
        raise ValueError(f"signal pair {signal_id}: missing required field kd_source")
    source = row["kd_source"]
    if not isinstance(source, str) or source.strip() == "":
        raise ValueError(
            f"signal pair {signal_id}: kd_source must be a non-empty string"
        )
    return source


def _kd_sigma(signal_id: str, row: dict) -> float | None:
    if "kd_sigma_M" not in row or row["kd_sigma_M"] is None:
        return None
    return _require_nonnegative_number(
        "kd_sigma_M", row["kd_sigma_M"], signal_id=signal_id
    )


def _kon(signal_id: str, row: dict) -> float | None:
    if "kon_per_M_s" not in row or row["kon_per_M_s"] is None:
        return None
    return _require_positive_number(
        "kon_per_M_s", row["kon_per_M_s"], signal_id=signal_id
    )


def _require_nonnegative_number(
    field: str,
    raw: object,
    signal_id: str | None = None,
) -> float:
    prefix = f"signal pair {signal_id}: " if signal_id is not None else ""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"{prefix}{field} must be a number >= 0")
    value = float(raw)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{prefix}{field} must be >= 0, got {raw!r}")
    return value


def _require_positive_number(
    field: str,
    raw: object,
    signal_id: str | None = None,
) -> float:
    prefix = f"signal pair {signal_id}: " if signal_id is not None else ""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"{prefix}{field} must be a number greater than 0")
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{prefix}{field} must be greater than 0, got {raw!r}")
    return value
