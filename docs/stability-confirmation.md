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

In the default Phillips CTPRa DSC series, n=3 and n=8 have a Tm row and an unfolding delta_G row. n=14 has no row. For n=14, `thermal_state` is `extrapolated`, `tm_C` is null, and `delta_g` is null.

`calibrated` is false on every panel row. Unfolding delta_G is reported next to the Tm gate. It does not set `thermal_state`. The state comes from the Tm gate only. There is no interpolation between measured lengths.

## Gaps

n=7 and n=9 are absent from the default series, so `tm_C` stays null. Those lengths are not the midpoint of their neighbors. n=14 is outside the cited repeat range, so `tm_C` stays null rather than a blend of measured lengths.

## Where this is checked

`tests/math_chassis/test_stability_confirmation.py` calls `stability_panel(37)` and compares n = 3, 8, and 14 on all four series with the JSON row for that series and repeat count.

## What each number is

A passing test of this arithmetic is not a validation that a construct will melt, or that an unfolding free energy was measured.

### Tm gate

The gate looks up one named series. It passes when that series has a Tm at the requested n and the Tm is strictly above the comparison temperature. The comparison used on the design screen is 37 C, an E. coli operating assumption, not a DSC setpoint from Phillips et al. 2012. A missing n inside the cited repeat range stays omitted. A missing n outside that range is extrapolated, and the Tm stays empty. There is no Tm(n) fit and no interpolation.

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
