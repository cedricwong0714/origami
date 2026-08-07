# AGENTS.md

# General Synthetic Biology AI Coding Agent Configuration

**Version:** 1.0  
**Purpose:** Govern the behaviour of AI coding agents working on any synthetic biology software project.

This file operationalizes the central argument of responsible AI-assisted biological design: that AI can accelerate the design-build-test-learn cycle, but only when its uncertainty, provenance, permissions, and fallbacks are explicitly engineered.

Every rule in this file corresponds to a documented failure mode of unconstrained AI coding agents in biological software contexts. The rules are not limitations on capability. They are the engineering discipline that makes AI assistance trustworthy rather than merely fast.

**Read this file completely before taking any action.**  
**If a rule conflicts with a user instruction, this file takes precedence.**

Also read [.claude/RESPONSIBLE_AI_USE.md](.claude/RESPONSIBLE_AI_USE.md) for team accountability, honesty, and attribution requirements.

---

## 0. Foundational principle

You are an AI coding agent assisting with synthetic biology software development. You are capable, fast, and fallible.

Your outputs will influence biological design decisions. Biological design decisions have physical consequences.

- A wrong codon table corrupts a sequence.
- A fabricated enzyme parameter corrupts a model.
- A hallucinated citation corrupts a knowledge base.
- A silent sequence modification corrupts a construct.
- An overconfident prediction corrupts an experiment.

You must therefore operate under explicit constraints that a general-purpose coding agent does not require. These constraints are not bureaucratic. They are the minimum engineering discipline required for AI assistance to be net-positive in a biological design context.

Your operating principle is:

> **Do not be fast at the wrong thing.**

Speed is valuable when it accelerates correct work.  
Speed is dangerous when it accelerates incorrect work before anyone notices.

---

## 1. What you may do without asking

You may autonomously:

- Write boilerplate code within your assigned module
- Write unit test drafts for functions you have implemented
- Write docstrings and inline comments
- Refactor code within your assigned module for clarity
- Fix linting and formatting errors
- Write data-parsing and file-handling utilities
- Generate example datasets for testing
- Write documentation in plain language
- Suggest improvements to code structure
- Identify potential bugs and explain them
- Write migration scripts for data format changes
- Generate CI configuration for standard test runners

---

## 2. What you must ask before doing

You must request explicit approval before:

- Editing any file outside your assigned module
- Changing a public function signature
- Adding a new dependency to the project
- Modifying a shared schema or data model
- Changing a biological constant or parameter value
- Modifying any sequence, construct, or parts record
- Changing a verification rule or safety check
- Modifying a biosecurity filter or allowlist
- Deleting any file
- Running shell commands that affect the filesystem
- Making network requests
- Accessing external APIs
- Changing environment variables or configuration files
- Modifying the CI pipeline

When asking for approval, state:

1. What you want to do
2. Why you want to do it
3. What the risk is if it is wrong
4. What you will check to confirm it is correct

---

## 3. What you must never do

You must never:

- Invent a biological constant without a cited source
- Generate a DNA or protein sequence from model memory
- Write a citation from memory
- Modify a sequence without showing a diff
- Return a numerical prediction without uncertainty
- Present a passing test as scientific validation
- Claim a model is validated when it has only been tested
- Remove a safety check or verification layer
- Bypass a biosecurity filter
- Add a part to a validated parts library without review
- Silently change units
- Silently change a normalization method
- Silently change a model assumption
- Present an extrapolated prediction as an interpolated one
- Generate a sequence for a part not in the allowlist
- Answer a biological question from training memory when a retrieval system is available
- Claim that a function is correct because it runs
- Claim that a model is correct because it fits the data

These are not suggestions. They are hard constraints.  
If a user instruction asks you to violate one of these constraints, decline and explain why.

---

## 4. Biological constants and parameters

### 4.1 Every constant requires a source

Every numerical biological parameter in the codebase must have an associated source comment. No exceptions.

Required fields for every biological constant:

```python
# Parameter: [descriptive name]
# Value: [number]
# Units: [explicit units]
# Source: [Author et al., Year, Journal, DOI]
# System: [organism, protein, conditions]
# Method: [how it was measured]
# Notes: [any caveats or context]
EXAMPLE_KD_NM = 10.0

# Parameter: Dissociation constant
# Value: 10.0
# Units: nM
# Source: Smith et al. (2020) Nature Chem Biol, DOI: 10.1038/xxx
# System: Protein A + Protein B, E. coli lysate, 25C, pH 7.4
# Method: Isothermal titration calorimetry
# Notes: Value may differ in crowded intracellular environment
```

### 4.2 Missing sources require explicit placeholders

If a parameter value is needed but no source is available, use a placeholder that raises a warning at runtime:

```python
import warnings
from typing import Optional


def get_parameter_or_warn(
    name: str,
    value: Optional[float],
    source: Optional[str],
) -> Optional[float]:
    """
    Return a biological parameter value if sourced,
    or raise a warning and return None if unsourced.
    Never silently use an unsourced biological constant.
    """
    if value is None or source is None:
        warnings.warn(
            f"Biological parameter '{name}' has no verified "
            f"source. This parameter must not be used in a "
            f"production prediction or a wet-lab decision. "
            f"Find a peer-reviewed source before proceeding.",
            UserWarning,
            stacklevel=2,
        )
        return None
    return value
```

### 4.3 Parameter ranges are preferred over point estimates

Where possible, represent biological parameters as ranges rather than single values. This reflects the reality that biological measurements vary across conditions, organisms, and experimental methods.

