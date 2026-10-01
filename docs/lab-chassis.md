# Lab chassis

The calculations on `/lab` match the experiments in the current lab plan.

Prep stores BCA or Bradford concentration and gel calls. It does not convert mass to a radius and it does not edit screw coordinates. If you enter a repeat count, the page shows the existing screw contour for that length and says the gel did not measure that distance.

The assay window fits `RLU = a + b × amount`, an optional single-exponential furimazine half-life, a coefficient of variation, and a flag for whether one RLU sits inside a linear range you stored.

Calcium is

    L = L_min + (L_max − L_min) / (1 + (EC50 / [Ca])^h)

EC50 is the midpoint of that curve. It does not replace the CaM–M13 peptide Kd. Fewer than four calcium concentrations produce no EC50. If the Hill slope is not identifiable, it is fixed at 1 and the result says so. Reads at 25 °C, 30 °C, and 37 °C are ratios, not an activation energy and not a melting temperature.

SpyCatcher uses fraction locked at each time and both starting concentrations. The default fit is

    d[adduct]/dt = k_lock [Tag][Catcher]

Pseudo-first-order is used only when you name the partner in excess. `k_rev` and `k_bond` are not fit. A rate whose 95% band reaches zero is omitted. The Zakeri 2012 literature k_on is shown beside a successful fit and is not overwritten.

The bridge reports tube2/tube1, tube3/tube2, and tube4/tube2. The sign pattern has no numerical cutoff.

`calibrated` stays false. The residual Gaussian process stays unfitted. A passing test is not scientific validation.
