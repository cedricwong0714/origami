from src.evidence_engine.retrieve_docs import retrieve_docs


def test_empty_corpus_insufficient_evidence():
    result = retrieve_docs("scaffold folding", [])
    assert result["chunks"] == []
    assert result["insufficient_evidence"] is True
    assert result["confidence"] == 0.0
    assert result["human_review_required"] is True


def test_no_overlap_insufficient_evidence():
    corpus = [
        {
            "source_id": "s1",
            "title": "Unrelated",
            "authors": ["A"],
            "year": 2020,
            "doi": "10.0000/example",
            "text": "completely different vocabulary xyz",
        }
    ]
    result = retrieve_docs("kinesin processivity assay", corpus)
    assert result["chunks"] == []
    assert result["insufficient_evidence"] is True


def test_keyword_overlap_ranks_and_confidence():
    corpus = [
        {
            "source_id": "low",
            "title": "Notes",
            "authors": ["B"],
            "year": 2019,
            "doi": "10.0000/b",
            "text": "folding of paper models",
        },
        {
            "source_id": "high",
            "title": "DNA origami scaffold folding",
            "authors": ["A"],
            "year": 2021,
            "doi": "10.0000/a",
            "text": "DNA origami scaffold folding protocol details",
        },
    ]
    result = retrieve_docs("DNA origami scaffold folding", corpus)
    assert result["insufficient_evidence"] is False
    assert result["chunks"][0]["source_id"] == "high"
    assert "extracted_passage" in result["chunks"][0]
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["chunks"][0]["score"] >= result["chunks"][1]["score"]
    assert result["human_review_required"] is False
