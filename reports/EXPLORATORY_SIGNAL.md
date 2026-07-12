# Exploratory pack-signal reconnaissance

Run date: 2026-07-13. This is a non-binding feasibility probe, not treatment schema
v0, the pre-registered thesis gate, or a causal analysis.

## Questions

1. Is coach/race-adjusted event-by-race result variation visibly larger than cell-level
   sampling noise in the currently recoverable corpus?
2. Can deliberately crude, literal Tourplay configuration fields predict held-out
   event-by-race residuals?
3. Is the exact-linked candidate corpus sufficiently connected for the planned model?

The probe uses the 20 exact-linked events with at least 25 playing coaches. Outcome
predictions use five deterministic whole-event folds. The baseline estimates shrunk
coach and race result effects using BB2025 games outside the held-out fold. Event/race
residual cells require at least four race appearances for the raw-field model.

The probes compare relative tier alone, literal resources alone, and both together.
Relative tier is `(tier - 1) / (number of tiers - 1)`, so zero is the least-compensated
tier and one the most-compensated. The resource fields are treasury, number of legal
pack alternatives, minimum/maximum pack currency, maximum stacked-player setting,
literal primary/secondary costs and presence, star presence/quantity, and extra-gold
maximum. Alternatives are summarized as the legal choice set; no roster choice is
inferred. Features and residuals are centered within race using training events only,
then fit with fixed ridge shrinkage. Conflicting duplicate race assignments are
excluded rather than overwritten.

## Results

- 20 candidate events contain 1,592 matches.
- Their direct shared-coach graph has only 9 edges; 6 events are isolated.
- The residual table has 395 event/race cells. Its weighted residual RMS is 0.144.
- A simple subtraction of estimated cell sampling variance leaves zero positive excess
  RMS. This is not proof of no heterogeneity: small cells, paired match residuals, and
  the approximate baseline make this a low-power descriptive diagnostic.
- 280 cells across 19 events enter the feature probes. One event has no evaluable
  cells after race-name/feature availability and minimum-count requirements.
- Tier alone gives equal-event held-out MSE improvement **−0.000325**, with 9 of 19
  events improved and a within-race permutation benchmark of `p=0.645`.
- Literal resources alone give **−0.00127**, with 3 of 19 events improved.
- Tier plus resources gives **−0.00163**, with 4 of 19 events improved.
- The mean standardized relative-tier coefficient is positive but small (`0.00865`)
  and does not translate into held-out predictive gain. It is therefore not evidence
  of a compensation effect.

All three models are worse than the race-centered baseline on average. Relative tier
is markedly less harmful than the eleven-field resource model, but supplies no
generalizing signal in this sample and specification.

Individual exploratory coefficients are not interpreted. They are correlated, depend
on organizer configuration conventions, and showed no aggregate held-out gain.

## What this does and does not imply

The result does **not** reject the pack-treatment thesis. The exact-linked sample is
small and selected; literal Tourplay fields mix units and legal alternatives; domain
mechanisms such as affordability or viable skill placement are absent; and event,
region, attendance, and organizer choices remain confounded.

It does show that merely feeding raw Tourplay settings into a regularized model is not
a convincing shortcut around domain expertise. The next pack work should therefore
use this corpus inventory to choose informative contrasts, then obtain the expert
composites and resource-pressure rules before schema v0 is frozen.

Connectivity is an immediate design concern. Across all 65 exact-linked events the
largest direct component is much healthier, but applying the 25-coach floor removes
many bridges. Candidate selection should consider smaller bridge events or identify
coach strength through the broader BB2025 NAF backbone, with an explicit sensitivity
to the direct-overlap-only subset.

## Reproduction

```bash
.venv/bin/bb-stats-exploratory-signal \
  data/derived/naf data/derived/tourplay data/derived/tourplay_resolved \
  reports/generated/exploratory_signal
```

Generated CSV/JSON artifacts are ignored by Git. The committed implementation and
tests preserve the assumptions needed to reproduce them.
