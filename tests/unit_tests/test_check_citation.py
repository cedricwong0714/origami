from src.evidence_engine.check_citation import check_citation


def test_supported_when_doi_and_number_in_passages():
    answer = "See 10.1234/abcde reporting 12.5 nM."
    passages = [
        {
            "source_id": "s1",
            "doi": "10.1234/abcde",
            "extracted_passage": "Kd was 12.5 nM in buffer.",
        }
    ]
    result = check_citation(answer, passages)
    assert result["is_supported"] is True
    assert result["unsupported"] == []
    assert "10.1234/abcde" in result["supported"]
    assert "12.5" in result["supported"]


def test_unsupported_doi_not_in_passages():
    answer = "Claim cites 10.9999/not-here."
    passages = [{"extracted_passage": "no doi here", "doi": "10.1111/other"}]
    result = check_citation(answer, passages)
    assert "10.9999/not-here" in result["unsupported"]
    assert result["is_supported"] is False


def test_unsupported_number_not_in_passages():
    answer = "The rate was 42.0"
    passages = [{"extracted_passage": "the rate was 7"}]
    result = check_citation(answer, passages)
    assert "42.0" in result["unsupported"]
    assert result["is_supported"] is False
