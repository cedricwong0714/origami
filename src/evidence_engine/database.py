# src/evidence_engine/database.py
from typing import Optional
from src.evidence_engine.schema import EvidenceEntry, CitationRecord

DEFAULT_EVIDENCE_STORE: dict[str, EvidenceEntry] = {
    "k_cat_OtsA": EvidenceEntry(
        parameter_key="k_cat_OtsA",
        value=0.5,
        unit="s^-1",
        confidence_score=0.95,
        experimental_context="Purified E. coli OtsA enzyme assay at 25°C",
        citation=CitationRecord(
            citation_id="DOI_10.1074/jbc.272.7.4367",
            title="Characterization of Trehalose-6-Phosphate Synthase",
            authors=["Giaever, S.", "Styrvold, O. B."],
            journal="Journal of Biological Chemistry",
            year=1997,
            doi="10.1074/jbc.272.7.4367"
        )
    )
}

class EvidenceDatabase:
    """In-memory evidence database manager."""
    
    def __init__(self, initial_data: Optional[dict[str, EvidenceEntry]] = None):
        self._store: dict[str, EvidenceEntry] = initial_data or DEFAULT_EVIDENCE_STORE.copy()

    def get_entry(self, parameter_key: str) -> Optional[EvidenceEntry]:
        return self._store.get(parameter_key)

    def register_entry(self, entry: EvidenceEntry) -> None:
        self._store[entry.parameter_key] = entry

    def list_all_keys(self) -> list[str]:
        return list(self._store.keys())