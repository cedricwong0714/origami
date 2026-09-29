"""Write the wiki snapshot used when the live API is offline."""

from __future__ import annotations

import json
from pathlib import Path

from origami.api.structural import predict_payload


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
    target = root / "web" / "structural" / "public" / "sa-snapshot.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = _plain(predict_payload((3, 8, 14)))
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
