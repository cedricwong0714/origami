"""Containment passport fields. Export is denied unless dual human+biosecurity gates pass."""

from __future__ import annotations


def make_passport(design: dict) -> dict:
    """Build a containment passport dict.

    ``export_allowed`` is True only when ``human_signoff`` is True and
    ``biosecurity`` is ``pass``. ``human_signoff_required`` is always True.
    """
    design_id = design.get("design_id", "")
    biosecurity = design.get("biosecurity", "unknown")
    human_signoff = design.get("human_signoff") is True
    export_allowed = human_signoff and str(biosecurity) == "pass"
    return {
        "design_id": design_id,
        "biosecurity": biosecurity,
        "human_signoff_required": True,
        "human_signoff": human_signoff,
        "export_allowed": export_allowed,
    }
