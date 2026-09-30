# Stability

## Purpose

Load one published CTPR thermal series, compare a cited melting temperature with an assay temperature, and evaluate a per-series length curve for the confirmation page.

The length curve is not a rewrite of `thermal_gate`. The gate still looks up a cited `Tm_C` row. `GET /api/stability/panel` is that lookup. `GET /api/stability/confirm` evaluates the length model.

## Scientific basis

With at least four points of one series and one observable, the model is

```text
y(n) = y_inf - (y_inf - y_1) * exp(-(n-1)/lambda)
```

`y_inf`, `y_1`, and `lambda` are positive. The shape is an assumption: a rod whose ends matter less as it gets longer, so the observable moves from `y_1` toward `y_inf`. It is not a parameter taken from a paper, and it is not a calibrated chassis model.

With two or three points the three-parameter form is not fit. The model is the line `y(n) = a + b*n`. Two points determine that line, and a length far from those points is weakly constrained. With fewer than two points, no curve is invented.

Coefficients come from `scipy.optimize.curve_fit` on that series alone. The 95% band is value ± 1.96 σ from the linearized covariance. It is a linear approximation, not a wet-lab confidence interval. A parameter whose covariance variance is not finite is non-identifiable. `confidence_tier` is `hypothesis_only`. `calibrated` is false.

## Inputs

Named series ids in `series.py`, read from `data/stability/ctpr_thermal_literature.json`. Melting temperature rows use units `C`. Unfolding ΔG rows keep the units string printed on those rows. The assay comparison on the page is 37 °C, an E. coli operating assumption, not a DSC setpoint from Phillips et al. 2012.

## Outputs

A model value at a requested repeat count, a standard error for each identifiable coefficient, and a 95% band when the prediction variance is finite. The literature cell, when one exists, is returned separately as a paper-row reference.

## Assumptions

- One series is fit at a time. Series are not averaged. Duplicate repeat counts in one series are not averaged.
- The fit is unweighted. Printed uncertainties are not used as weights.
- ΔG(n) is a fit of the printed unfolding ΔG column versus repeat count. It is not a temperature correction.
- Pass or fail on the confirmation page compares the calculated melting temperature with the assay temperature. ΔG does not set that state.

## Known limitations

Phillips CTPRa DSC unfolding ΔG is still rising across the cited lengths. The saturating form cannot follow a curve that keeps steepening, so those coefficients are weakly separated and the linearized band is wide. The reported ΔG is still the model at that n.

Cortajarena and Regan 2011 has no ΔG rows in this file. That series stays without a calculated ΔG. The value is not borrowed from Phillips.

There is no unfolding assay of the Hong Kong team fusion. A passing test of this arithmetic is not scientific validation.

## Parameter sources

No ΔHcal, ΔCp, or other biological constant was added. `y_inf`, `y_1`, `lambda`, `a`, and `b` are estimated by the fit to the rows already in `data/stability/ctpr_thermal_literature.json`. The literature file is the source of the data. It is not edited by this module.

The factor 1.96 is the standard-normal 97.5 percentile used for the 95% band. It is not a biological parameter.

## Tests

```text
PYTHONPATH=/workspace python -m pytest tests/math_chassis/test_length_fit.py tests/math_chassis/test_stability_confirmation.py -q
```

## Owner

The team maintaining the stability confirmation screen.
