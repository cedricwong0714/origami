"""Streamlit / Hugging Face entry.

Hosts look for a root script. This file puts the repo on sys.path so
``origami`` and ``sandbox`` resolve. Do not use ``app.py`` on a host:
that file starts the older Explore/Design UI, not this chassis sandbox.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import sandbox.app  # noqa: F401, E402
