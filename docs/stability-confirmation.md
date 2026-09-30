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
