# Stability confirmation

This note locks the thermal lookup the design screen already uses. It does not add a melting model, and it does not change any thermal number in the literature file.

Passing these checks means the panel echoes that file. It is not a validation that a construct will melt at the reported temperature in a chassis.

## Default series

The default series id is `phillips2012_ctpra_dsc`. That series is Phillips et al. 2012, DOI 10.1002/pro.2018, construct family CTPRa, differential scanning calorimetry, 50 mM phosphate, pH 7.0. The numbers are read from `data/stability/ctpr_thermal_literature.json`.

## Series stay separate

These four series are reported side by side. They are never averaged:

- `phillips2012_ctpra_dsc` (the default)
- `cortajarena2011_ctpra_dsc`
- `phillips2012_ctpra_cd`
- `phillips2012_ctpr_dsc`

A repeat count that appears in more than one series keeps one row per series.

## Assay temperature

The comparison at 37 C is an E. coli operating assumption. It is not a DSC setpoint from Phillips et al. 2012.

## What a row contains

`GET /api/stability/panel` and `stability_panel` are the lookup. In the default Phillips CTPRa DSC series, n=3 and n=8 have a Tm row and an unfolding delta_G row. n=14 has no row. On that lookup, `thermal_state` is `extrapolated`, `tm_C` is null, and `delta_g` is null.

`GET /api/stability/confirm` is the page payload. The number at each repeat count is a per-series length fit evaluated at that n. With at least four points the model tried first is `y(n) = y_inf - (y_inf - y_1) * exp(-(n-1)/lambda)`, with `y_inf`, `y_1`, and `lambda` positive. It is reported only when it is identifiable: every parameter standard error is finite, and the prediction sigma at n = 3, 8, and 14 is not larger than the absolute prediction. Otherwise the same rows use the line `y(n) = a + b*n`, and that line's value and linearized 95% band are what is shown. If the line is also non-identifiable, no point value is reported; for unfolding ΔG the warning is that the rows do not determine ΔG(n). With two or three points the model is the line `y(n) = a + b*n`. The default-series Tm fit stays the saturating form. The default-series unfolding ΔG uses the line. n=14 on the default series is that model at 14, and the payload says 14 is past the longest cited length in the series. The comparison at 37 °C uses the calculated melting temperature. A paper cell, when one exists, is `paper_tm_C` or `paper_delta_g`. It is not the primary number. Cortajarena has no ΔG rows, so calculated ΔG stays unset for that series and is not borrowed. The 95% band is value ± 1.96 σ from the linearized fit covariance, labeled a linear approximation, not a wet-lab confidence interval. ΔHcal and ΔCp are not estimated.

`calibrated` is false on every row. Unfolding ΔG does not set pass or fail. The state comes from comparing the calculated Tm with the assay temperature. Series are not averaged. A passing test is not scientific validation.

## Gaps

n=7 and n=9 are absent from the default series, so `tm_C` stays null. Those lengths are not the midpoint of their neighbors. n=14 is outside the cited repeat range, so `tm_C` stays null rather than a blend of measured lengths.

## Where this is checked

`tests/math_chassis/test_stability_confirmation.py` calls `stability_panel(37)` and `literature_confirm(37)` and compares n = 3, 8, and 14 on all four series with the JSON row for that series and repeat count. A null printed Tm uncertainty stays null, and the published interval is null. The gate's own zero-width envelope is not copied onto the panel.

## What each number is

A passing test of this arithmetic is not a validation that a construct will melt, or that an unfolding free energy was measured.

### Tm gate

`thermal_gate` looks up one named series. It passes when that series has a Tm at the requested n and the Tm is strictly above the comparison temperature. The comparison used on the design screen's gate is 37 C, an E. coli operating assumption, not a DSC setpoint from Phillips et al. 2012. A missing n inside the cited repeat range stays omitted. A missing n outside that range is extrapolated, and the gate's own Tm stays empty. That gate is not the confirmation page. The page uses the length fit described above.

### Printed ΔG

The printed unfolding ΔG is a table cell. For the default series it is the Phillips 2012 CTPRa DSC value at 10 C (Table I, kcal mol-1, sign as printed). It stays that cell when the user edits Tm. It is not the calculator output. For n = 3 that cell is the JSON value 4.8 kcal mol-1. n = 14 has no cell, so the printed ΔG stays empty.

### Two-state identity

For a two-state melt, ΔG(Tm) = 0. That identity depends on the Tm in use. It is not a measurement, and it does not need ΔH or ΔS. It holds only for a two-state transition. calibrated stays false. No uncertainty band is attached to the zero.

### Gibbs–Helmholtz curve

Away from Tm the two-state relation is, with T in kelvin,

ΔH(T) = ΔHcal + ΔCp (T − Tm)

ΔS(T) = ΔHcal / Tm + ΔCp ln(T / Tm)

