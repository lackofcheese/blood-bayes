# Schema-informed pack-signal preliminary protocol

Frozen on 2026-07-20 before running this feature specification against outcomes. This is a
non-binding pipeline test, not the confirmatory thesis gate. The same outcomes informed earlier
tier and raw-resource reconnaissance, so no p-value from this exercise is confirmatory.

## Question

Do a small set of source-faithful, schema-inspired resource envelopes predict held-out
event-by-race residuals better than a race-centered baseline in the reviewed Tourplay wave-two
corpus? Does adding those envelopes improve on relative tier alone?

## Corpus and holdout

- Use `data/derived/tourplay_wave2` and `data/derived/tourplay_resolved_wave2` only.
- Use exact reviewed NAF links already present in that corpus.
- Retain the pre-existing threshold of at least 40 playing coaches; do not select a new size
  threshold from these results.
- Estimate coach/race-adjusted event-by-race residual cells using the existing five-fold
  complete-event baseline.
- Require at least four race appearances in a cell.
- Hold out one complete event at a time in the feature probe. Center and scale within race from
  training events only.

## Frozen feature envelope

Each event/race receives the treatment made available to that race, not a realized roster.
Across mutually exclusive legal packs, capacities use the maximum legal alternative and are
therefore availability envelopes:

1. `team_gold_k`: the published tier treasury budget in Tourplay's displayed-thousands unit;
2. `primary_capacity_max`: maximum purchasable Primary advancements, bounded by the legal
   pack's currency and cost where present, otherwise by its explicit quantity cap;
3. `secondary_capacity_max`: the analogous Secondary capacity, zero when unavailable;
4. `star_quantity_max`: maximum Star Player quantity exposed by any legal pack;
5. `extra_gold_k_max`: maximum explicit Extra Gold option.

Tourplay sentinel quantity `999` is bounded at 16, the ordinary roster-size ceiling, only when
computing an availability envelope. A currency-priced advancement with no positive pack budget
or cost is not safely convertible; event/race mappings containing such a legal alternative are
excluded rather than imputed. Conflicting duplicate tier/race assignments are also excluded.

These features deliberately omit stacking, Elite membership, inducement counts, and local
match rules because the current normalized semantics are insufficient for a defensible common
numeric treatment. Human-reviewed pack values are not required for this pipeline rehearsal.

## Frozen summaries

Report three grouped probes on the same evaluable cells:

- relative tier only;
- the five mechanism features only; and
- relative tier plus the five mechanism features.

For each report equal-event held-out MSE improvement, match-weighted MSE improvement, event
count, and events improved. The primary pipeline statistic is the mechanism-only equal-event
MSE improvement. The secondary contrast is combined improvement minus tier-only improvement.
Run the existing 199-permutation within-race benchmark for the mechanism-only statistic as a
calibration diagnostic, not as a confirmatory test.

## Interpretation rule

A positive result only shows that this representation is worth carrying into later design. A
null or negative result can reject this preliminary representation, not the underlying pack
effect. No result changes pack review status, freezes schema v0, or bypasses the human promotion
gate in `packs/DEFERRED_REVIEWS.md`.
