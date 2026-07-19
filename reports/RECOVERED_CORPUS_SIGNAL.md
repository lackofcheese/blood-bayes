# Signal after the first reviewed-link recovery wave

Run date: 2026-07-13. This is a post-selection exploratory sensitivity, not the
pre-registered thesis gate. The recovered events were chosen for validation value and
size, so comparisons with the original corpus are not an unbiased sequential test.

## Corpus change

The 30-case Luna review accepted 26 links and rejected four apparent negatives. Eleven
accepted events had at least 40 playing coaches; all 11 compact Tourplay detail requests
returned HTTP 200 and usable machine-readable pack structures.

After merging those reviewed details with the original coverage while preserving the
original corpus separately:

- 76 Tourplay events normalize successfully, with three original missing-cache rows;
- 75 events and 6,115 matches have unambiguous race-tier mappings for the match model;
- all 2,340 race rows, 705 packs, 2,758 options, 3,531 inducements, and 7,826 star rows
  resolve exactly once;
- only the previously known fabulous-mercenary IDs remain semantically unresolved.

The original tier schedule had 64 evaluable events and 2,704 matches. The first recovery
wave therefore adds 11 evaluable events but 3,411 matches because it deliberately targets
large tournaments.

## Match-level tier result

| Summary | Original corpus | Expanded corpus |
|---|---:|---:|
| Evaluable events | 64 | 75 |
| Evaluable matches | 2,704 | 6,115 |
| Common tier coefficient | +0.0291 | +0.0508 |
| All-event equal-event MSE gain | −0.000208 | −0.000212 |
| All-event match-weighted gain | −0.000066 | +0.000036 |
| ≥25-coach equal-event gain | −0.000024 | +0.000025 |
| ≥25-coach match-weighted gain | +0.000064 | +0.000114 |
| ≥40-coach equal-event gain | +0.000175 | +0.000266 |
| ≥40-coach events improved | 5/8 | 11/19 |

The common effect points more strongly in the expected direction and now improves the
match-weighted full-corpus metric and both larger-event summaries. Equal weighting over
all events remains negative because small events continue to be volatile. The shrunk
race-specific alternative remains negative, so unconstrained heterogeneity does not
explain the improvement.

## Conditional W/D/L detectability

The optimistic fixed-nuisance simulation also improves:

| Injected effect | Original detection | Expanded detection |
|---:|---:|---:|
| 0.025 | 7.0% | 10.6% |
| 0.050 | 14.6% | 30.4% |
| 0.100 | 48.2% | 74.8% |

This remains underpowered for modest effects, but the change demonstrates that recovering
large events materially improves the design. More validated events—especially large,
connected, and repeat-series contrasts—are likely more valuable than adding model
flexibility now.

## Interpretation

The expanded result is encouraging but cannot be treated as confirmation:

- events were selected partly for size and recoverability;
- thresholds and summaries were already inspected;
- tier mixes organizer belief with compensation;
- the simulation holds nuisance predictions fixed;
- pack semantics have not passed domain review.

The appropriate next step is another frozen recovery wave followed by a separately
declared evaluation summary, or the domain review and formal schema/power rehearsal—not
continued opportunistic threshold selection on this result.
