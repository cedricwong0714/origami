"""Pure audit-row builder. Does not write files."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def log_audit(event: dict) -> dict:
    """Return an audit row with ISO timestamp and id hash of canonical JSON.

    The original ``event`` is copied into the row. No filesystem writes.
    """
    canonical = json.dumps(event, sort_keys=True, default=str, separators=(",", ":"))
    event_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "id": event_id,
        "timestamp": timestamp,
        "event": dict(event),
    }
