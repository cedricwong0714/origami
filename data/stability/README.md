# CTPR thermal-stability literature

`ctpr_thermal_literature.json` holds primary experimental melting temperatures and unfolding free energies for consensus tetratricopeptide-repeat (CTPR / CTPRa) scaffolds. Every value was read from a paper page opened in this session. FoldX, CamSol, and Aggrescan outputs were not used.

`n_repeats` is the integer in the authors' construct name (CTPRa6 means six consensus repeats). It is not increased by a C-terminal solvating helix when a paper includes one. Phillips et al. (2012) sometimes draw that cap as half a repeat in Figure 3; the rows below keep the integer used in their Table I.

The file has 51 rows. `run_design` does not load this file by default. Passing the whole file as `thermal_table_path` raises, because several \(T_m\) series share repeat counts and must not be averaged. That series is the default stability prior: `thermal_series="phillips2012_ctpra_dsc"`, Phillips et al. 2012, DOI 10.1002/pro.2018, Table I (DSC column), CTPRa only, 50 mM phosphate, pH 7.0. The numbers were read from Table I, not from a plotted figure. CTPR rows in that table stay out. When the caller omits an assay temperature, designs are compared at 37 C, the chosen E. coli operating point, which is not a temperature from Table I. Pass `thermal_prior=False` to skip the gate. Other named Tm series, not mixed into the default, are `cortajarena2011_ctpra_dsc`, `phillips2012_ctpra_cd`, and `phillips2012_ctpr_dsc`. The default series also reports the same table's unfolding ΔG at 10°C (`kcal mol-1`, sign as printed). That ΔG does not decide pass or fail. Among lengths that already pass the steric gate and the Tm gate, the report names the one with the largest printed value in that column. The lookup does not change `next_n`. The Phillips CTPR DSC series has the same kind of companion column. Cortajarena 2011 has no ΔG column in this file, so `delta_g` stays empty for that series. Chemical-denaturation ΔG rows are not ranked. \(\Delta G\) signs are copied as printed and are not the pass/fail gate.

## Included papers

### Cortajarena and Regan, 2011

