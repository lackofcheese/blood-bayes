# Deferred pack reviews

Human review was deliberately deferred on 2026-07-20 while the project remains in
preliminary-testing mode. This is a deferral, not a waiver.

## Allowed before review

- schema, ingestion, feature-engineering, and power-pipeline development;
- explicitly exploratory analyses that retain `draft` / `unreviewed` provenance;
- tests of missing-data behavior and sensitivity to uncertain pack fields; and
- AI-assisted source reconnaissance whose findings remain unreviewed.

## Promotion gate

Before any pack is marked `model_ready`, schema v0 is frozen, a confirmatory pack-effect
analysis is run, or a result is presented as relying on authoritative pack values:

1. a named human must re-open every pinned normative artifact;
2. every required field must be confirmed, disputed, or marked unclear with direct evidence;
3. the whole-document clause sweep must be completed; and
4. unresolved source/version and schema findings must be dispositioned.

## Queue

| Pack | Current state | Highest-priority unresolved items |
|---|---|---|
| Eucalyptus Bowl 2026 v0.4 | `draft`, all fields `unreviewed` | progression; event type; external rules versions; inducement normalizations; schema gaps for roster size and local rules |
| EuroBowl 2026 FINAL | `draft`, all fields `unreviewed` | current tournament-play source; games/scoring/progression; team-versus-squad semantics; Flowing Funds granularity; catalog normalizations |

The reconciled AI queue is in `reports/AI_PACK_PREREVIEW.md`. Pack lint warnings are the
machine-enforced reminder: they must not be suppressed merely to make preliminary output look
complete.
