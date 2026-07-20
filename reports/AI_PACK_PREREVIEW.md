# AI pack pre-review

Run date: 2026-07-20. This is a reconciled agent review, not human approval. Every affected
field remains `unreviewed`, both annotations remain `draft`, and clause coverage remains
incomplete.

## Method

The normative artifacts were downloaded before review and checked against the existing
manifests. Two agents independently received each artifact, the current annotation, and the
derived roster-builder cross-check. Each was asked for a whole-document sweep with locators,
including non-roster rules and unsafe inferences. Reconciliation used the conservative value
when reviewers differed.

| Pack | Normative artifact | SHA-256 | Independent reviews |
|---|---|---|---:|
| Eucalyptus Bowl 2026 v0.4 | 17-page organizer PDF | `b5d273dc9c8adaf337aeaf8e07e130bea3f355220e4219be6449771bebf69b40` | 2 |
| EuroBowl 2026 FINAL | 1357x1920 organizer image | `d87342a1c88e4137bc774f15c7d2922fb6e6723598933f5c86cf0598bc897d84` | 2 |

## Eucalyptus reconciliation

Both reviewers independently agreed that the PDF directly establishes six games and base
scoring of 80/40/10, followed by Median Opponents Score, touchdown differential, touchdown
total, casualty differential, and casualty total. The named first tiebreak is not a statistical
median: the source examples use opponent points per game and a drop-high/drop-low trimmed sum.

Both found no explicit resurrection, recovery, injury retention, SPP, or between-game
progression rule. One reviewer proposed `open`/`individual` from the coach-level language; the
other rejected that inference because the PDF never labels the event type. Reconciliation keeps
both `progression` and `event_structure` null.

The roster transcription largely agrees with the PDF, subject to human review of:

- the exact 31-race choice set, because the PDF incorporates BB2025 and prints Slann but does
  not enumerate the other races;
- generic catalog IDs for the named Josef Bugman, Sports Wizard, and Dodgy League Rep variants;
- the apparent source typo `Plaque Doctor` normalized to `plague_doctor`;
- custom inducement costs and caps imported from catalog evidence rather than printed values;
  and
- whether the list of things bought from the shared 1.25m Gold is exhaustive.

The review recovered previously omitted clauses for an 11-player minimum, discarded unspent
Gold, the full tiebreak calculation, awards, presentation and a score-affecting painting
penalty, BBTM result handling, clocks and slow-play sanctions, local match conventions, a late
attendance default result, and conduct/removal. These are now granular `other_rules` rather
than one roster-builder `out_of_scope` placeholder.

## EuroBowl reconciliation

Both visual reviews agreed that the FINAL image directly establishes:

- all 31 teams across seven tiers and their Team Budget, Skill Gold, and Flowing Funds;
- the seven priced advancement packages and the one-package-per-player rule;
- caps on players receiving Secondary and Stack packages;
- the ten allowed inducement categories;
- tier-specific Veteran and Legend access and Skill Gold fees;
- the printed playable and banned Star lists;
- payment of ordinary Star fees from Team Budget and a minimum 11 players after hiring Stars;
  and
- the Stalling rule and reference to current BB2025 NAF recommendations.

The official page schedules six EuroBowl rounds, but it could not be cached as a verified
artifact: the direct request returned only a WAF error. The page also still calls its prose
version 0.2 while embedding the sheet labelled FINAL. Consequently no page-derived value has
been added to the annotation. Games, progression, scoring, squad size, uniqueness, pairings,
matchup procedure, and even the schema's team-versus-squad event label remain unresolved
pending a pinned current organizer source.

The direct image review exposed several source-boundary issues:

- `flowing_funds.step: 10000` is derived; the image instead says funds may be divided in any
  way and does not state a granularity;
- the four Elite skills are not named on the sheet;
- the Secondary cap is printed as a cap on players with that advancement type, not a raw skill
  count;
- characteristic improvements are absent from a closed-looking menu but not separately stated
  to be banned;
- Stars absent from both printed lists are inferred unavailable using an external catalog;
- `Scrooge Sorehead` is silently normalized to `scrappa_sorehead`; and
- the schema does not directly represent minimum roster size or the ordinary Star-price
  resource.

## Schema findings

The trials now identify changes to consider before freezing schema v0:

1. Add roster-size constraints rather than relegating explicit 11-player rules to
   `other_rules`.
2. Represent source-defined tiebreak algorithms, not only ordered labels.
3. Distinguish caps on skills, packages, and players receiving a package type.
4. Allow unknown Flowing Funds granularity instead of requiring an inferred step.
5. Preserve named inducement variants and Star display-name-to-catalog-ID mappings.
6. Let clause coverage name multiple normative artifacts for packs split across a roster sheet
   and tournament-play document.
7. Pin incorporated rules and mutable organizer pages before treating them as pack evidence.

The extraction enum now distinguishes PDF, visual, and web AI evidence. This improves source
provenance only; none of those methods can produce `confirmed` review status.

## Human handoff

The human pass should start from the added normative locators, concentrate first on the listed
ambiguities and catalog normalizations, then still sweep every artifact independently. It must
locate the missing current EuroBowl tournament-play contract and a direct Eucalyptus statement
of progression/event type, or explicitly leave those fields unresolved. Only that pass may add
reviewer identity/date, mark fields confirmed or unclear, and complete clause coverage.
