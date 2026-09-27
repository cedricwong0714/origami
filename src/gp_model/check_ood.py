"""Feature-bound out-of-domain checks (no model training)."""

from __future__ import annotations


def check_ood(features: dict[str, float], bounds: dict[str, tuple[float, float]]) -> dict:
    """Report whether ``features`` lie inside inclusive ``bounds``.

    ``bounds`` maps feature name to ``(lower, upper)``.
    Missing bounds for a present feature, or a value outside the interval,
    are listed in ``reasons`` and set ``in_domain`` to False.
    """
    reasons: list[str] = []
    for name, value in sorted(features.items(), key=lambda item: item[0]):
        if name not in bounds:
            reasons.append(f"no bounds for feature '{name}'")
            continue
        lower, upper = bounds[name]
        numeric = float(value)
        if numeric < float(lower) or numeric > float(upper):
            reasons.append(
                f"'{name}'={numeric} outside [{float(lower)}, {float(upper)}]"
            )

    return {
        "in_domain": len(reasons) == 0,
        "reasons": reasons,
    }
