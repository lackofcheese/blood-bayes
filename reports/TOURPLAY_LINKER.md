# NAF to Tourplay recovery reconnaissance

Run date: 2026-07-13. This report discovers candidate links; it does not promote them
into the trusted exact-link corpus or fetch pack details without review.

## Lowest-request discovery surface

The cached Tourplay application bundle exposes three public browser endpoints:

- `GET /api/tournament?type=10&page=N`: 200 tournament cards per page;
- `GET /api/tournament/filter?type=10&filter=<term>`: name autocomplete;
- `GET /api/tournament/{slug}`: canonical tournament metadata and rules configuration.

Six polite list requests cached 1,200 tournament cards spanning July 2026 back through
March 2025, the NAF BB2025-variant event window. Each card supplies name, canonical slug,
start/end dates, country, locality/region, ruleset, NAF flag, mode, and registration
count. Pagination is therefore far cheaper than one search request—or one agent—per NAF
event. Raw pages are checksummed under ignored `data/raw/tourplay/tournament-pages/`.

## Offline linker

The linker considers only the 650 NAF variant-15 events with played games. It compares
Tourplay ruleset-25 cards within two days using normalized full/year-stripped name,
date, static country mapping, and soft locality similarity. A candidate requires:

- combined score at least `0.82`;
- name similarity at least `0.80`; and
- runner-up margin at least `0.08`.

Candidates remain review-only. Date and locality are soft because stale organizer dates,
UTC boundaries, venue names, and reused series names occur in the exact seeds.

Of 65 previously exact-linked NAF events, 64 canonical slugs occur in the six listing
pages and 60 rank first. Fifty-three pass the conservative threshold with the identical
slug. Two apparent confident slug disagreements are `Craba Bowl II → craba-bowl-2` and
`Burdin Bowl 2026 → burdin-bowl-2026`; these look like current canonical aliases for
older embedded slugs and require ID/detail confirmation rather than automatic rejection.
Both embedded slugs actually point to BB2020 configurations, while the proposed current
slugs are BB2025, NAF-marked, and match the NAF events' 2026 dates. Exact embedded links
are strong evidence, but not infallible ground truth.
The validation is therefore promising but not yet a precision certificate.

The first pass proposes 165 review candidates among the 585 previously unlinked events:
83 have at least 25 playing coaches, 28 at least 40, and 11 at least 60. Together they
cover 10,430 NAF matches across 26 countries.
The generated report preserves scores, margins, known-seed ranks, and rejected/ambiguous
rows so thresholds can be audited rather than silently tuned.

## Independent Luna-per-example benchmark

Two cheap Luna agents independently reviewed geographically distinct candidates:

- NAF `9427`, Waterbowl 2026 → `waterbowl-2026`: exact name and dates, GB/Stockport,
  Tourplay NAF flag, BB2025 rules, and 106 Tourplay registrations versus 103 NAF entries.
- NAF `10403`, XIX Tilean Team Cup 2026 → `tilean-team-cup-2026`: exact dates,
  Italy/Gorle, team mode, Tourplay NAF flag, and 291 registrations versus 286 NAF entries.

Both reviewers classified their candidate as linked with strong metadata evidence. This
is evidence that agents are useful for the ambiguity/review tail, not justification for
spawning one per all 585 events. Pagination plus deterministic scoring should handle the
bulk; Luna review should concentrate on high-value near-ties, aliases, and date conflicts.

## Scaling recommendation

1. Freeze listing-page checksums and candidate thresholds.
2. Confirm current-slug aliases against event IDs/details.
3. Manually or Luna-review a stratified labeled sample, including confident candidates,
   near-ties, and proposed negatives; estimate precision before promotion.
4. Fetch one compact detail response only for reviewed accepted slugs, with the existing
   delay, cache, hard cap, and blocked-response stopping rules.
5. Re-run coverage, connectivity, and tier-power diagnostics on the expanded trusted set.

The agent-per-example extreme remains a useful quality benchmark. It is not the cheapest
primary recovery method now that six list requests expose the whole date window.
