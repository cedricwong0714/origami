# src/evidence_engine/schema.py
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class CitationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    citation_id: str
    title: str
    authors: list[str]
    journal: str
    year: int
    doi: Optional[str] = None
    pmid: Optional[str] = None

class EvidenceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    parameter_key: str
    value: float
    unit: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    experimental_context: str
    citation: CitationRecord