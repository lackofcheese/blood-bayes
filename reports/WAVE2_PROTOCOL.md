# Tourplay recovery wave two: frozen protocol

Frozen before review, fetching, normalization, or outcome re-analysis on 2026-07-13.

Wave two contains the 20 largest unreviewed high-confidence candidates with at least 40
playing coaches after wave one, ordered by coach count with deterministic event-ID
tie-breaking. It includes four countries or regions absent from the largest European
cluster, three squad events, and one deliberately lower-scoring large candidate. The
exact list is `data/curated/tourplay_wave2_plan.csv`.

Every candidate receives a Luna metadata review using NAF identity/source fields,
cached Tourplay listing metadata, format, location, NAF/ruleset flags, and registration
counts. Reviewers return linked, rejected, ambiguous, or not found. No candidate is
fetched or promoted before review. Accepted slugs receive one compact detail request,
with a three-second delay, cache, hard request cap, no retries, and stop after three
consecutive blocked responses.

The post-wave analysis reports only these previously used summaries:

1. evaluable events and matches;
2. common within-race relative-tier coefficient;
3. equal-event and match-weighted held-out MSE improvement over all events;
4. the same improvements for the pre-existing 25- and 40-coach thresholds;
5. number of held-out events improved at those thresholds; and
6. conditional W/D/L detection probability at injected effects 0.05 and 0.10.

No threshold, feature, race grouping, or pack mechanism will be selected from wave-two
outcomes. The comparison remains exploratory and post-wave selection does not become a
binding thesis-gate result.