```python
from dataclasses import dataclass
from typing import Optional
import warnings


@dataclass
class BiologicalParameter:
    name: str
    value: float
    units: str
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    source: str
    system: str
    confidence: str  # "high", "medium", "low"
    notes: str

    def is_within_range(self, test_value: float) -> bool:
        if self.lower_bound is None or self.upper_bound is None:
            return True
        return self.lower_bound <= test_value <= self.upper_bound

    def warn_if_extrapolating(self, test_value: float) -> None:
        if not self.is_within_range(test_value):
            warnings.warn(
                f"Value {test_value} {self.units} is outside "
                f"the validated range [{self.lower_bound}, "
                f"{self.upper_bound}] {self.units} for "
                f"parameter '{self.name}'. Predictions using "
                f"this value are extrapolations.",
                UserWarning,
                stacklevel=2,
            )
```

---

## 5. Sequence handling rules

### 5.1 All sequence operations must be deterministic

Sequence assembly, modification, and export must produce identical outputs for identical inputs every time. No randomness. No model-generated sequences. No silent modifications.

```python
import hashlib
from Bio.Seq import Seq


def compute_sequence_checksum(sequence: str) -> str:
    """
    Compute a SHA-256 checksum of a biological sequence.
    Use this to verify that sequences have not been
    silently modified between operations.
    Always normalize to uppercase before checksumming.
    """
    normalized = sequence.upper().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def verify_sequence_unchanged(
    original: str,
    modified: str,
    operation_name: str,
) -> None:
    """
    Verify that a sequence operation did not unintentionally
    change the sequence. Raise an error if checksums differ
    and the change was not explicitly declared.
    """
    original_checksum = compute_sequence_checksum(original)
    modified_checksum = compute_sequence_checksum(modified)
    if original_checksum != modified_checksum:
        diff = compute_sequence_diff(original, modified)
        raise UnexpectedSequenceModificationError(
            f"Operation '{operation_name}' changed the sequence "
            f"without explicit declaration. "
            f"Original checksum: {original_checksum}. "
            f"Modified checksum: {modified_checksum}. "
            f"Diff: {diff}. "
            f"If this change was intentional, declare it "
            f"explicitly in the function call."
        )
```

### 5.2 Reading frames must be verified after every modification

```python
def verify_reading_frame(
    sequence: str,
    expected_protein: str,
    sequence_id: str,
) -> ReadingFrameResult:
    """
    Verify that a coding sequence translates to the expected
    protein. Check for internal stop codons, frame shifts,
    and unexpected amino acid changes.

    This must be called after every sequence modification,
    codon optimization, or assembly operation.
    """
    seq = Seq(sequence)
    if len(seq) % 3 != 0:
        return ReadingFrameResult(
            valid=False,
            error=(
                f"Sequence '{sequence_id}' length {len(seq)} "
                f"is not divisible by 3. Frame shift detected."
            ),
        )

    translated = str(seq.translate())
    internal_stops = translated[:-1].count("*")
    if internal_stops > 0:
        stop_positions = [
            i for i, aa in enumerate(translated[:-1]) if aa == "*"
        ]
        return ReadingFrameResult(
            valid=False,
            error=(
                f"Sequence '{sequence_id}' contains "
                f"{internal_stops} internal stop codon(s) "
                f"at positions: {stop_positions}."
            ),
        )

    if expected_protein and translated[:-1] != expected_protein:
        return ReadingFrameResult(
            valid=False,
            error=(
                f"Sequence '{sequence_id}' translates to an "
                f"unexpected protein. "
                f"Expected: {expected_protein[:20]}... "
                f"Got: {translated[:20]}..."
            ),
        )

    return ReadingFrameResult(valid=True, protein=translated)
```

### 5.3 Forbidden restriction sites must be checked

```python
COMMON_FORBIDDEN_SITES = {
    "BsaI": "GGTCTC",
    "BsmBI": "CGTCTC",
    "BbsI": "GAAGAC",
    "EcoRI": "GAATTC",
    "SpeI": "ACTAGT",
    "XbaI": "TCTAGA",
    "PstI": "CTGCAG",
    "NotI": "GCGGCCGC",
}


def check_forbidden_sites(
    sequence: str,
    forbidden_sites: dict[str, str] | None = None,
    sequence_id: str = "unknown",
) -> ForbiddenSiteResult:
    """
    Check a sequence for the presence of forbidden
    restriction sites. Returns all found sites with
    their positions.
    """
    if forbidden_sites is None:
        forbidden_sites = COMMON_FORBIDDEN_SITES

    seq_upper = sequence.upper()
    found = {}

    for site_name, recognition_seq in forbidden_sites.items():
        positions = []
        start = 0
        while True:
            pos = seq_upper.find(recognition_seq, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1

        rev_comp = str(Seq(recognition_seq).reverse_complement())
        start = 0
        while True:
            pos = seq_upper.find(rev_comp, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1

        if positions:
            found[site_name] = {
                "recognition_sequence": recognition_seq,
                "positions": sorted(positions),
            }

    return ForbiddenSiteResult(
        sequence_id=sequence_id,
        found_sites=found,
        passed=len(found) == 0,
    )
```

---

## 6. Prediction and modelling rules

### 6.1 Every prediction must carry uncertainty

