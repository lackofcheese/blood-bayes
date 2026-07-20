# Pack schema v0 trial status

Run date: 2026-07-20. Schema v0 is implemented but not frozen. The two trial records are
evidence-bearing imports, not human-approved annotations.

## Implemented boundary

`src/bb_stats/packs.py` now provides strict Pydantic models and semantic lints for:

- normative, amendment, derived-transcription, and non-normative observation sources;
- source and upstream-artifact SHA-256 provenance;
- evidence locators, extraction methods, and block-level field reviews;
- human review states with mandatory reviewer/date metadata;
- whole-document clause coverage;
- legal-race choice sets and race-to-treatment-group mappings;
- Team Gold, skill-funding modes, Flowing Funds, improvement packages and caps;
- Star and inducement policies;
- games, progression, scoring, event structure, and unmodeled material rules; and
- explicit, reviewed event-to-pack patches for organizer amendments.

Unknown keys fail validation. Legal races must cover the race-group mapping exactly,
group references must resolve, and BB2025 race IDs are checked. Model-ready annotations
must have complete global rules, complete clause coverage, and human-confirmed normative
evidence for every required block. Tourplay-only or derived-only evidence cannot satisfy
that gate.

## Eucalyptus Bowl trial

`packs/drafts/eucalyptus-bowl-2026-v0.4.yaml` imports the pinned roster-builder manifest
and executable-format facts at commit `5d650dc`:

- 31 legal BB2025/NAF races in one treatment group;
- 1.25m shared Team Gold;
- 20k Primary and 30k Elite Primary skill prices;
- one added skill per player, no Secondary or characteristic improvements;
- four-copy caps for Block, Dodge, Guard, and Mighty Blow;
- Star Players banned; and
- the executable inducement allow-list, retained as derived cross-check evidence.

Two independent AI sweeps added direct PDF locators, six games, 80/40/10 scoring and ordered
tiebreakers, plus granular non-roster clauses. Human review remains required for every block.
Progression and event structure remain null because the PDF does not state them; the reviewer
must not infer resurrection or open/individual structure from the fixed roster and coach-level
language.

## EuroBowl trial

`packs/drafts/eurobowl-2026-final.yaml` imports:

- all 31 races across seven source tiers;
- tier-specific Team Gold, skill Gold, and Flowing Funds;
- all seven Primary/Secondary/Elite/Stack packages;
- per-player, Secondary, and Stack caps;
- tier-dependent Veteran and Legend access and fees;
- banned/unavailable Star lists and advancement restrictions; and
- the ten-entry inducement allow-list.

Two independent visual sweeps added direct locators for the tier, funds, advancement,
inducement, and Star panels. The FINAL roster image does not by itself establish event type,
games, resurrection, scoring, squad size, uniqueness, pairing, or match procedure, so those
fields remain null. The official page shows six rounds but could not be cached as a verified
artifact and still carries stale v0.2 prose. Human review must identify and pin authoritative
surrounding documents rather than fill those fields from community knowledge.

## Verification result

Both YAML records parse and pass structural/semantic lint with no errors. Their lint output
consists only of expected `unreviewed` warnings: eight required review blocks for Eucalyptus
and fourteen for EuroBowl. The reconciled AI findings are recorded in
`reports/AI_PACK_PREREVIEW.md`. Tests seed unknown keys, missing race mappings, unknown race
IDs, incoherent scoring, incomplete model readiness, and non-normative event patches; each
fails as intended.

## Human handoff and freeze gate

For each trial, a human reviewer must:

1. verify the pinned normative artifact digest and version;
2. check every imported roster block against the organizer source;
3. add direct quotes or source-faithful table locators to normative evidence;
4. sweep every page/section for non-roster and administrative clauses;
5. resolve or explicitly mark discrepancies as `disputed` or `unclear`;
6. supply games, progression, scoring, and event-structure facts; and
7. record reviewer identity/date and complete clause coverage.

Schema v0 should be revised if either review needs a concept that cannot be represented
without flattening meaning. It may be frozen only after both trials complete and the
≤60-minute annotation target is measured rather than assumed.
