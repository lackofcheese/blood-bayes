# Match-level relative-tier reconnaissance

Run date: 2026-07-13. This is exploratory and non-binding. Relative tier combines
organizer belief and delivered compensation; its coefficient is predictive, not causal.

## Design

One oriented row is used per BB2025 match, with win/draw/loss scored as 1/0.5/0. The
antisymmetric ridge baseline jointly estimates coach and race terms on all BB2025
matches outside the held-out event fold. Unlinked matches improve nuisance estimation
but receive no tier value.

Relative tier is normalized within event from zero (least compensated) to one (most
compensated), then centered within race using training events only. The common model
adds the difference between the two races' centered relative tiers. A separate
race-specific model uses strongly shrunk tier responses only for races supported in at
least five training events. It does not combine an unidentified common coefficient with
unconstrained deviations.

Five deterministic folds hold out complete linked events. All models are scored on the
same held-out matches for which both races have one unambiguous Tourplay tier.

## Observed result

- 64 events and 2,704 matches are evaluable; one linked event is excluded by tier/race
  ambiguity or coverage.
- The mean fitted common coefficient is `+0.0291` result points for a full move from
  least- to most-compensated relative tier.
- Across all events, the common model's equal-event MSE improvement is `−0.000208`; it
  improves 30 of 64 events. Match weighting reduces the loss to `−0.0000656`.
- At the 25-coach threshold, equal-event improvement is `−0.0000241`; match-weighted
  improvement is `+0.0000637`, and 10 of 20 events improve.
- The 8 events with at least 40 coaches are positive under both summaries
  (`+0.000175` event-equal; `+0.000158` match-weighted), but this threshold comparison
  is descriptive and was not pre-registered.
- The shrunk race-specific alternative is essentially flat: `+0.0000171` across all
  events, but `−0.00000489` among the 20 larger events.

The positive coefficient does not translate into stable held-out gain across the full
corpus. Larger events lean positive, but the size thresholds are few, selected, and
examined after seeing the data. This is suggestive directionally, not evidence that
relative tier generalizes.

### Coach–race specialization sensitivity

Adding a separately shrunk coach×race term barely changes the result:

- common tier coefficient: `0.0291 → 0.0297`;
- all-event equal-event improvement: `−0.000208 → −0.000216`;
- ≥25-coach equal-event improvement: `−0.0000241 → −0.0000234`;
- ≥25-coach match-weighted improvement: `+0.0000637 → +0.0000651`.

General coach adjustment does not appear to be hiding a large specialization confound
under this contemporaneous, shrunk sensitivity. This is not yet a strictly pre-event
coach–race history model, so temporal leakage and changing ability remain later checks.

## Injection rehearsal

Known common effects were added to the observed scalar outcomes throughout the same
schedule and the entire grouped fitting pipeline was rerun. This validates recovery
mechanics amid the observed noise; because it reuses observed outcomes and is not a
generative W/D/L simulation, it is not a formal power calculation.

| Added effect | Mean recovered common coefficient | MSE gain, all 64 events | MSE gain, 20 events ≥25 coaches |
|---:|---:|---:|---:|
| 0.000 | 0.029 | −0.000208 | −0.000024 |
| 0.025 | 0.051 | −0.000247 | +0.000030 |
| 0.050 | 0.073 | −0.000234 | +0.000131 |
| 0.100 | 0.116 | −0.000053 | +0.000472 |

The coefficient recovers about 87% of an added common effect. Equal weighting across all
events remains dominated by volatile small events even after a large injection. The
larger-event subset responds monotonically, but contains only 20 event clusters.

## Interpretation

The expanded match-level model is less negative than the earlier event/race-cell probe,
and the observed coefficient has the expected sign. It still supplies no held-out
predictive evidence. The rehearsal suggests that effects around 0.025 result points are
at the edge of visibility in the larger events, while even 0.10 is not enough to make
the current equal-all-event summary clearly positive.

Next statistical work should use a proper simulated three-category W/D/L generator,
event-cluster uncertainty, and prospective/calendar sensitivities. Next data work should
seek additional linked events and repeated-series contrasts. No tier result should be
promoted into schema v0 from this exploration alone.
