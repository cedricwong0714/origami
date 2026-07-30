# src/evidence_engine/retriever.py
import json
import urllib.request
import urllib.parse
from typing import Optional
from src.evidence_engine.database import EvidenceDatabase
from src.evidence_engine.schema import EvidenceEntry, CitationRecord

class EvidenceRetriever:
    def __init__(self, db: Optional[EvidenceDatabase] = None):
        self.db = db or EvidenceDatabase()

    def fetch_citation_from_pubmed(self, pmid: str) -> Optional[CitationRecord]:
        """
        Automated external retrieval: Fetches paper metadata directly from PubMed NCBI E-utilities API.
        """
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CLASP-Copilot/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    result = data.get("result", {}).get(str(pmid), {})
                    
                    authors = [a.get("name", "") for a in result.get("authors", [])]
                    title = result.get("title", "Unknown Title").strip(".")
                    journal = result.get("source", "Unknown Journal")
                    pubdate = result.get("pubdate", "2000").split()[0]
                    year = int(pubdate) if pubdate.isdigit() else 2000
                    
                    return CitationRecord(
                        citation_id=f"PUBMED_{pmid}",
                        title=title,
                        authors=authors,
                        journal=journal,
                        year=year,
                        pmid=str(pmid)
                    )
        except Exception as e:
            # Fall back gracefully if network or API is down
            print(f"[Warning] Failed to fetch PubMed ID {pmid}: {e}")
            return None

    def fetch_parameter_with_citation(
        self, 
        key: str, 
        fallback_value: float, 
        fallback_pmid: Optional[str] = None
    ) -> tuple[float, Optional[EvidenceEntry]]:
        """
        1. Checks local storage.
        2. If missing but a PMID is provided, automatically fetches citation from PubMed live API.
        3. Caches the newly retrieved record into the local DB.
        """
        entry = self.db.get_entry(key)
        if entry:
            return entry.value, entry

        # Automated live retrieval step
        if fallback_pmid:
            citation = self.fetch_citation_from_pubmed(fallback_pmid)
            if citation:
                new_entry = EvidenceEntry(
                    parameter_key=key,
                    value=fallback_value,
                    unit="arbitrary",
                    confidence_score=0.85,
                    experimental_context="Fetched automatically via PubMed API",
                    citation=citation
                )
                self.db.register_entry(new_entry)
                return fallback_value, new_entry

        return fallback_value, None