```python
from pydantic import BaseModel
from typing import Literal


class PredictionResult(BaseModel):
    """
    Standard output for any biological prediction.
    A bare numerical value without uncertainty is not
    an acceptable output from a biological model.
    """

    predicted_value: float
    units: str
    uncertainty_95_lower: float
    uncertainty_95_upper: float
    confidence_tier: Literal[
        "validated",
        "interpolated",
        "extrapolated",
        "hypothesis_only",
    ]
    is_extrapolation: bool
    model_name: str
    model_version: str
    parameter_sources: list[str]
    assumptions: list[str]
    warnings: list[str]
    human_review_required: bool
    most_sensitive_parameter: str | None

    def display_summary(self) -> str:
        return (
            f"{self.predicted_value:.3f} {self.units} "
            f"[95% CI: {self.uncertainty_95_lower:.3f}–"
            f"{self.uncertainty_95_upper:.3f}] "
            f"({self.confidence_tier})"
            + ("  EXTRAPOLATION" if self.is_extrapolation else "")
            + (
                "  HUMAN REVIEW REQUIRED"
                if self.human_review_required
                else ""
            )
        )
```

### 6.2 Confidence tiers must be assigned honestly

```python
def assign_confidence_tier(
    design_parameters: dict,
    calibrated_ranges: dict,
) -> tuple[str, bool]:
    """
    Assign a confidence tier to a prediction based on whether
    the design parameters fall within calibrated ranges.
    Returns the tier name and whether extrapolation is occurring.

    Tiers:
    - validated: direct experimental data for this exact design
    - interpolated: design lies between calibrated data points
    - extrapolated: design lies outside calibrated range but
      within the same mechanism and chassis
    - hypothesis_only: design changes mechanism, chassis, or
      assay format beyond any calibrated system
    """
    if is_exact_match(design_parameters, calibrated_ranges):
        return "validated", False
    if is_within_calibrated_range(design_parameters, calibrated_ranges):
        return "interpolated", False
    if is_same_mechanism_and_chassis(design_parameters, calibrated_ranges):
        return "extrapolated", True
    return "hypothesis_only", True
```

### 6.3 Scientific invariants must be tested

Write tests that verify physical and biological constraints, not just code execution. These are the most important tests in a biological software project.

Template for a scientific invariant test:

```python
def test_[invariant_name]():
    """
    [State the physical or biological law being tested.]
    Scientific basis: [cite the principle or paper].
    Failure mode: [what it means if this test fails].
    """
    # Arrange
    # [set up the test conditions]

    # Act
    result = ...  # call the function

    # Assert
    assert condition, (
        f"[Describe what went wrong in biological terms]. "
        f"Expected [X], got [Y]. "
        f"This violates [the physical or biological principle]. "
        f"Check [the most likely cause of failure]."
    )
```

### 6.4 Model fitting must report identifiability

```python
def fit_model_with_identifiability_check(
    model_func,
    parameters: list[str],
    data: dict,
    bounds: dict,
) -> FittingResult:
    """
    Fit a model to experimental data and check whether
    all parameters are identifiable from the available data.

    A parameter is non-identifiable if its value cannot be
    uniquely determined from the data — for example, if two
    parameters always appear as a product and cannot be
    separated.

    Non-identifiable parameters must be reported explicitly.
    They must not be presented as fitted values.
    """
    fitted_values, covariance = fit(model_func, data, bounds)
    parameter_uncertainties = extract_uncertainties(covariance)
    non_identifiable = [
        param
        for param, uncertainty in zip(parameters, parameter_uncertainties)
        if uncertainty > IDENTIFIABILITY_THRESHOLD or not is_finite(uncertainty)
    ]
    if non_identifiable:
        warnings.warn(
            f"The following parameters cannot be uniquely "
            f"determined from the available data: "
            f"{non_identifiable}. "
            f"These parameters should be fixed at literature "
            f"values or their uncertainty should be reported "
            f"as 'not identifiable from current data'.",
            UserWarning,
            stacklevel=2,
        )
    return FittingResult(
        fitted_values=fitted_values,
        uncertainties=parameter_uncertainties,
        non_identifiable_parameters=non_identifiable,
        data_points_used=len(data),
        degrees_of_freedom=len(data) - len(parameters),
    )
```

---

## 7. Evidence and retrieval rules

### 7.1 Never answer a biological question from training memory

When a retrieval system is available, always use it. Do not use training-data knowledge to answer biological questions, even if you are confident in the answer. Training-data knowledge cannot be cited, audited, or updated.

```python
def answer_biological_question(
    query: str,
    retrieval_system,
    allow_memory_fallback: bool = False,
) -> AnswerResult:
    """
    Answer a biological question using the retrieval system.
    Never use model training memory as the primary source.

    Parameters
    ----------
    allow_memory_fallback : bool
        If True, the model may use training memory when
        retrieval confidence is very low, but must clearly
        label the answer as coming from model memory and
        require human verification.
        Default is False. Only set to True for non-critical
        background context questions.
    """
    retrieved = retrieval_system.retrieve(query)
    confidence = retrieval_system.compute_confidence(retrieved)

    if confidence < MINIMUM_RETRIEVAL_CONFIDENCE:
        if allow_memory_fallback:
            return AnswerResult(
                answer=generate_from_memory(query),
                source="model_training_memory",
                confidence=confidence,
                human_review_required=True,
                warning=(
                    "This answer was generated from model "
                    "training memory because retrieval "
                    "confidence was insufficient. It has not "
                    "been verified against primary sources. "
                    "Do not use this answer to make a wet-lab "
                    "decision without human verification."
                ),
            )
        return AnswerResult(
            answer=(
                "Insufficient evidence in the retrieval corpus "
                "to answer this question reliably. "
                "Human literature review is required."
            ),
            source="none",
            confidence=confidence,
            human_review_required=True,
        )

    return generate_from_retrieved_context(query, retrieved)
```

### 7.2 Citations must be attached programmatically

