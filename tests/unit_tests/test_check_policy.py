from src.compliance.check_policy import check_policy


def test_flags_release() -> None:
    flags = check_policy({"notes": "planned environmental release"})
    assert flags
    assert all(isinstance(f, str) for f in flags)


def test_no_halt_empty() -> None:
    flags = check_policy({"notes": "standard lab cloning"})
    assert flags == []


def test_nested_release_is_flagged() -> None:
    flags = check_policy({"notes": {"detail": "planned environmental release"}})
    assert flags
    assert any("release" in flag.lower() for flag in flags)
