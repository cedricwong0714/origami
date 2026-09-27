from src.compliance.scan_deps import scan_deps


def test_unpinned() -> None:
    findings = scan_deps("numpy\n")
    assert len(findings) == 1
    assert findings[0]["issue"].startswith("unpinned")


def test_pinned_empty() -> None:
    findings = scan_deps("numpy==1.26.0\npytest==8.0.0\n")
    assert findings == []
