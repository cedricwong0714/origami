import importlib.util
from pathlib import Path

# Load by file path so src.ui.__init__ (dashboard/sklearn) is not imported.
_PATH = Path(__file__).resolve().parents[2] / "src" / "ui" / "make_passport.py"
_SPEC = importlib.util.spec_from_file_location("src_ui_make_passport", _PATH)
assert _SPEC and _SPEC.loader
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
make_passport = _MOD.make_passport


def test_export_denied_by_default() -> None:
    passport = make_passport({"design_id": "d1", "biosecurity": "pass"})
    assert passport["human_signoff_required"] is True
    assert passport["export_allowed"] is False


def test_export_needs_both() -> None:
    passport = make_passport(
        {"design_id": "d1", "biosecurity": "pass", "human_signoff": True}
    )
    assert passport["export_allowed"] is True


def test_biosecurity_fail_blocks_export() -> None:
    passport = make_passport(
        {"design_id": "d1", "biosecurity": "block", "human_signoff": True}
    )
    assert passport["export_allowed"] is False
