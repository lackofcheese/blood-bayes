# Roster-builder rules-pack crosswalk

Assessment date: 2026-07-20. The inspected source is the sibling
`../roster-builder` checkout at commit `3bdaa2f`, including its then-uncommitted
rules-pack work. Treat the inventory as a provisional snapshot until that checkout is
committed; imports must record a manifest digest rather than rely on this assessment date.

## Decision

Use `roster-builder/data/rules-packs/*.yaml` as an evidence-bearing draft input to the
`bb-stats` pack schema. Do not use `data/formats/*.yaml` as the canonical statistical
record and do not add a runtime dependency on the sibling repository.

The rules-pack manifests preserve pinned organizer sources, normalized source tables,
editorial judgements, clause coverage, and conformance fixtures. The executable formats
are intentionally optimized for validating one roster; they omit or flatten rules that
matter to outcome and field models. Tourplay remains a non-normative observation source.

An imported value cannot enter a model-ready pack merely because the upstream manifest
is `runnable`. `runnable` means complete for single-roster validation, not complete for
`bb-stats`, and it does not certify human review of every statistical field.

## Snapshot inventory

The inspected corpus contains:

- 16 BB2025 rules-pack manifests: 13 `runnable` and three `surveyed`;
- 165 classified clauses: 132 `supported`, four `awkward`, three `gap`, and 26
  `out_of_scope` for the roster validator;
- 204 conformance fixtures and eight explicit ambiguity judgements; and
- source URL, declared version, retrieval date, and SHA-256 for every manifest.

The 26 `out_of_scope` clauses are the main statistical recovery queue. Only 11 carry
page locators. Most combine several concepts into prose such as “resurrection, pairings,
scoring, timing, and prizes”; those concepts must be revisited separately rather than
mapped to one generic flag.

## Field crosswalk

`sourceModel` is deliberately YAML-native and uses pack-specific keys. The examples
below are observed families, not a stable upstream API.

| `bb-stats` concept | Useful roster-builder evidence | Readiness and required handling |
|---|---|---|
| Pack identity and edition | `id`, `name`, `rulesEdition` | Direct after registry review. A roster-builder ID is a source ID, not automatically the canonical `pack_id`. |
| Source provenance | `source.{url,version,retrieved,sha256,living}`, `discovery`, `corroboration` | Strong. Copy the pinned document identity and the imported manifest digest. Do not copy machine-local discovery paths. |
| Legal-race choice set | `eligibleTeams`, `teams`, `tiers`, `teamTiers`, `teamSchedule`, omission lists | Partial. A race absent from a tier table may be forbidden, accidentally omitted, or supplied by a later amendment. Require an explicit legal-race decision. |
| Race-to-tier/group assignment | `tiers`, `teamTiers`, `teams`, `teamSchedule`, executable classifier tables | Usually strong. Preserve the source's group identity even when a later treatment vector makes the label unnecessary. |
| Team/treasury budget | `teamGold`, `teamGoldByTier`, `tierFunds`, `tierParams`, `teamSchedule`, `sharedGold`, `treasuryValues` | Strong but not one scalar. Keep team gold, skill gold/SPP, shared pools, and Flowing Funds distinct before deriving effective budget. |
| Primary/Secondary improvements | skill-count tables, point budgets and costs, `advancementPackages`, `upgradeSets`, `upgradeMenu`, `skillRules` | Rich but heterogeneous. Preserve every legal alternative and its accounting unit; never infer a realized coach build or collapse choice sets prematurely. |
| Stacking and repetition | per-player caps, stacked-player caps, Elite sets/caps, per-skill copy caps | Strong. Normalize player-stack, repeated-skill, and named-set restrictions as separate fields. |
| Characteristic improvements | characteristic costs, limits, result floors, package choices | Strong where present. Retain characteristic-specific constraints rather than folding them into Secondary counts. |
| Star access | caps, access teams/tiers, taxes, banned lists, named classes | Strong for roster legality. Preserve access, count, price/tax, and exclusions separately. |
| Inducement access | allow/banned lists, caps, prices, free grants, custom inducements | Strong for roster legality. Source-local entities and match-use effects need explicit evidence and an `other` escape path. |
| Games count | No consistent structured field observed | Missing. Re-open the organizer source and annotate explicitly. Do not infer from NAF match counts or schedule rows. |
| Resurrection/progression | Commonly buried in `out_of_scope` tournament-play summaries | Missing as structured data. Re-open the cited pages—or the whole document when pages are absent—and classify explicitly. |
| W/D/L scoring and bonuses | Commonly buried with tie-breaks and administration | Missing as structured data. Record base result points separately from TD/CAS bonuses, caps, tie-breakers, and squad scoring. |
| Event/open/squad structure | Occasional `tournamentKind`, `squadRules`, `squadSize`, squad costs; otherwise prose | Partial. Record event type, squad size, duplicate-race/star constraints, and whether scoring is individual or squad-level. |
| Local match-play rules | `out_of_scope` clauses such as replacement kick-off results, mandatory setup, mirrored-Star cancellation, and custom match effects | Prose only. Preserve each material rule separately in `other`, with evidence, until a reviewed feature family exists. Do not silently discard it because schema v0 has no coefficient for it. |
| Event-time amendments | `corroboration`, Tourplay amendments, discrepancy notes | Discovery evidence only unless an organizer amendment or explicit review establishes the rules actually applied. Represent an event application/patch separately from the reusable pack template. |
| Field-level evidence | Clause pages, judgement quotes/rationales, fixtures | Partial. Page references usually attach to clauses, not individual normalized values; ordinary values often have no quote. The `bb-stats` import must attach evidence and review state to every model-used field. |
| Human review | No reviewer identity, review date, or per-field approval state in the manifest contract | Missing. Upstream lint and executable fixtures demonstrate internal consistency, not independent human verification. |

