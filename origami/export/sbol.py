"""Minimal SBOL 3 XML for a protein Component plus Sequence.

This is interchange XML, not a SynBioHub upload.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from origami.export.constructs import ConstructError, construct_for_n


def sbol3_protein_xml(
    sequence: str,
    *,
    display_id: str,
    name: str,
    description: str,
) -> str:
    seq = sequence.upper().strip()
    if not seq:
        raise ConstructError("sequence is empty")
    if not display_id.replace("_", "").isalnum():
        raise ConstructError("display_id must be alphanumeric")
    uri = f"https://github.com/cedricwong0714/origami/{display_id}"
    seq_uri = f"{uri}_seq"
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:sbol="http://sbols.org/v3#" '
        'xmlns:dcterms="http://purl.org/dc/terms/">\n'
        f'  <sbol:Component rdf:about="{escape(uri)}">\n'
        f"    <sbol:displayId>{escape(display_id)}</sbol:displayId>\n"
        f"    <sbol:name>{escape(name)}</sbol:name>\n"
        f"    <sbol:description>{escape(description)}</sbol:description>\n"
        "    <sbol:type rdf:resource=\"https://identifiers.org/SBO:0000252\"/>\n"
        "    <sbol:role rdf:resource=\"https://identifiers.org/SO:0000417\"/>\n"
        f'    <sbol:hasSequence rdf:resource="{escape(seq_uri)}"/>\n'
        "  </sbol:Component>\n"
        f'  <sbol:Sequence rdf:about="{escape(seq_uri)}">\n'
        f"    <sbol:displayId>{escape(display_id)}_seq</sbol:displayId>\n"
        "    <sbol:encoding rdf:resource=\"https://identifiers.org/edam:format_1929\"/>\n"
        f"    <sbol:elements>{escape(seq)}</sbol:elements>\n"
        "  </sbol:Sequence>\n"
        "</rdf:RDF>\n"
    )


def sbol_for_n(n_repeats: int) -> str:
    row = construct_for_n(n_repeats)
    return sbol3_protein_xml(
        row["sequence"],
        display_id=f"CTPR_n{n_repeats}",
        name=str(row["construct_id"]),
        description=(
            f"Team-supplied amino acids, n={n_repeats}. "
            f"sha256={row['sequence_sha256']}. calibrated=false."
        ),
    )
