"""
ORIGAMI compliance layer — code implementations of AGENTS.md templates.

This package operationalizes uncertainty, provenance, sequence integrity,
verification layers, and honest refusal paths required by AGENTS.md.
"""

from src.compliance.biological_parameters import (
    BiologicalParameter,
    ORIGAMI_PARAMETER_LIBRARY,
    get_parameter_or_warn,
)
from src.compliance.data_integrity import (
    DataOverwriteError,
    ExperimentalDataset,
    safe_write_experimental_data,
)
from src.compliance.models import (
    Check,
    ForbiddenSiteResult,
    ReadingFrameResult,
    UnexpectedSequenceModificationError,
    VerificationLayerResult,
)
from src.compliance.prediction_result import (
    PredictionResult,
    assign_confidence_tier_from_maturity,
    profile_prediction_to_result,
)
from src.compliance.sequence_integrity import (
    check_forbidden_sites,
    compute_sequence_checksum,
    verify_reading_frame,
    verify_sequence_unchanged,
)
from src.compliance.structured_answer import StructuredBiologicalAnswer
from src.compliance.units import ConcentrationUnit, UnitMismatchError, convert_concentration

__all__ = [
    "BiologicalParameter",
    "Check",
    "ConcentrationUnit",
    "DataOverwriteError",
    "ExperimentalDataset",
    "ForbiddenSiteResult",
    "ORIGAMI_PARAMETER_LIBRARY",
    "PredictionResult",
    "ReadingFrameResult",
    "StructuredBiologicalAnswer",
    "UnexpectedSequenceModificationError",
    "UnitMismatchError",
    "VerificationLayerResult",
    "assign_confidence_tier_from_maturity",
    "check_forbidden_sites",
    "compute_sequence_checksum",
    "convert_concentration",
    "get_parameter_or_warn",
    "profile_prediction_to_result",
    "safe_write_experimental_data",
    "verify_reading_frame",
    "verify_sequence_unchanged",
]
