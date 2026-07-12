# Tourplay and pack-source reconnaissance

Status: preliminary public-surface check on 2026-07-13. No bulk collection or
authenticated access was performed.

## Finding

Tourplay is visibly used for tournament registration, roster submission, results, and
standings, but the public search surface did not reveal official API documentation or
public automation terms. Its React application uses compact same-origin JSON endpoints.
The public event route resolves a slug with `GET /api/tournament/{slug}`. A live response
was 1.8 KB and included the internal event ID, normalized slug, dates, country/locality,
ruleset, `isNaf`, categories, tiers, treasury budgets, race lists, inducements, and
improvement packs. The inspected response exposed NAF status but no NAF tournament ID.

The prior NBBBL worker independently confirms authenticated endpoints for tournament
inscriptions and individual rosters:

- `GET /api/inscriptions/{slug}/inscriptions`
- `GET /api/rosters/{roster_id}`

The roster response includes the selected tier improvement pack, treasury, roster race,
line-ups, skill properties, and star-player information. It is useful for later pack/build
validation but creates one-request-per-roster fan-out and is unnecessary for initial
event linking.

### Pack-configuration sample

Three exact NAF-to-Tourplay links for upcoming BB2025 events were sampled through the
single event-metadata request. All three returned configured tier data. The responses
covered race-to-tier membership, treasury, permitted inducement IDs, improvement-pack
SPP budgets, primary/secondary costs, stacking limits/costs, skill repetition limits,
star access, banned stars, and custom star costs. This demonstrates that useful pack
parameters are recoverable without loading a roster for at least some tournaments.

A tier can contain several improvement packs because the packs may be alternative legal
build branches. The correct machine-readable mapping composes `race → tier` with
`tier → improvementPacks`, yielding a legal pack choice set for each race. Danish Open's
EuroBowl 2026 rules confirm this interpretation: tiers 5–7 may choose standard,
Veterans, or Legends branches subject to tier-specific costs and mutual-exclusion rules.
A roster lookup reveals the branch actually chosen by a coach, not pack availability.

Documents remain necessary where package labels encode organiser instructions that
Tourplay does not enforce structurally, and for scoring, resurrection/progression,
bespoke rules, and normative conflict resolution.

Public tournament packs commonly link to a Tourplay event while keeping the normative
rules in a PDF. For example, the 2026 BBBL Troll Bowl V pack identifies its build rules
and separately links coaches to Tourplay for registration. Blood, Sweat & Balls 9 does
the same for roster submission. This supports treating Tourplay roster/event data and
the pack document as complementary sources rather than assuming either one is complete.

## Safe next step

1. Extract exact Tourplay slugs embedded in NAF URL and information fields; these are
   high-confidence seed links.
2. Resolve a small set through the one-request event metadata endpoint and retain raw
   responses in the ignored data cache.
3. Determine whether completed events returning HTTP 423 require authentication or a
   different archival endpoint before scaling beyond the seed set.
4. Validate any name/date/location linker against exact seed links before applying it to
   NAF events with no explicit Tourplay URL.
5. Preserve event-to-pack links with method, confidence, review status, and evidence.
6. Never accept fuzzy name/date matching without review.

## Sources checked

- Tourplay public home page: <https://tourplay.net/>
- NAF-hosted BBBL Troll Bowl V rules pack:
  <https://www.thenaf.net/tournament_files/11027/BBBL%20Troll%20Bowl%20V_Rulespack_Jun2026_v003.pdf>
- Blood, Sweat & Balls 9 rules pack:
  <https://www.blackdragongames.co.uk/downloads/BSB9_1.1.pdf>
