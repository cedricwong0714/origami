# Assay window

## Purpose
Turn a standard curve, a furimazine time series, replicate readings, and a linear range into numbers the rest of the lab chassis can trust.

## Scientific basis
The standard curve is the line RLU = a + b × amount. Furimazine decay is RLU = A exp(−k t), with half-life ln(2) / k. CV is the sample standard deviation divided by the mean. These are definitions of the fit, not measured biological constants.

## Inputs
Amounts and RLU, minutes and RLU, a list of replicates, and an optional RLU window. Units are whatever the caller recorded for the amount axis. Time enters in minutes and is converted to seconds by multiplying by 60.

## Outputs
Slope, intercept, half-life, and CV, each with a 95% band only when the fit covariance is finite. A missing sigma is omitted. `calibrated` is false.

## Assumptions
The standard curve is linear inside the points you typed. The decay is a single exponential. Replicates are exchangeable.

## Known limitations
This module does not decide that a later luminescence value is biologically meaningful. It only says whether that value sits inside the window you stored.

## Parameter sources
None. Every number comes from the request.

## Tests
`PYTHONPATH=/workspace python -m pytest tests/math_chassis/test_lab_chassis.py -q`

## Owner
Dry-lab / math chassis maintainers.
