# ORIGAMI architecture

```
team sequences / plates / CamSol (dry)
        |
        v
+------------------+     +---------------------------+
| Deterministic    |     | SSDK learner              |
| chassis          |     | sklearn Matérn residual   |
| structure        |     | five assay GPs            |
| Phillips Tm/ΔG   |     | multi-fidelity lum        |
| docking          |---->| next n (not averaged)     |
| kinetics         |     | chassis_at_next_n         |
+------------------+     +---------------------------+
        |                         |
        v                         v
   SBOL / GenBank / SBML     plate vs freeze report
   passport JSON             synthetic fixtures
```

Wet luminescence does not edit the screw or the Phillips curve.

Exports:

| Format | What it contains | What it is not |
|---|---|---|
| GenBank | Team amino acids | DNA, codon-optimized |
| SBOL 3 XML | Same protein Component | SynBioHub push |
| SBML L2 | Recruitment, Spy, or NanoBiT | A new custom ODE |
| Passport | Chassis snapshot + sequence checksum | A validation certificate |

`calibrated` stays false.
