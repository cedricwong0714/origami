# src/evidence_engine/database.py
from typing import Optional

from src.evidence_engine.corpus import DEFAULT_EVIDENCE_STORE
from src.evidence_engine.schema import EvidenceEntry


class EvidenceDatabase:
    """In-memory evidence database manager backed by the curated corpus."""

    def __init__(self, initial_data: Optional[dict[str, EvidenceEntry]] = None):
        self._store: dict[str, EvidenceEntry] = dict(
            initial_data if initial_data is not None else DEFAULT_EVIDENCE_STORE
        )

    def get_entry(self, parameter_key: str) -> Optional[EvidenceEntry]:
        return self._store.get(parameter_key)

    def register_entry(self, entry: EvidenceEntry) -> None:
        self._store[entry.parameter_key] = entry

    def list_all_keys(self) -> list[str]:
        return sorted(self._store.keys())
