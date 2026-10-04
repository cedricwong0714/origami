"""Write a protein GenBank record from a caller amino-acid string.

This is not a compiled DNA construct. There is no codon table here.
"""

from __future__ import annotations

from origami.export.constructs import ConstructError, construct_for_n


def _wrap_origin(sequence: str) -> str:
    seq = sequence.upper().replace(" ", "")
    lines = []
    for i in range(0, len(seq), 60):
        chunk = seq[i : i + 60]
        groups = " ".join(chunk[j : j + 10] for j in range(0, len(chunk), 10))
        lines.append(f"{i + 1:>9} {groups}")
    return "\n".join(lines)


def protein_genbank(
    sequence: str,
    *,
    locus: str,
    definition: str,
    note: str,
) -> str:
    seq = sequence.upper().strip()
    if not seq or any(c not in "ACDEFGHIKLMNPQRSTVWY" for c in seq):
        raise ConstructError("sequence must be amino acids A–Y (no BJOUXZ)")
    if not locus.replace("_", "").isalnum():
        raise ConstructError("locus must be alphanumeric")
    return (
        f"LOCUS       {locus[:16]:<16}{len(seq):>6} aa                    UNK 01-OCT-2026\n"
        f"DEFINITION  {definition}\n"
        "ACCESSION   .\n"
        "VERSION     .\n"
        "KEYWORDS    .\n"
        "SOURCE      .\n"
        "  ORGANISM  .\n"
        "COMMENT     Team-supplied protein. ORIGAMI did not generate this sequence.\n"
        "COMMENT     calibrated=false. Not a DNA GenBank file.\n"
        f"COMMENT     {note}\n"
        "FEATURES             Location/Qualifiers\n"
        f"     Protein         1..{len(seq)}\n"
        '                     /product="CLASP CTPR fusion (team sequence)"\n'
        "ORIGIN\n"
        f"{_wrap_origin(seq)}\n"
        "//\n"
    )


def genbank_for_n(n_repeats: int) -> str:
    row = construct_for_n(n_repeats)
    return protein_genbank(
        row["sequence"],
        locus=f"CTPRN{n_repeats}",
        definition=f"{row['construct_id']} n={n_repeats}",
        note=f"sha256={row['sequence_sha256']}",
    )
