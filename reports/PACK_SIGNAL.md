# Schema-informed pack-signal preliminary result

Run date: 2026-07-20. The feature definition and interpretation rule were committed in
`ba11706` before this outcome run. This remains a non-binding pipeline test: the same outcomes
informed earlier reconnaissance, the inputs are Tourplay availability envelopes, and no draft
pack field was promoted or treated as human-confirmed.

## Coverage

- 95 reviewed NAF-to-Tourplay links were available.
- Safe envelopes were recovered for 2,886 event/race pairs across 94 events.
- The frozen ≥40-coach threshold selected 39 events and 7,125 matches.
- One selected event lacked safe envelopes; 38 events and 795 race cells entered every probe.
- The selected-event coach graph has 204 direct-overlap edges and two isolated events.

The five mechanism features were Team Gold, maximum Primary capacity, maximum Secondary
capacity, maximum Star quantity, and maximum Extra Gold. They describe the most permissive
legal alternative available to a race, not a coach's selected or affordable realized roster.

## Frozen results

All models use the same cells, training-only within-race centering/scaling, and leave-one-event-
out evaluation.

| Probe | Equal-event MSE improvement | Match-weighted improvement | Events improved |
|---|---:|---:|---:|
| Relative tier only | +0.000230 | +0.000114 | 26/38 |
| Five mechanisms only | +0.000093 | +0.000172 | 24/38 |
| Tier plus mechanisms | +0.000189 | +0.000185 | 25/38 |

The frozen primary statistic, mechanism-only equal-event improvement, is positive. Its
199-permutation within-race calibration gives a null mean of `−0.000334`, null 95th percentile
of `−0.000034`, and one-sided diagnostic `p=0.005`. This is a useful pipeline signal, not a
confirmatory p-value, because earlier analyses already inspected these outcomes and helped
motivate the representation.

The frozen secondary contrast is negative: adding mechanisms changes equal-event improvement
from `+0.000230` to `+0.000189`, an increment of `−0.000042`. Under match weighting the same
increment is positive (`+0.000071`), but match weighting was a reported summary rather than the
frozen secondary decision contrast.

## Interpretation

The schema-inspired representation clears the deliberately modest test of carrying some
held-out predictive signal by itself. It is substantially more disciplined than the earlier
eleven-field literal-resource probe and is worth retaining for later design work.

It does not yet separate delivered compensation from organizer tier judgement. Relative tier
remains better on the equal-event summary, and the combined model does not improve that frozen
comparison. The mechanism coefficients are correlated and should not be interpreted as causal
effects of Gold, skills, Secondary access, Stars, or Extra Gold.

The positive match-weighted result and negative incremental equal-event result also show that
event size and volatility still matter. No post-hoc size threshold or event exclusion is applied
here; in particular, the largest negative event-level mechanism result remains in the summary.

## Limitations carried forward

- Legal alternatives are independently maximized, so feature maxima need not describe one
  jointly attainable roster.
- Tourplay is non-normative and may differ from the organizer rulebook actually applied.
- A currency-priced advancement with unsafe budget/cost semantics is excluded, producing one
  missing selected event.
- Stacking, Elite membership, inducements, local match rules, scoring, and event structure are
  omitted rather than coerced into weak common features.
- Race/event residual cells remain noisy and paired within matches.
- Reuse of previously inspected outcomes prevents confirmatory inference.

## Consequence

Keep the five-feature envelope as a preliminary baseline, but do not treat it as the treatment
model or evidence beyond tier. The next design improvement should represent jointly attainable
legal packages and affordability, then rehearse power and validation without choosing features
from these outcomes. Deferred human review remains a promotion gate under
`packs/DEFERRED_REVIEWS.md`, not an immediate prerequisite for that engineering work.

## Reproduction

```bash
.venv/bin/bb-stats-pack-signal \
  data/derived/naf data/derived/tourplay_wave2 data/derived/tourplay_resolved_wave2 \
  reports/generated/pack_signal
```

The generated JSON and feature-envelope CSV are ignored; the protocol, implementation, tests,
and this reconciled result are committed.
