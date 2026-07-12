# Tourplay identifier coverage

Run date: 2026-07-13. Inputs are cached and checksummed; registry construction performs
no network access.

The current Tourplay application bundle and BB2020/BB2025 master-data responses resolve:

- 173 race enum IDs;
- all 65 race IDs observed in the normalized pack corpus;
- all 12 observed improvement-pack types, from a 15-value application enum;
- all observed pack cost types;
- all 34 observed inducement master IDs and their versioned names/costs;
- all 110 observed star-player IDs and their versioned names.

Examples include `3001 → Amazon` under BB2025 and `3022 → Shambling Undead`. The
registry keeps Tourplay's enum key, display name, ruleset, and roster-master ID separate
so edition-specific source identities remain auditable.

Seven observed IDs remain unresolved. They are event-specific fabulous-mercenary IDs
(`13468`, `13470`–`13475`) absent from both the roster/inducement master payload and the
generic mercenary-template endpoint. They remain raw, explicit, and quarantined from
semantic interpretation; they are not required to resolve ordinary race, skill, star,
or inducement treatment fields.

The enum source is the cached application bundle with SHA-256
`8643f1610bf5837b4a6fb2ec448a80d31c3acb3f57e644c3606d70731c1a148e`.

## Authoritative event cross-check

NAF tournament `10924`, Danish Open (Danish National 2026), links directly to
Tourplay event `20949`. Its published rules delegate roster construction to the
EuroBowl 2026 rules. Comparing those rules with the normalized and resolved Tourplay
metadata gives an exact match on:

- tier membership and team budgets of 1,070/1,070/1,080/1,100/1,120/1,140/1,150;
- skill-gold allowances of 120/140/160/190/220/240/270;
- Flowing Funds of 10/20/30/30/30/40/50, encoded as resolved `ExtraGold` options;
- no Veteran or Legend branch for tiers 1–4;
- for tier 5, either one or two Veterans at 50 each, or one Legend at 100;
- for tiers 6–7, either one or two Veterans at 40 each, or one Legend at 80.

The Veteran and Legend alternatives are separate legal improvement packs for the same
tier. They are therefore a choice set, not race assignments. Team rosters would show
which branch a coach realized, but are unnecessary for recovering which branches the
tournament allowed.

This comparison validates the interpretation of the relevant Tourplay fields against
an independent human-readable rules source. It is one event-level validation, not a
claim that every organizer configured Tourplay without error.
