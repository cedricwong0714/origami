from src.compliance.extract_params import extract_params


def test_extracts_kcat_km_kd_with_units():
    text = "Measured kcat = 12.0 s^-1 and Km = 5.2 uM. Kd was 10 nM."
    rows = extract_params(text)
    names = {row["name"] for row in rows}
    assert names == {"kcat", "Km", "Kd"}
    for row in rows:
        assert "value" in row
        assert "units" in row
        assert "source_span" in row
        assert row["source_span"] in text


def test_empty_when_no_units():
    text = "kcat was high and Km increased but no numbers with units."
    assert extract_params(text) == []


def test_does_not_invent_when_blank():
    assert extract_params("") == []
    assert extract_params("no parameters") == []