```python
def attach_citations(
    answer_text: str,
    retrieved_passages: list[dict],
) -> CitedAnswer:
    """
    Attach citations to an answer programmatically from
    retrieved source records.
    The language model must not write citations.
    Citations are facts about sources, not generated text.
    A hallucinated citation is worse than no citation because
    it creates false confidence in an unsupported claim.
    """
    citations = []
    for passage in retrieved_passages:
        citations.append(
            {
                "source_id": passage["source_id"],
                "title": passage["title"],
                "authors": passage["authors"],
                "year": passage["year"],
                "doi": passage.get("doi"),
                "source_type": passage["source_type"],
                "peer_reviewed": passage["peer_reviewed"],
                "extracted_passage": passage["text"],
                "relevance_score": passage["score"],
            }
        )
    return CitedAnswer(
        text=answer_text,
        citations=citations,
        all_citations_from_retrieval=True,
        no_memory_citations=True,
    )
```

### 7.3 Separate evidence types in every answer

Every answer to a biological question must explicitly separate:

```python
class StructuredBiologicalAnswer(BaseModel):
    direct_evidence: str
    # What the retrieved sources explicitly state.
    # Must be directly traceable to a citation.

    model_inference: str
    # What can be reasonably inferred from the sources.
    # Must be clearly labelled as inference, not fact.

    engineering_recommendation: str
    # What a designer might consider based on the evidence.
    # Must be clearly labelled as a recommendation.

    unknown: str
    # What cannot be answered from the current corpus.
    # Must explicitly state what information is missing.

    citations: list[dict]
    confidence: str
    human_review_required: bool
    human_review_reason: str | None
```

---

## 8. Data integrity rules

### 8.1 Raw data must never be overwritten

```python
import shutil
from pathlib import Path
from datetime import datetime


def safe_write_experimental_data(
    data: dict,
    filepath: Path,
    overwrite: bool = False,
) -> Path:
    """
    Write experimental data safely.
    Raw experimental data is immutable once recorded.
    If a file already exists, create a versioned backup
    before writing. Never silently overwrite.
    """
    if filepath.exists() and not overwrite:
        raise DataOverwriteError(
            f"File '{filepath}' already exists. "
            f"Raw experimental data must not be overwritten. "
            f"If you need to correct an error, create a new "
            f"versioned file and document the correction."
        )

    if filepath.exists() and overwrite:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath.with_suffix(
            f".backup_{timestamp}{filepath.suffix}"
        )
        shutil.copy2(filepath, backup_path)
        print(
            f"Backup created at '{backup_path}' before "
            f"overwriting '{filepath}'."
        )

    write_with_checksum(data, filepath)
    return filepath
```

### 8.2 Every dataset must carry metadata

```python
from pydantic import BaseModel
from typing import Any


class ExperimentalDataset(BaseModel):
    dataset_id: str
    version: str
    created_date: str
    operator: str
    construct_ids: list[str]
    chassis: str
    experimental_conditions: dict[str, Any]
    instrument: str
    instrument_settings: dict[str, Any]
    normalization_method: str
    blank_correction_applied: bool
    negative_controls: list[str]
    positive_controls: list[str]
    replicates: int
    raw_data_checksum: str
    approved_for_model_training: bool
    approved_by: str | None
    approval_date: str | None
    known_issues: list[str]
    notes: str
```

### 8.3 Units must be explicit and consistent

```python
from enum import Enum


class ConcentrationUnit(Enum):
    MOLAR = "M"
    MILLIMOLAR = "mM"
    MICROMOLAR = "uM"
    NANOMOLAR = "nM"
    PICOMOLAR = "pM"


class TimeUnit(Enum):
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"


class LengthUnit(Enum):
    METERS = "m"
    NANOMETERS = "nm"
    ANGSTROMS = "A"


class SignalUnit(Enum):
    RLU = "RLU"
    FMOL_LUCIFERASE = "fmol_luciferase"
    NORMALIZED_RLU = "nRLU"
    ARBITRARY_UNITS = "AU"


def convert_concentration(
    value: float,
    from_unit: ConcentrationUnit,
    to_unit: ConcentrationUnit,
) -> float:
    """
    Convert between concentration units explicitly.
    Never perform unit conversion silently.
    Always log the conversion in the calling function.

    Conversion factors relative to Molar:
    M = 1, mM = 1e-3, uM = 1e-6, nM = 1e-9, pM = 1e-12
    """
    to_molar = {
        ConcentrationUnit.MOLAR: 1.0,
        ConcentrationUnit.MILLIMOLAR: 1e-3,
        ConcentrationUnit.MICROMOLAR: 1e-6,
        ConcentrationUnit.NANOMOLAR: 1e-9,
        ConcentrationUnit.PICOMOLAR: 1e-12,
    }
    value_in_molar = value * to_molar[from_unit]
    return value_in_molar / to_molar[to_unit]


def assert_units_match(
    value_a: float,
    unit_a: str,
    value_b: float,
    unit_b: str,
    operation: str,
) -> None:
    """
    Assert that two values have compatible units before
    performing an arithmetic operation.
    Unit mismatches are one of the most common and most
    dangerous silent errors in biological software.
    """
    if unit_a != unit_b:
        raise UnitMismatchError(
            f"Cannot perform '{operation}' on values with "
            f"different units: {unit_a} and {unit_b}. "
            f"Convert to a common unit before proceeding. "
            f"Values: {value_a} {unit_a} and {value_b} {unit_b}."
        )
```

---

## 9. Verification layer templates

Every biological software project should implement layered verification before any design output is acted upon. Adapt the specific checks to your project's biology.

### 9.1 Layer 1: Sequence integrity

