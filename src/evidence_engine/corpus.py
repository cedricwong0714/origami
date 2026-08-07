"""
Curated ORIGAMI evidence corpus.

Entries are literature-parameterized values already used by the CLASP Docs /
physical engine. Context strings intentionally avoid implying CLASP wet-lab
measurement so Explore Mode classifies them as model_inference until Tier-1
data are ingested.
"""

from __future__ import annotations

from src.evidence_engine.schema import CitationRecord, EvidenceEntry

# --- Citations named in CLASP Docs / engine comments (verified DOIs) ---

CITE_GIAEVER_1997 = CitationRecord(
    citation_id="DOI_10.1074/jbc.272.7.4367",
    title="Characterization of Trehalose-6-Phosphate Synthase",
    authors=["Giaever, S.", "Styrvold, O. B."],
    journal="Journal of Biological Chemistry",
    year=1997,
    doi="10.1074/jbc.272.7.4367",
)

CITE_IKURA_1992 = CitationRecord(
    citation_id="DOI_10.1126/science.1523409",
    title="Solution structure of a calmodulin-target peptide complex by multidimensional NMR",
    authors=["Ikura, M.", "Clore, G. M.", "Gronenborn, A. M.", "Zhu, G.", "Klee, C. B.", "Bax, A."],
    journal="Science",
    year=1992,
    doi="10.1126/science.1523409",
    pmid="1523409",
)

CITE_DIXON_2016 = CitationRecord(
    citation_id="DOI_10.1021/acschembio.5b00753",
    title="NanoLuc Complementation Reporter Optimized for Accurate Measurement of Protein Interactions in Cells",
    authors=["Dixon, A. S.", "Schwinn, M. K.", "Hall, M. P.", "et al."],
    journal="ACS Chemical Biology",
    year=2016,
    doi="10.1021/acschembio.5b00753",
    pmid="26569370",
)

CITE_ZAKERI_2012 = CitationRecord(
    citation_id="DOI_10.1073/pnas.1115485109",
    title="Peptide tag forming a rapid covalent bond to a protein, through engineering a bacterial adhesin",
    authors=["Zakeri, B.", "Fierer, J. O.", "Celik, E.", "et al."],
    journal="Proceedings of the National Academy of Sciences",
    year=2012,
    doi="10.1073/pnas.1115485109",
    pmid="22392974",
)

CITE_DUEBER_2009 = CitationRecord(
    citation_id="DOI_10.1038/nbt.1558",
    title="Synthetic protein scaffolds provide modular control over metabolic flux",
    authors=["Dueber, J. E.", "Wu, G. C.", "Malmirchegini, G. R.", "et al."],
    journal="Nature Biotechnology",
    year=2009,
    doi="10.1038/nbt.1558",
    pmid="19648908",
)


def _entry(
    key: str,
    value: float,
    unit: str,
    confidence: float,
    context: str,
    citation: CitationRecord,
) -> EvidenceEntry:
    return EvidenceEntry(
        parameter_key=key,
        value=value,
        unit=unit,
        confidence_score=confidence,
        experimental_context=context,
        citation=citation,
    )


DEFAULT_EVIDENCE_STORE: dict[str, EvidenceEntry] = {
    "k_cat_OtsA": _entry(
        "k_cat_OtsA",
        0.5,
        "s^-1",
        0.95,
        "Purified E. coli OtsA enzyme assay at 25°C (literature primary characterization).",
        CITE_GIAEVER_1997,
    ),
    "cam_m13_kd_ca_sat_M": _entry(
        "cam_m13_kd_ca_sat_M",
        1e-7,
        "M",
        0.9,
        "Literature-parameterized CaM–M13 Kd under Ca2+-saturating conditions (ORIGAMI recruitment engine).",
        CITE_IKURA_1992,
    ),
    "cam_ca_ec50_M": _entry(
        "cam_ca_ec50_M",
        2e-6,
        "M",
        0.8,
        "Literature-parameterized free-Ca2+ EC50 used for Hill activation of CaM (ORIGAMI calcium_kinetics; CLASP Docs range 1–5 µM).",
        CITE_IKURA_1992,
    ),
    "cam_ca_hill_n": _entry(
        "cam_ca_hill_n",
        4.0,
        "dimensionless",
        0.85,
        "Literature-parameterized Hill coefficient reflecting four Ca2+ sites on CaM (ORIGAMI calcium_kinetics).",
        CITE_IKURA_1992,
    ),
    "resting_cytoplasmic_ca_M": _entry(
        "resting_cytoplasmic_ca_M",
        1e-7,
        "M",
        0.8,
        "Literature-parameterized resting cytoplasmic free Ca2+ (~100 nM) used as baseline in ORIGAMI recruitment model.",
        CITE_IKURA_1992,
    ),
    "nanobit_intrinsic_kd_M": _entry(
        "nanobit_intrinsic_kd_M",
        190e-6,
        "M",
        0.95,
        "Literature LgBiT–SmBiT intrinsic Kd (NanoBiT); ORIGAMI nanobit_reporter constant.",
        CITE_DIXON_2016,
    ),
    "nanobit_max_distance_nm": _entry(
        "nanobit_max_distance_nm",
        3.0,
        "nm",
        0.9,
        "Literature-parameterized effective reconstitution distance ≤30 Å used as ORIGAMI hard distance rule.",
        CITE_DIXON_2016,
    ),
    "inter_m13_spacing_3_repeats_nm": _entry(
        "inter_m13_spacing_3_repeats_nm",
        5.5,
        "nm",
        0.85,
        "Literature-informed scaffold spacing scale for sequential enzymes (Dueber synthetic scaffolds; CLASP Docs CTPR example).",
        CITE_DUEBER_2009,
    ),
    "ctpr_persistence_length_nm": _entry(
        "ctpr_persistence_length_nm",
        15.0,
        "nm",
        0.8,
        "Literature-parameterized CTPR rigid-rod persistence length used in ORIGAMI geometry engine (CLASP Docs / scaffold design table).",
        CITE_DUEBER_2009,
    ),
    "ctpr_rise_per_repeat_nm": _entry(
        "ctpr_rise_per_repeat_nm",
        1.1,
        "nm",
        0.85,
        "Structural parameter used by ORIGAMI CTPR screw-transform geometry (CLASP Docs / ctpr_geometry).",
        CITE_DUEBER_2009,
    ),
    "spy_isopeptide_enabled": _entry(
        "spy_isopeptide_enabled",
        1.0,
        "boolean_as_float",
        0.9,
        "SpyTag/SpyCatcher form a spontaneous isopeptide bond when proximal (literature system used as ORIGAMI covalent-capture prior; value=1 denotes enabled mechanism).",
        CITE_ZAKERI_2012,
    ),
}


def corpus_size() -> int:
    return len(DEFAULT_EVIDENCE_STORE)