DOI: [10.1002/pro.564](https://doi.org/10.1002/pro.564)

Citation: Cortajarena AL, Regan L. Calorimetric study of a series of designed repeat proteins: modular structure and modular folding. Protein Sci. 2011;20(2):336-340.

Read from the PubMed Central HTML for PMC3048418, Table I (DSC columns). The buffer and pH are in the Figure 1 caption on the same page: 0.5 mg/mL protein, 150 mM NaCl, 50 mM phosphate, pH 6.8, MicroCal VP-Capillary DSC, 60°C/h. Table I does not print an uncertainty on Tm, so `uncertainty` is null.

| Construct | n | Tm (°C) | Where |
| --- | --- | --- | --- |
| CTPRa2 | 2 | 57.9 | Table I |
| CTPRa3 | 3 | 68.3 | Table I |
| CTPRa4 | 4 | 72.7 | Table I |
| CTPRa6 | 6 | 77.1 | Table I |
| CTPRa8 | 8 | 78.9 | Table I |
| CTPRa10 | 10 | 80.1 | Table I |

These are DSC midpoints. The CD column of the same table is an apparent van't Hoff enthalpy, not a Tm, and was not entered.

### Phillips, Javadi, Millership, and Main, 2012

DOI: [10.1002/pro.2018](https://doi.org/10.1002/pro.2018)

Citation: Phillips JJ, Javadi Y, Millership C, Main ERG. Modulation of the multistate folding of designed TPR proteins through intrinsic and extrinsic factors. Protein Sci. 2012;21(3):327-338.

Read from the PubMed Central HTML for PMC3375434, Table I. Thermal melts were at pH 7 in 50 mM phosphate (Results). Methods state 50 mM phosphate, pH 7.0. DSC used a MicroCal VP-DSC, 20 to 90°C, 1°C/min, 30–150 μM. CD melts followed ellipticity at 222 nm, 1–4 μM. The ΔG column header is an image; the image reads ΔG with subscript D-N and superscript H2O. The article text says this column is the model-independent unfolding free energy from the Gibbs–Helmholtz equation, extrapolated to 10°C, using ΔHcal, Tm, and ΔCp. Uncertainties are the mean spread of at least two experiments, except where footnote f says the fit error was larger (CTPRa4, CTPR2, and CTPR3 DSC Tm).

DSC Tm (model-independent numerical integration), Table I:

| Construct | n | Tm (°C) |
| --- | --- | --- |
| CTPRa2 | 2 | 53 ± 0.3 |
| CTPRa3 | 3 | 63 ± 0.6 |
| CTPRa4 | 4 | 68 ± 0.1 |
| CTPRa5 | 5 | 71 ± 0.1 |
| CTPRa6 | 6 | 71 ± 1.0 |
| CTPRa8 | 8 | 74 ± 0.5 |
| CTPRa10 | 10 | 74 ± 1.3 |
| CTPR2 | 2 | 68 ± 0.04 |
| CTPR3 | 3 | 76 ± 0.1 |

CD Tm, same table. Footnote g marks CTPRa8, CTPRa10, CTPR2, and CTPR3 as not calculated, so those cells were not entered.

| Construct | n | Tm (°C) |
| --- | --- | --- |
| CTPRa2 | 2 | 51 ± 0.2 |
| CTPRa3 | 3 | 62 ± 0.04 |
| CTPRa4 | 4 | 67 ± 0.03 |
| CTPRa5 | 5 | 70 ± 0.03 |
| CTPRa6 | 6 | 71 ± 0.03 |

Unfolding ΔG at 10°C, kcal mol−1, same table:

| Construct | n | ΔG |
| --- | --- | --- |
| CTPRa2 | 2 | 3.2 ± 0.6 |
| CTPRa3 | 3 | 4.8 ± 0.4 |
| CTPRa4 | 4 | 4.2 ± 1.1 |
| CTPRa5 | 5 | 6.0 ± 0.8 |
| CTPRa6 | 6 | 7.7 ± 0.2 |
| CTPRa8 | 8 | 14.3 ± 1.5 |
| CTPRa10 | 10 | 23.4 ± 2.1 |
| CTPR2 | 2 | 7.6 ± 1.1 |
| CTPR3 | 3 | 12.0 ± 0.7 |

CTPRa and CTPR are different sequences (inter-repeat loop PRS versus PNN). They are separate rows.

### Main, Stott, Jackson, and Regan, 2005

DOI: [10.1073/pnas.0404530102](https://doi.org/10.1073/pnas.0404530102)

Citation: Main ERG, Stott K, Jackson SE, Regan L. Local and long-range stability in tandemly arrayed tetratricopeptide repeats. Proc Natl Acad Sci U S A. 2005;102(16):5721-6.

Read from the PubMed Central HTML for PMC556279, Table 1. The free-energy column header is an image; the image reads ΔG with subscript D-N and superscript H2O. The next column is ΔΔG (the stability difference between two lengths) and was not entered. Buffer in Methods: 50 mM phosphate, pH 6.8, 150 mM NaCl. Errors are from the fit. These are chemical-denaturation unfolding free energies, not DSC melting temperatures. Units in the table are kcal·mol−1.

| Condition | CTPR1 | CTPR2 | CTPR3 |
| --- | --- | --- | --- |
| 25°C GuHCl, CD | 1.5 ± 0.1 | 6.8 ± 0.2 | 10.7 ± 0.2 |
| 25°C GuHCl, fluorescence | — | 6.6 ± 0.2 | 10.5 ± 0.4 |
| 20°C GuHCl, fluorescence | 1.5 ± 0.1 | 7.1 ± 0.3 | 10.1 ± 0.4 |
| 20°C urea, fluorescence | 1.9 ± 0.2 | 6.9 ± 0.3 | 9.3 ± 0.5 |
| 4°C GuHCl, fluorescence | 2.1 ± 0.2 | — | — |
| 4°C urea, fluorescence | 2.2 ± 0.2 | — | — |

Table 2 repeats the 20°C GuHCl equilibrium values and was not entered again.

### Perez-Riba, Lowe, Main, and Itzhaki, 2018

DOI: [10.1016/j.bpj.2018.03.038](https://doi.org/10.1016/j.bpj.2018.03.038)

Citation: Perez-Riba A, Lowe AR, Main ERG, Itzhaki LS. Context-dependent energetics of loop extensions in a family of tandem-repeat proteins. Biophys J. 2018;114(11):2552-2562.

Read from the PMC full text of the article (Biophys J. 2018;114(11):2552–2562). Table 1 gives two-state chemical-denaturation free energies for the unmodified CTPR2, CTPR3, CTPR4, and CTPR6 series. The paper states that these proteins lack the C-terminal solvating helix. Measurements were at 25°C in 50 mM sodium phosphate, pH 6.8, 150 mM NaCl. The CD methods paragraph names GdmHCl. The fluorescence methods paragraph describes high-throughput equilibrium denaturation and does not restate the denaturant name. Errors are the standard error of the mean.

Table 1 prints ΔG_D−N^H2O with a leading minus sign. Equation 2 on the same paper defines that quantity as m × [D]50%, which is positive for these midpoints. The JSON copies the sign printed in the table and does not flip it.

Fluorescence, Table 1, kcal mol−1:

| Construct | n | ΔG |
| --- | --- | --- |
| CTPR2 | 2 | −7.4 ± 0.1 |
| CTPR3 | 3 | −12.0 ± 0.9 |
| CTPR4 | 4 | −19.2 ± 0.9 |
| CTPR6 | 6 | −25.5 ± 1.1 |

CD, Table 1, kcal mol−1:

| Construct | n | ΔG |
| --- | --- | --- |
| CTPR2 | 2 | −7.6 ± 0.1 |
| CTPR3 | 3 | −10.3 ± 0.1 |
| CTPR4 | 4 | −23.3 ± 0.5 |
| CTPR6 | 6 | −26.5 ± 0.5 |

Table 4, construct CTPR2a (the text identifies this DPRS protein as CTPRa2): −6.4 ± 0.1 kcal mol−1. The matching CTPR2n row in Table 4 is the same fluorescence number as CTPR2 in Table 1 and was not entered twice.

## Papers and numbers not entered

- Kajander T, Cortajarena AL, Main ERG, Mochrie SGJ, Regan L. A new folding paradigm for repeat proteins. J Am Chem Soc. 2005. DOI 10.1021/ja0524494 (PMID 16028928). PubMed record only. The full text was not opened, so no number was taken.
- Kajander T, Cortajarena AL, Mochrie S, Regan L. Structure and stability of designed TPR protein superhelices: unusual crystal packing and implications for natural TPR proteins. Acta Crystallogr D Biol Crystallogr. 2007;63:800-811. DOI 10.1107/S0907444907024353 (PMID 17582171). Not in PMC. The publisher page returned a Cloudflare block. The abstract that was retrieved does not state a Tm or a ΔG. CTPR8 and CTPR20 were not assigned a number.
- Cortajarena and Regan 2011 studied CTPRa2 through CTPRa20, and Figure 1 shows a CTPRa20 thermogram, but Table I stops at CTPRa10. No numeric Tm for CTPRa20, CTPRa5, or the missing lengths was read, so those lengths were left out.
- Phillips et al. 2012 Table II reprints rounded Cortajarena Tm values (58, 68, 73, 77, 79, and 80°C). Those are not a second experiment. The unrounded Cortajarena Table I values are the rows that were kept.
- Phillips et al. 2012 also lists a two-state fit Tm from the same DSC endotherm, van't Hoff enthalpies, and β. Those are not separate Tm or ΔG measurements and were not entered. Supporting Information Table I (CD melts from pH 5 to 8) is cited in the text, but that numeric table was not in the HTML that was read.
- Cortajarena AL, Mochrie SG, Regan L. Modulating repeat protein stability: the effect of individual helix stability on the collective behavior of the ensemble. Protein Sci. 2011;20(6):1042-7. DOI 10.1002/pro.638 (PMID 21495096, PMC3104233). The PMC page returned a browser check, so the table was not read. The PubMed abstract describes thermal curves of CTPRa2 variants and does not state a Tm.
- Millership C, Phillips JJ, Main ER. Ising Model Reprogramming of a Repeat Protein's Equilibrium Unfolding Pathway. J Mol Biol. 2016;428(9 Pt A):1804-17. DOI 10.1016/j.jmb.2016.02.022 (PMID 26947150, PMC4871810). The PMC page returned a browser check. No number was read.
- Perez-Riba et al. 2018 Table 1 also lists CTPR-YD point mutants and CTPR6-YD loop insertions. Table 2 lists Ising intrinsic and interface parameters. Tables 3 and 5 list ΔΔG costs of mutation or loop insertion. Those rows were read and left out because they are not the unmodified consensus scaffold versus repeat number. Figure S2 is described only as "very high melting temperatures," with no Tm in the text that was read.
- DARPins, consensus ankyrin repeats, and natural TPR domains that appeared in search results were not entered. They are not CTPR scaffolds.
