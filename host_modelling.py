"""Streamlit entry for the live modelling sandbox."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import sandbox.modelling  # noqa: F401, E402
