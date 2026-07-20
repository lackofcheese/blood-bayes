# Pack schema v0 annotation guide

Schema v0 records the rules offered by a reusable tournament pack. It does not record a
coach's realized roster, and it does not assume a platform configuration is authoritative.

## Source order

1. Pin the final organizer document as `normative` with URL, version, retrieval date, and
   SHA-256.
2. Add organizer amendments as separate `amendment` sources. Apply them only through an
   explicit event application when they do not create a new reusable pack revision.
3. Add roster-builder manifests/formats as `derived_transcription` and Tourplay as
   `non_normative_observation`. Each derived artifact records its own digest and the pinned
   repository commit.
4. Disagreement never resolves silently. Record it as a `disputed` field review and state why.

## Evidence and review

Values and review metadata are deliberately separate. `evidence` identifies a source locator
and quote or structured table reference. `field_reviews` maps each model-relevant block to its
evidence and status:

- `unreviewed`: imported or extracted, with no human approval;
- `confirmed`: checked by a named human against the normative source;
- `disputed`: a named human found incompatible evidence;
- `unclear`: a named human could not obtain a safe value from the source.

Only `confirmed` counts toward model readiness. A model-ready annotation also requires a named,
dated whole-document clause sweep. Agent review, upstream `runnable` status, executable tests,
and agreement between two derived sources are useful checks but are not human confirmation.

### Optional AI pre-review

AI can prepare the human review queue, but cannot approve it:

1. Pin and checksum the complete normative artifact before extraction.
2. Give the same artifact and current draft to two independent agents. Require page or visual
   locators and a whole-document sweep, including rules outside roster construction.
3. Reconcile their reports. Transcribe facts only when the normative artifact states them;
   preserve disagreements and unsupported inferences as explicit review findings.
4. Record direct AI evidence as `llm_pdf`, `llm_visual`, or `llm_web`, as appropriate. A web
   fact must not enter the pack merely from an unpinned search result or blocked cache.
5. Keep affected fields `unreviewed`, the annotation `draft`, and human clause coverage
   incomplete. Agent names do not populate the human reviewer fields.
6. Hand the reconciled locators, ambiguities, and schema gaps to a human, who re-opens every
   normative source and remains responsible for confirmation and the final clause sweep.

The required schema-v0 review paths are:

- `legal_races` and `race_groups`;
- one `groups.<group_id>` block for every treatment group;
- `global_rules.games`, `.progression`, `.scoring`, and `.event_structure`; and
- `other_rules`.

## Annotation procedure

1. Create the source and evidence registries before copying normalized values.
2. Transcribe the legal-race choice set explicitly. Absence from a tier table is not proof that
   a race is forbidden.
3. Define treatment groups in source units. Keep Team Gold, skill Gold, SPP, selections, shared
   pools, packages, and Flowing Funds distinct.
4. Preserve every legal improvement alternative. Do not select a representative build.
5. Record stacking, per-skill repetition, Stars, and inducements separately.
6. Sweep the entire document for games, resurrection/progression, scoring, event/squad rules,
   pairing constraints, and local match-play rules. Do not inherit roster-builder's
   `out_of_scope` classification.
7. Put material rules without a schema-v0 feature in `other_rules` with
   `materiality: needs_review` or `not_modelled`. Administrative clauses are `admin_only`.
8. Compare roster-relevant facts with the pinned executable format and Tourplay observation.
   Differences create review findings; they never rewrite the organizer source automatically.
9. Run `bb-stats-pack-lint packs/drafts/<file>.yaml`.

## Trial and freeze rule

Eucalyptus Bowl is the open-event trial; EuroBowl is the squad-event trial. Both remain drafts
until a human re-opens their normative sources and completes the missing non-roster sweep. Freeze
schema v0 only after those two reviews identify no required structural change.