ΔG(T) = ΔH(T) − T ΔS(T)

It needs a caller-supplied ΔHcal and ΔCp. It is not identifiable from Tm alone. The literature JSON does not contain those calorimetric numbers, and this note does not add them. A typed ΔHcal and ΔCp stay on this path.

### Effective enthalpy under ΔCp = 0

A finite Tm plus a finite anchor ΔG at a known reference temperature is still one equation in two unknowns (ΔHcal, ΔCp). The calculator closes that only under the explicit assumption ΔCp = 0, labeled on every output of this path:

ΔH_eff = ΔG(T_ref) / (1 − T_ref / Tm)

ΔG(T) = ΔH_eff (1 − T / Tm)

ΔS_eff = ΔH_eff / Tm

Temperatures are kelvin. ΔG(Tm) = 0 and ΔG(T_ref) equals the anchor. ΔH_eff is an effective enthalpy under ΔCp = 0. It is not the DSC ΔHcal from Phillips et al. 2012. That paper used a nonzero ΔCp, and that number is not in the JSON. The confidence tier is hypothesis_only, is_extrapolation is true, and calibrated stays false. Changing Tm changes ΔH_eff and ΔG(T). The printed table cell does not change. If Tm equals the anchor temperature, the denominator is 0, the path is refused, ΔG at that temperature is the anchor, and ΔH is not identifiable. If there is no anchor (n = 14, or the user cleared it), ΔG(T) is not invented and only ΔG(Tm) = 0 is shown. kcal and kJ are converted only with 1 kcal = 4.184 kJ, and that conversion is recorded.

## Remaining blockers

These are missing inputs. They are not coded around.

- `ctpr_thermal_literature.json` has no ΔHcal and no ΔCp. The Phillips calorimetric curve, which used a nonzero ΔCp, cannot be computed from the file.
- n = 14 has no cited Tm and no printed ΔG in the default series. Neither number is invented.
- There is no unfolding assay of the Hong Kong team fusion. `calibrated` stays false. A passing test is not that assay.

## Audit gaps

Checked `origami/stability/thermo.py`, `gate.py`, `series.py`, `origami/api/stability.py`, `origami/drylab.py` `stability_panel`, the stability board, the calculator, and `tests/math_chassis/test_thermo_calculator.py`, `test_stability_confirmation.py`, `test_drylab.py`.

What already held, and was left in place:

- For a two-state melt, ΔG(Tm) = 0. That identity has no uncertainty band.
- Under ΔCp = 0, ΔH_eff = ΔG(T_ref) / (1 − T_ref/Tm) and ΔG(T) = ΔH_eff (1 − T/Tm), with T_K = t_C + 273.15. Changing Tm changes ΔH_eff. The printed ΔG cell does not change.
- The full Gibbs–Helmholtz curve is a separate path and runs only when the caller supplies ΔHcal and ΔCp. The literature file still has neither.
- The thermal panel uses one series at a time. A missing n outside the cited repeat range is extrapolated. A missing n inside that range stays omitted. Series are not averaged. `calibrated` stays false.

Gaps:

- The ΔCp = 0 path reported point values and then said no sigma had been supplied, even when the cited Tm row and the printed ΔG row already store uncertainties. That propagation is now coded. It reads those sigmas from the caller, who copies them from the table. It does not type them. If either sigma is null, the point value remains and the band is omitted. Null is not stored as 0. The 95% band is value ± 1.96 σ from a first-order delta method, labeled as a linear approximation, not a wet-lab confidence interval. ∂H/∂Tm is negative, −G T_ref / (D² Tm²). The variance uses that square, which is the unsigned magnitude. ΔG(T) includes Cov(H, Tm), so the band at T_ref matches the anchor uncertainty. The calculator draws that band for the default series at n = 3 and n = 8, where both printed uncertainties exist.
- `stability_panel` used to set `tm_uncertainty_C` from the gate envelope. The gate gives a missing uncertainty zero width, so a null table uncertainty became 0. The panel now copies the printed uncertainty, and null stays null.
- The lookup panel still omits a missing printed Tm uncertainty. `thermal_gate` still keeps zero width for its own pass/fail tests. The calculator does not read that envelope as a sigma.
- `/stability` lists all four series at n = 3, 8, and 14. The primary number is the length fit. Phillips 2012 CTPR DSC has two Tm points, so that series uses the line and warns that two points determine a line. n = 14 is past the longest cited length and is still a calculated number.

Still open, and not coded around:

- `thermal_gate` still averages duplicate Tm rows at the same n if a caller passes more than one. The panel passes one series, and each named series has one Tm per n.
- `ctpr_thermal_literature.json` has no ΔHcal and no ΔCp. The length fit does not estimate them. n = 14 has no cited Tm and no printed ΔG in the default series; the page shows the length model there, not a new table cell. There is no unfolding assay of the Hong Kong team fusion. `calibrated` stays false.
