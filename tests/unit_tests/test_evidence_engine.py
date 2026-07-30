# tests/unit_tests/test_evidence_engine.py
from src.evidence_engine.retriever import EvidenceRetriever

def test_live_pubmed_auto_retrieval():
    retriever = EvidenceRetriever()
    
    # Query a parameter not in local memory, providing a valid PubMed ID
    val, entry = retriever.fetch_parameter_with_citation(
        key="live_test_param",
        fallback_value=12.5,
        fallback_pmid="24158912"
    )

    assert val == 12.5
    assert entry is not None
    assert entry.citation.pmid == "24158912"
    assert "PUBMED_24158912" in entry.citation.citation_id