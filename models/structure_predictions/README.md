# structure_predictions/

Place AlphaFold / ESMFold scripts and **small** processed summaries here.

- Do **not** commit full PDB/mmCIF libraries or large trajectory dumps.
- Upload heavy structure archives to Zenodo and record the DOI in this folder’s `zenodo_links.json` (create when you have one).
- Preferred layout per prediction job:

```
structure_predictions/
  <construct_id>/
    meta.json          # model version, date, sequence hash
    summary.json       # pLDDT stats, interface residues (small)
    # complex.pdb      # gitignored — keep local or on Zenodo
```
