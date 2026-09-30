"""Write the wiki stability snapshot used when the live API is offline.

Payload matches ``GET /api/stability/confirm``: Phillips 2012 CTPRa DSC
length fit at n = 3, 8, and 14.
"""

from __future__ import annotations

import json
from pathlib import Path

from origami.api.stability import literature_confirm

# 37 C is the conventional E. coli incubation temperature used as the
# comparison point. It is an operating assumption, not a DSC setpoint
# from Phillips et al. 2012.
_T_ASSAY_C = 37.0


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
    payload = _plain(literature_confirm(_T_ASSAY_C))
    if not isinstance(payload, dict):
        raise TypeError("literature_confirm must return a dict")
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