## Rules that must be recovered beyond roster construction

The non-roster sweep is mandatory for every imported pack. At minimum it must make an
explicit decision for:

1. number of games and progression versus resurrection;
2. win/draw/loss points, bonus points, caps, and whether scoring is individual or squad-level;
3. legal race choice, squad size, duplicate-race and duplicate-Star constraints;
4. pairings or schedule constraints that systematically change matchup exposure;
5. local kick-off, weather, setup, casualty, or inducement-use rules that can affect W/D/L;
6. event-time amendments and the relationship between the reusable pack and each event; and
7. any remaining source clause, preserved verbatim under `other` even when it is not modeled.

Administrative rules such as venue access or miniature painting can be classified as
non-model material, but they still need a coverage decision so omission is visible.

## Import and review boundary

The pack schema should be source-independent. A draft importer may prefill it from a
roster-builder manifest, a Tourplay observation, or direct PDF extraction, but all paths
must produce the same evidence and review envelope.

For each source, store:

- stable source kind and ID, authority (`normative`, `amendment`, or
  `non_normative_observation`), URL/version/digest, and retrieval date;
- for derived sources, the upstream artifact digest and its pinned organizer-source digest;
- page/section locator and a short quote or source-faithful table reference; and
- extraction method (`manual`, `roster_builder_import`, `tourplay_import`, or
  `llm_pdf`) without treating the method as a confidence score.

For every model-used field, store evidence references and one of:

- `unreviewed` — imported or extracted but not checked by a human;
- `confirmed` — a named human checked the value against the normative source;
- `disputed` — sources or reviewers disagree; or
- `unclear` — the source does not support a safe value.

`confirmed` records require reviewer identity and review date. `disputed` and `unclear`
remain valid annotations but cannot be silently coerced to a model value. Pack-level
model readiness requires all required fields to be `confirmed` and a completed
whole-document clause sweep. The planned independent second pass on 3–4 packs remains
necessary; upstream `runnable` status does not replace it.

Authority order is:

1. a pinned final organizer document;
2. a pinned organizer amendment for the affected event or pack revision; and
3. Tourplay or another platform configuration as corroboration and discrepancy evidence.

Because the model needs rules actually applied, a reviewed event-time amendment may
override the reusable template through an explicit event-to-pack application record.
Tourplay alone never performs that override.

## Validation use

The executable roster-builder formats remain valuable as an independent consistency
check. For a reviewed `bb-stats` pack, compare mechanically derivable facts—legal races,
tier assignments, budgets, improvement choices, stacking, Stars, and inducements—against
the pinned executable format. A difference produces a review finding; it never silently
rewrites either source.

Eucalyptus Bowl is the first schema trial because it is a primary open-event target and
already has a runnable manifest. EuroBowl is the second trial because it exercises
squad-wide choice constraints and exposes the boundary between roster treatment and the
field model.

## Immediate implementation sequence

1. Incorporate the evidence/review envelope and event-application distinction into the
   schema-v0 annotation guide.
2. Hand-map the Eucalyptus manifest into a draft schema-v0 record, then perform the
   missing non-roster source sweep and human review.
3. Repeat with EuroBowl and record every schema or workflow change needed for squad rules.
4. Freeze schema v0 only after both trials validate and every source clause is classified.
5. Use manifest import to accelerate the remaining pack annotations; validate roster
   fields against executable formats and retain Tourplay as a discrepancy source.
