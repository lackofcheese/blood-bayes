# Conditional W/D/L tier-power diagnostic

Run date: 2026-07-13. This is an optimistic design diagnostic, not the final power
rehearsal for the thesis gate.

## Method

The joint baseline supplies cross-fitted expected scores for the 2,704 evaluable matches
in 64 linked events. These nuisance predictions are held fixed. Synthetic W/D/L outcomes
are then generated with the observed BB2025 draw probability (`0.2392`) and common tier
effects added to expected score. Each synthetic dataset refits a common tier coefficient
using the same five complete-event folds.

The detection threshold is the 95th percentile of equal-event held-out MSE improvement
under 500 null simulations. Holding nuisance predictions fixed makes these detection
probabilities optimistic; a full refit and richer draw generator would generally reduce
power.

## Results

| Injected tier effect | Mean recovered coefficient | Mean held-out MSE gain | Detection probability |
|---:|---:|---:|---:|
| 0.000 | 0.001 | −0.000054 | 5.0% |
| 0.010 | 0.008 | −0.000071 | 3.2% |
| 0.025 | 0.024 | −0.000042 | 7.0% |
| 0.050 | 0.042 | +0.000028 | 14.6% |
| 0.100 | 0.083 | +0.000296 | 48.2% |

The null calibration is correct by construction. Monte Carlo variation makes the 0.01
row slightly lower than the null; neither small-effect row differs meaningfully from
null behavior. Even a very large `0.10` result-point effect is detected in fewer than
half of simulations.

The actual outcomes give a two-stage coefficient of `+0.0108`, equal-event improvement
of `−0.0000923`, and 29 of 64 events improved. This two-stage statistic differs from the
joint model's `+0.0291` because nuisance effects are fixed rather than jointly refit.
Both fail their held-out predictive comparison.

## Consequence

The current null is not strong evidence that tier compensation has no effect. Under an
optimistic simulation, the existing schedule has poor probability of detecting even
effects that would be practically substantial. The limiting resource is independent,
well-supported event-level tier contrast, not the raw number of match rows.

The next useful data step is expanding validated NAF→Tourplay coverage and finding
repeat-series tier changes. A final gate rehearsal should refit every nuisance term,
simulate race-specific draw propensities and heterogeneous tier response, and calibrate
the eventual pre-registered statistic rather than reuse this exploratory threshold.