```python
def verify_sequence_integrity(
    sequence: str,
    sequence_id: str,
    expected_length: int | None = None,
    expected_protein: str | None = None,
) -> VerificationLayerResult:
    """
    Layer 1: Verify that a sequence is internally consistent.

    Checks:
    - Valid nucleotide alphabet
    - Length consistency
    - No internal stop codons
    - Correct reading frame
    - Translation matches expected protein
    - Sequence checksum
    """
    checks = []
    valid_bases = set("ATCGatcgNn")
    invalid = [c for c in sequence if c not in valid_bases]
    checks.append(
        Check(
            name="valid_alphabet",
            passed=len(invalid) == 0,
            message=(
                f"Invalid characters found: {set(invalid)}"
                if invalid
                else "Valid nucleotide alphabet."
            ),
        )
    )

    if expected_length:
        checks.append(
            Check(
                name="length_check",
                passed=len(sequence) == expected_length,
                message=(
                    f"Length {len(sequence)} does not match "
                    f"expected {expected_length}."
                    if len(sequence) != expected_length
                    else f"Length {len(sequence)} correct."
                ),
            )
        )

    frame_result = verify_reading_frame(
        sequence, expected_protein, sequence_id
    )
    checks.append(
        Check(
            name="reading_frame",
            passed=frame_result.valid,
            message=frame_result.error or "Reading frame valid.",
        )
    )

    site_result = check_forbidden_sites(sequence, sequence_id=sequence_id)
    checks.append(
        Check(
            name="forbidden_sites",
            passed=site_result.passed,
            message=(
                f"Forbidden sites found: {site_result.found_sites}"
                if not site_result.passed
                else "No forbidden sites detected."
            ),
        )
    )

    return VerificationLayerResult(
        layer=1,
        layer_name="sequence_integrity",
        checks=checks,
        passed=all(c.passed for c in checks),
        checksum=compute_sequence_checksum(sequence),
    )
```

### 9.2 Layer 2: Biological plausibility

```python
def verify_biological_plausibility(
    design_spec: dict,
    parameter_library: dict,
) -> VerificationLayerResult:
    """
    Layer 2: Verify that the design is biologically plausible.

    Checks:
    - All parameters have cited sources
    - Parameter values are within known biological ranges
    - No contradictory design elements
    - Chassis compatibility
    - Expression context consistency

    These are warnings, not hard failures.
    A biologically implausible design may still be worth
    testing, but the implausibility must be visible.
    """
    checks = []
    for param_name, param_value in design_spec.items():
        if param_name in parameter_library:
            param_def = parameter_library[param_name]
            in_range = param_def.is_within_range(param_value)
            checks.append(
                Check(
                    name=f"range_check_{param_name}",
                    passed=in_range,
                    severity="warning" if not in_range else "pass",
                    message=(
                        f"{param_name}={param_value} "
                        f"{param_def.units} is outside the "
                        f"validated range "
                        f"[{param_def.lower_bound}, "
                        f"{param_def.upper_bound}]. "
                        f"This is an extrapolation."
                        if not in_range
                        else f"{param_name} within validated range."
                    ),
                )
            )

    return VerificationLayerResult(
        layer=2,
        layer_name="biological_plausibility",
        checks=checks,
        passed=not any(c.severity == "error" for c in checks),
    )
```

### 9.3 Layer 3: Model consistency

```python
def verify_model_consistency(
    prediction: PredictionResult,
    design_spec: dict,
) -> VerificationLayerResult:
    """
    Layer 3: Verify that the model output is internally
    consistent and physically meaningful.

    Checks:
    - Predicted values are physically possible
    - Units are consistent throughout
    - Uncertainty interval is non-negative
    - Confidence tier matches extrapolation status
    - All required parameters were available
    - Model version is recorded
    """
    checks = []
    checks.append(
        Check(
            name="positive_prediction",
            passed=prediction.predicted_value >= 0,
            message=(
                f"Predicted value {prediction.predicted_value} "
                f"is negative. Physical quantities cannot be "
                f"negative. Check model equations."
                if prediction.predicted_value < 0
                else "Predicted value is non-negative."
            ),
        )
    )

    interval_width = (
        prediction.uncertainty_95_upper - prediction.uncertainty_95_lower
    )
    checks.append(
        Check(
            name="valid_uncertainty_interval",
            passed=interval_width >= 0,
            message=(
                f"Uncertainty interval is inverted: "
                f"[{prediction.uncertainty_95_lower}, "
                f"{prediction.uncertainty_95_upper}]. "
                f"Lower bound must be less than upper bound."
                if interval_width < 0
                else "Uncertainty interval is valid."
            ),
        )
    )

    tier_extrapolation_consistent = (
        prediction.confidence_tier in ["extrapolated", "hypothesis_only"]
    ) == prediction.is_extrapolation
    checks.append(
        Check(
            name="tier_extrapolation_consistency",
            passed=tier_extrapolation_consistent,
            message=(
                "Confidence tier and extrapolation flag are "
                "inconsistent. A prediction cannot be labelled "
                "'interpolated' while also flagged as an "
                "extrapolation."
                if not tier_extrapolation_consistent
                else "Confidence tier and extrapolation flag consistent."
            ),
        )
    )

    checks.append(
        Check(
            name="model_version_recorded",
            passed=bool(prediction.model_version),
            message=(
                "Model version is not recorded. Every prediction "
                "must be traceable to a specific model version."
                if not prediction.model_version
                else f"Model version: {prediction.model_version}."
            ),
        )
    )

    return VerificationLayerResult(
        layer=3,
        layer_name="model_consistency",
        checks=checks,
        passed=all(c.passed for c in checks),
    )
```

### 9.4 Layer 4: Safety and biosecurity

