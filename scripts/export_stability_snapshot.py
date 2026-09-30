"""Write the wiki stability snapshot used when the live API is offline.

Rows come from ``stability_panel``. Series stay separate. No Tm(n) is fit.
"""

from __future__ import annotations

import json
from pathlib import Path

from origami.drylab import stability_panel

# 37 C is the conventional E. coli incubation temperature used as the
# comparison point. It is an operating assumption, not a DSC setpoint
# from Phillips et al. 2012 or Cortajarena et al. 2011.
_T_ASSAY_C = 37.0
_NOTE = (
    "37 C is an E. coli operating assumption, not a paper setpoint. "
    "The four series stay separate and are not averaged. "
    "n outside a series is extrapolated and no Tm(n) was fit."
)


def _plain(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / "web" / "structural" / "public" / "stability-snapshot.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = _plain(stability_panel(_T_ASSAY_C))
    if not isinstance(rows, list):
        raise TypeError("stability_panel must return a list of rows")
    payload = {
        "calibrated": False,
        "t_assay_C": _T_ASSAY_C,
        "rows": rows,
        "note": _NOTE,
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
