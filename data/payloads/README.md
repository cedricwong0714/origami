# Payload records

Paste your own protein sequences and construct masses here as JSON arrays
accepted by `origami.io.payloads.load_payloads`.

Required on every row: `payload_id`, `role`, `fusion_terminus`,
`repeat_index`, `radius_A`, `linker_sigma_A`.

Optional: `protein_sequence`, `mw_Da` with `mw_source`. Mass is stored as
typed. Erickson Rmin is computed only as a comparison. It does not replace
`radius_A`.

Do not commit generated ORF sequences. OtsA and OtsB remain allowlisted by
ID until a team deposit is checksummed.
