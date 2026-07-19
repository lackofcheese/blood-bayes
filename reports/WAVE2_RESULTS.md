# Tourplay recovery wave two: results

Run date: 2026-07-13. Selection and reported summaries were frozen in
`WAVE2_PROTOCOL.md` before review, fetching, or outcome re-analysis.

## Recovery

All 20 frozen candidates were independently reviewed by Luna and accepted. Evidence is
stored in `data/curated/tourplay_wave2_review.csv`. Every accepted slug then received one
delayed compact detail request:

- 20/20 returned HTTP 200 and were cached;
- all 20 contain tiers, race mappings, improvement packs, and stacking rules;
- 16 contain explicit skill costs;
- 18 contain explicit star configuration;
- 13 expose legal pack choice sets and seven a single pack per tier.

Canonical event IDs and coverage fields are in
`data/curated/tourplay_wave2_details.csv`.

## Cumulative corpus

The original exact-link corpus, wave one, and wave two are retained as separate derived
outputs. Cumulatively:

- 96 events normalize successfully; three old exact links still lack cache;
- 95 events and 8,952 matches have unambiguous race-tier mappings;
- all 2,951 race rows, 879 packs, 3,468 options, 4,381 inducements, and 9,114 star rows
  resolve exactly once;
- ten observed unresolved IDs are all event-specific fabulous mercenaries; ordinary
  races, packs, options, inducements, and stars remain fully resolved.

## Frozen tier summaries

| Summary | Original | After wave one | After wave two |
|---|---:|---:|---:|
| Evaluable events | 64 | 75 | 95 |
| Evaluable matches | 2,704 | 6,115 | 8,952 |
| Common tier coefficient | +0.0291 | +0.0508 | +0.0611 |
| All-event equal-event MSE gain | −0.000208 | −0.000212 | −0.000264 |
| All-event match-weighted gain | −0.000066 | +0.000036 | +0.000059 |
| ≥25 equal-event gain | −0.000024 | +0.000025 | −0.000011 |
| ≥25 match-weighted gain | +0.000064 | +0.000114 | +0.000132 |
| ≥40 equal-event gain | +0.000175 | +0.000266 | +0.000191 |
| ≥40 match-weighted gain | +0.000158 | +0.000165 | +0.000190 |
| ≥40 held-out events improved | 5/8 | 11/19 | 26/39 |

The coefficient strengthens monotonically and all match-weighted summaries are now
positive. The frozen ≥40 event-equal summary remains positive, with a clear majority of
events improved. Equal weighting over all events remains negative, and the ≥25
equal-event result returns slightly below zero; small-event volatility remains a real
limitation rather than disappearing with more large events. The race-specific alternative
remains negative under every frozen threshold.

## Conditional detectability

| Injected effect | Original | After wave one | After wave two |
|---:|---:|---:|---:|
| 0.050 | 14.6% | 30.4% | 44.8% |
| 0.100 | 48.2% | 74.8% | 89.6% |

Wave two materially improves the design, but the optimistic conditional simulation still
detects a `0.05` result-point effect less than half the time. A formal end-to-end power
rehearsal would be weaker because nuisance models must be refit.

## Interpretation and stopping recommendation

The result is now consistently encouraging for a common relative-tier signal among
larger events, but it remains exploratory, predictive, and selected. Tier combines
organizer judgement with delivered compensation, and no domain-approved pack schema has
yet separated those mechanisms.

Stop sequential outcome-guided recovery analysis here. Additional reviewed links remain
valuable for the eventual corpus, but their outcomes should next be assessed only under
the domain-informed schema and a formally frozen gate/power protocol. Continuing to add
waves while inspecting the same tier coefficient would turn a useful reconnaissance
pattern into uncontrolled sequential testing.
