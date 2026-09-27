# Deposited CTPR coordinates

`ctpr_deposited_ca.json` holds C-alpha coordinates copied from the RCSB mmCIF files of PDB 2AVP, 2HYZ, and 2FO7. Those entries cite Kajander, Cortajarena, Mochrie, and Regan, Acta Crystallographica Section D 63:800–811 (2007), DOI 10.1107/S0907444907024353.

The article PDF is not open access. Nothing in the JSON is a sentence from that PDF. The numbers are atomic coordinates, rounded to 0.001 Å, grouped into the 34-residue repeat that the chain sequence actually repeats.

`origami.physical.deposited` refits each repeat onto the next one. The mean rise of that fit is the runtime axial rise. The twist used for coordinates stays 45° per repeat, which lies inside the deposited twist range and keeps eight repeats to a turn. The sample standard deviation of the fit is the rise and twist uncertainty. The scaffold radius is the mean repeat-centroid radius. The docking radius is the mean radial distance of the junction between C-alpha 34 and C-alpha 1 of the next block. Payload clash uses the mean C-alpha cloud of those repeats, placed on the runtime screw. `calibrated` stays false.
