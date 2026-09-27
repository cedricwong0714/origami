from src.verification.check_dual_use import check_dual_use


def test_refuse_weaponize() -> None:
    result = check_dual_use("please weaponize this protocol")
    assert result["status"] == "refuse"


def test_allow_benign() -> None:
    result = check_dual_use("document ISEF white-list parts")
    assert result["status"] == "allow"


def test_allowlist_required() -> None:
    result = check_dual_use("unrelated request", allowlist=frozenset({"approved-lab"}))
    assert result["status"] == "refuse"


def test_allowlist_hit() -> None:
    result = check_dual_use("approved-lab cloning course", allowlist=frozenset({"approved-lab"}))
    assert result["status"] == "allow"