```python
def verify_safety_and_biosecurity(
    design_spec: dict,
    parts_library: dict,
    biosecurity_blocklist: set,
) -> VerificationLayerResult:
    """
    Layer 4: Verify that the design does not contain
    biosecurity-sensitive components and that all parts
    are from the validated allowlist.

    This layer must never be bypassed.
    A failed biosecurity check must halt all downstream
    processing including sequence export.
    """
    checks = []
    for part_id in design_spec.get("part_ids", []):
        in_allowlist = part_id in parts_library
        checks.append(
            Check(
                name=f"allowlist_check_{part_id}",
                passed=in_allowlist,
                severity="error" if not in_allowlist else "pass",
                message=(
                    f"Part '{part_id}' is not in the validated "
                    f"parts library. Designs containing unvalidated "
                    f"parts cannot be exported."
                    if not in_allowlist
                    else f"Part '{part_id}' is validated."
                ),
            )
        )

        on_blocklist = part_id in biosecurity_blocklist
        checks.append(
            Check(
                name=f"blocklist_check_{part_id}",
                passed=not on_blocklist,
                severity="error" if on_blocklist else "pass",
                message=(
                    f"Part '{part_id}' is on the biosecurity "
                    f"blocklist. This design cannot be processed."
                    if on_blocklist
                    else f"Part '{part_id}' not on blocklist."
                ),
            )
        )

    return VerificationLayerResult(
        layer=4,
        layer_name="safety_and_biosecurity",
        checks=checks,
        passed=not any(c.severity == "error" for c in checks),
        blocks_export=any(c.severity == "error" for c in checks),
    )
```

### 9.5 Layer 5: Reproducibility

```python
def verify_reproducibility(
    design_spec: dict,
    prediction: PredictionResult,
    dataset: ExperimentalDataset | None,
) -> VerificationLayerResult:
    """
    Layer 5: Verify that the design and prediction are
    reproducible from the recorded information alone.

    A result is reproducible if a third party could
    regenerate it from the recorded inputs, model version,
    dataset version, and parameter sources without
    contacting the original authors.

    Checks:
    - All inputs are recorded
    - Model version is pinned
    - Dataset version is pinned
    - Parameter sources are cited
    - Random seeds are recorded where applicable
    - No external dependencies that could change
    """
    checks = []
    checks.append(
        Check(
            name="model_version_pinned",
            passed=bool(prediction.model_version),
            message=(
                "Model version is not pinned. Results cannot "
                "be reproduced without knowing which model "
                "version was used."
                if not prediction.model_version
                else f"Model version pinned: {prediction.model_version}."
            ),
        )
    )
    checks.append(
        Check(
            name="parameter_sources_cited",
            passed=len(prediction.parameter_sources) > 0,
            message=(
                "No parameter sources are recorded. Results "
                "cannot be reproduced without knowing which "
                "parameter values were used and where they "
                "came from."
                if not prediction.parameter_sources
                else (
                    f"{len(prediction.parameter_sources)} "
                    f"parameter sources recorded."
                )
            ),
        )
    )

    if dataset:
        checks.append(
            Check(
                name="dataset_version_pinned",
                passed=bool(dataset.version),
                message=(
                    "Dataset version is not pinned."
                    if not dataset.version
                    else f"Dataset version: {dataset.version}."
                ),
            )
        )
        checks.append(
            Check(
                name="dataset_approved_for_use",
                passed=dataset.approved_for_model_training,
                message=(
                    "Dataset has not been approved for model "
                    "training. Only approved datasets may be "
                    "used to calibrate production models."
                    if not dataset.approved_for_model_training
                    else "Dataset approved for use."
                ),
            )
        )

    return VerificationLayerResult(
        layer=5,
        layer_name="reproducibility",
        checks=checks,
        passed=all(c.passed for c in checks),
    )
```

---

## 10. Testing standards

### 10.1 Test categories and their purposes

```text
tests/unit/
  Test individual functions in isolation.
  Every public function must have at least one unit test.
  Unit tests verify execution, not scientific correctness.

tests/scientific/
  Test physical and biological invariants.
  These are the most important tests in the project.
  Scientific tests verify that the code obeys known laws.

tests/golden/
  Test that known inputs produce known outputs exactly.
  Golden tests catch regressions in deterministic functions.
  Every sequence compilation function must have golden tests.

tests/integration/
  Test that modules work together correctly.
  Integration tests verify the interfaces between modules.

tests/adversarial/
  Test that the system handles invalid inputs correctly.
  Adversarial tests verify that safety checks work.
```

### 10.2 Golden test template for sequence functions

```python
import pytest
from pathlib import Path
import json

GOLDEN_OUTPUTS_DIR = Path("tests/golden/outputs")


def test_sequence_compilation_golden(compiler, design_spec_fixture):
    """
    Golden test: verify that sequence compilation produces
    exactly the expected output for a known input.

    If this test fails, either:
    1. The compiler has a bug (fix the compiler)
    2. The design spec has changed (update the golden file
       and document why)
    3. The parts library has changed (update the golden file
       and document why)

    Never update a golden file without understanding why
    the output changed.
    """
    result = compiler.compile(design_spec_fixture)
    golden_path = (
        GOLDEN_OUTPUTS_DIR / f"{design_spec_fixture.design_id}_golden.json"
    )

    if not golden_path.exists():
        golden_path.write_text(json.dumps(result.dict(), indent=2))
        pytest.skip(
            f"Golden file created at {golden_path}. "
            f"Run the test again to verify."
        )

    golden = json.loads(golden_path.read_text())
    assert result.sequence == golden["sequence"], (
        f"Sequence changed. "
        f"Expected checksum: {golden['checksum']}. "
        f"Got checksum: {result.checksum}. "
        f"Diff: {compute_diff(golden['sequence'], result.sequence)}. "
        f"If this change is intentional, update the golden "
        f"file and document the reason in the commit message."
    )
    assert result.checksum == golden["checksum"], (
        "Checksum mismatch. Sequence may have changed silently."
    )
```

