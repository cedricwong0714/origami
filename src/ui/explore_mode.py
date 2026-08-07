"""
Explore Mode — evidence-grounded inquiry.

Retrieves source-backed parameters, separates direct evidence from inference,
and refuses when confidence is insufficient.
"""

from __future__ import annotations

from typing import Any, Optional

from src.evidence_engine.retriever import EvidenceRetriever
from src.evidence_engine.schema import EvidenceEntry

INSUFFICIENT_EVIDENCE_MSG = "Insufficient evidence for a reliable recommendation."
MIN_DIRECT_CONFIDENCE = 0.7
MIN_INFERENCE_CONFIDENCE = 0.5


class ExploreMode:
    def __init__(self, retriever: Optional[EvidenceRetriever] = None):
        self.retriever = retriever or EvidenceRetriever()

    def ask(
        self,
        parameter_key: str,
        fallback_value: Optional[float] = None,
        fallback_pmid: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Answer an evidence question about a single parameter key.

        Never invents citations. Refuses when the local corpus (and optional
        PubMed metadata fetch) cannot support a reliable recommendation.
        """
        entry = self.retriever.db.get_entry(parameter_key)

        if entry is None and fallback_value is not None and fallback_pmid:
            _, entry = self.retriever.fetch_parameter_with_citation(
                key=parameter_key,
                fallback_value=fallback_value,
                fallback_pmid=fallback_pmid,
            )

        if entry is None:
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "message": INSUFFICIENT_EVIDENCE_MSG,
                "parameter_key": parameter_key,
                "evidence_class": "unsupported",
                "contradictions": [],
            }

        evidence_class = self._classify(entry)
        if evidence_class == "unsupported":
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "message": INSUFFICIENT_EVIDENCE_MSG,
                "parameter_key": parameter_key,
                "evidence_class": evidence_class,
                "entry": entry.model_dump(),
                "contradictions": [],
            }

        return {
            "status": "OK",
            "parameter_key": parameter_key,
            "value": entry.value,
            "unit": entry.unit,
            "evidence_class": evidence_class,
            "confidence_score": entry.confidence_score,
            "experimental_context": entry.experimental_context,
            "citation": entry.citation.model_dump(),
            "contradictions": [],
            "inference_note": None
            if evidence_class == "direct_evidence"
            else "Value is model/literature inference, not a direct CLASP wet-lab measurement.",
        }

    def list_available_evidence(self) -> list[str]:
        return self.retriever.db.list_all_keys()

    def _classify(self, entry: EvidenceEntry) -> str:
        ctx = entry.experimental_context.lower()
        if entry.confidence_score >= MIN_DIRECT_CONFIDENCE and (
            "assay" in ctx or "purified" in ctx or "measured" in ctx
        ):
            return "direct_evidence"
        if entry.confidence_score >= MIN_INFERENCE_CONFIDENCE:
            return "model_inference"
        return "unsupported"


def explore(
    parameter_key: str,
    fallback_value: Optional[float] = None,
    fallback_pmid: Optional[str] = None,
) -> dict[str, Any]:
    """Module-level convenience entrypoint."""
    return ExploreMode().ask(
        parameter_key,
        fallback_value=fallback_value,
        fallback_pmid=fallback_pmid,
    )