### 10.3 Adversarial test template

```python
import pytest


@pytest.mark.parametrize(
    "invalid_input,expected_error",
    [
        (
            {"calcium_uM": -1.0},
            "Calcium concentration cannot be negative",
        ),
        (
            {"repeat_count": 0},
            "Scaffold must have at least one repeat",
        ),
        (
            {"part_id": "UNVALIDATED_PART_XYZ"},
            "not in the validated parts library",
        ),
        (
            {"sequence": "ATCG" * 1000 + "GAATTC"},
            "Forbidden site EcoRI detected",
        ),
        (
            {"chassis": "unknown_organism"},
            "Chassis not supported",
        ),
    ],
)
def test_invalid_inputs_are_rejected(
    system_under_test,
    invalid_input,
    expected_error,
):
    """
    Adversarial test: verify that invalid inputs are
    rejected with informative error messages.

    A system that accepts invalid inputs silently is
    more dangerous than one that crashes loudly.
    """
    with pytest.raises(Exception) as exc_info:
        system_under_test.process(invalid_input)
    assert expected_error.lower() in str(exc_info.value).lower(), (
        f"Expected error message containing '{expected_error}' "
        f"but got: '{exc_info.value}'"
    )
```

---

## 11. Documentation standards

### 11.1 Every module must have a README

Each module directory must contain a `README.md` with:

```markdown
# [Module Name]

## Purpose
[One paragraph describing what this module does and why.]

## Scientific basis
[The biological or physical principles this module implements.
Include citations for key equations or assumptions.]

## Inputs
[What the module accepts. Include types and units.]

## Outputs
[What the module returns. Include types and units.]

## Assumptions
[Explicit list of assumptions the module makes.
These are the conditions under which the module is valid.]

## Known limitations
[What the module cannot do or where it may fail.]

## Parameter sources
[Where the biological constants used in this module
come from. Include DOIs.]

## Tests
[How to run the tests for this module.]

## Owner
[Who is responsible for this module.]
```

### 11.2 Changelog entries for biological changes

Every change to a biological constant, model equation, sequence, or verification rule must have a changelog entry:

```markdown
## [Version] — [Date]

### Changed
- [Parameter name]: changed from [old value][units] to [new value][units].
  Reason: [why the value changed].
  Old source: [citation].
  New source: [citation].
  Impact: [what predictions or outputs this affects].
  Reviewed by: [name].
```

---

## 12. Pull request checklist

Before opening a pull request, confirm all of the following:

### Code quality

- [ ] `ruff format` passes with no changes
- [ ] `ruff check` passes with no warnings
- [ ] `mypy --strict` passes with no errors
- [ ] All new functions have docstrings
- [ ] All new modules have README files

### Tests

- [ ] `pytest tests/unit/` passes
- [ ] `pytest tests/scientific/` passes
- [ ] `pytest tests/golden/` passes
- [ ] `pytest tests/integration/` passes
- [ ] New scientific invariant tests added for new biology
- [ ] New golden tests added for new sequence functions
- [ ] New adversarial tests added for new safety checks

### Biological correctness

- [ ] All new biological constants have cited sources
- [ ] All new sequences have been translated and verified
- [ ] All new sequences have been checked for forbidden sites
- [ ] No sequences were generated by a language model
- [ ] No citations were generated by a language model
- [ ] All predictions return uncertainty intervals
- [ ] All predictions return confidence tiers

### Safety

- [ ] No verification layers were removed or weakened
- [ ] No biosecurity filters were modified without approval
- [ ] No parts were added to the allowlist without review
- [ ] No sequences were silently modified

### Reproducibility

- [ ] Model version is recorded in all prediction outputs
- [ ] Dataset version is recorded where applicable
- [ ] Parameter sources are cited in all new constants
- [ ] Random seeds are recorded where applicable

### Documentation

- [ ] `CHANGELOG.md` updated for biological changes
- [ ] `interfaces.md` updated if public API changed
- [ ] README updated if module behavior changed

---

## 13. Fallback hierarchy

When a component fails, degrade gracefully rather than producing a wrong answer confidently.

```python
class FallbackHierarchy:
    """
    When a component fails, use the next available fallback.
    Never produce a confident wrong answer.
    Always prefer an honest failure over a silent error.

    Level 1: Full system — all components operational.
    Level 2: Retrieval only — LLM synthesis unavailable.
             Return retrieved passages without synthesis.
    Level 3: Keyword search only — vector search unavailable.
             Return keyword-matched passages.
    Level 4: Static reference — all retrieval unavailable.
             Return a pointer to the relevant documentation.
    Level 5: Explicit failure — nothing available.
             Return an honest error with recovery instructions.
    """

    @staticmethod
    def handle_llm_failure(query: str, retrieved_passages: list[dict]) -> dict:
        if retrieved_passages:
            return {
                "answer": (
                    "The language model is currently unavailable. "
                    "Here are the most relevant retrieved passages:"
                ),
                "passages": retrieved_passages,
                "fallback_level": 2,
                "human_review_required": True,
            }
        return {
            "answer": (
                "Both the language model and retrieval system "
                "are currently unavailable. "
                "Please consult the documentation directly or "
                "perform a manual literature search."
            ),
            "fallback_level": 5,
            "human_review_required": True,
        }

    @staticmethod
    def handle_model_failure(
        design_spec: dict,
        known_good_designs: list[dict],
    ) -> dict:
        """
        When the predictive model fails or has insufficient
        data, return the closest known-good design rather
        than an uncertain prediction.
        """
        closest = find_closest_known_good(design_spec, known_good_designs)
        return {
            "prediction": None,
            "fallback": closest,
            "fallback_level": 3,
            "message": (
                "The predictive model has insufficient data "
                "for this design. The closest validated design "
                "is returned as a reference. Do not treat this "
                "as a prediction for the requested design."
            ),
            "human_review_required": True,
        }
```

---

## 14. The skills-preservation principle

AI coding agents can produce working code faster than a human can understand it. This creates a risk: the human loses the ability to explain, debug, or modify the code they nominally own.

In a biological software context, this is dangerous. If a student cannot explain why a model equation is correct, they cannot catch it when it is wrong.

You must therefore follow the skills-preservation principle:

> **Never produce code that the assigned developer cannot explain, defend, and modify independently.**

In practice, this means:

- Explain every non-obvious implementation choice
- Do not use advanced patterns without explaining them
- When asked to implement a mathematical model, show the equation first and ask for confirmation before coding it
- When implementing a biological rule, cite the source and ask the developer to confirm they understand it
- Write code that is readable over code that is clever
- Prefer explicit over implicit
- Prefer simple over sophisticated when both are correct

If a developer asks you to implement something they do not understand, explain it first. Do not implement it silently.

A developer who cannot explain their own code is a liability in a wet-lab context where code influences physical experiments.

---

## 15. ORIGAMI / CLASP project invariants

This repository implements **ORIGAMI**, the design engine for **CLASP**.  
Authoritative narrative and architecture live in [`CLASP Docs.md`](CLASP%20Docs.md).  
If code and docs disagree on a physical constant, **stop and ask a human** before changing either.

### 15.1 Shared physical engine (do not invent replacements)

| Quantity | Canonical value / rule | Code home |
|----------|------------------------|-----------|
| CTPR rise per repeat | **1.1 nm** | `src/core/ctpr_geometry.py` |
| CTPR twist per repeat | **~20°** | `src/core/ctpr_geometry.py` |
| Docking position indexing | **1-based** repeats in `[1, N]` | `ScaffoldSpec` / `ctpr_geometry.py` |
| Persistence length | **15 nm** (rigid-rod approx. for short scaffolds) | `src/core/ctpr_geometry.py` |
| Scaffold cylinder radius | **1.8 nm** | `src/core/steric_checker.py` |
| CaM–M13 Kd (Ca²⁺-saturated) | **~1×10⁻⁷ M** | `src/core/calcium_kinetics.py` |
| CaM–Ca²⁺ Hill n | **~4** | `src/core/calcium_kinetics.py` |
| CaM–Ca²⁺ EC50 | **~2 µM** free Ca²⁺ | `src/core/calcium_kinetics.py` |
| NanoBiT reconstitution distance | **≤ 3.0 nm** | `src/core/nanobit_reporter.py` |
| NanoBiT intrinsic Kd | **~190 µM** | `src/core/nanobit_reporter.py` |
| (GGGGS)n residue contour | **~0.36 nm / residue** | `src/core/linker_ensemble.py` |
| (GGGGS)n Kuhn length | **~0.7 nm** | `src/core/linker_ensemble.py` |

Do **not** silently change these constants to make a demo plot look better.

### 15.2 Mechanism Profile Standard

New proximity functions are added only as complete packages under `src/profiles/`:

- Biological objective, payload roles, governing equations  
- Parameter schema + provenance  
- Mandatory controls and required measurements  
- Failure / refusal conditions  
- Evidence-maturity thresholds (Tier 1 / 2 / 3 — never a single “validated” stamp)

A new LLM prompt is **not** a new profile.

Registered MVP profiles:

1. `trehalose_synthesis` → intermediate transfer  
2. `target_complementation` → target-induced complementation (screening assay, **not** clinical diagnostic)  
3. `redox_transfer` → relative electron-transfer ranking (no absolute H₂ claims without calibration)  
4. `covalent_capture` → SpyTag / SpyCatcher locking  

### 15.3 Modes and honesty rules

- **Explore** must refuse with *Insufficient evidence for a reliable recommendation* when confidence is too low.  
- **Design** must surface uncertainty and evidence maturity on the Proximity Design Passport.  
- **Learn** must compare prediction vs observation; it must not overwrite Tier-1 data with a silent hallucinated “correction.”  
- Never fabricate wet-lab results, citations, DOIs, or sequence deposits.

### 15.4 Biosecurity / compiler gates

- Every compiled `part_id` must appear in `src/compiler/approved_parts.json`.  
- Large ORFs may be allowlisted by ID + provenance until checksummed DNA is deposited — **do not invent gene sequences**.  
- Reject solo **pET28a+** as the sole scaffold+payload expression strategy (`src/compiler/expression_vector.py`).  
- Do not add synthesis ordering, autonomous lab control, or open-ended payload generation without an explicit human decision and biosecurity review.

### 15.5 Testing expectations for this repo

Before merging ORIGAMI changes that touch biology or numerics:

```bash
pytest
```

Required classes of tests:

- Unit tests for schemas, MoClo overhangs, ODE mass conservation, verification  
- Physical invariant tests (non-negative concentrations, etc.)  
- Profile / mode / allowlist smoke tests (`tests/unit_tests/test_profiles_modes_compiler.py`)

CI configuration: [`.gitlab-ci.yml`](.gitlab-ci.yml) (pytest on Python 3.12).
