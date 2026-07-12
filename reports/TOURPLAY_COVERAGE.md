# BB2025 Tourplay pack-data coverage

Run date: 2026-07-13. Source: NAF export dated 2026-07-11. This is a
source-feasibility report, not the final gate-corpus selection.

## Bounded exact-link result

- 650 BB2025 events have recorded NAF games.
- 69 have an exact Tourplay event URL in NAF URL or information fields.
- 65/69 returned compact public event metadata; four returned HTTP 423.
- All 65 successful responses contained tiers, race membership, and treasury.
- 64/65 contained improvement packs and stacking fields.
- 55 contained explicit primary/secondary SPP costs; 57 exposed star configuration.
- 24 event links had exactly one improvement pack per tier.
- 40 had multiple legal improvement-pack alternatives in at least one tier.
- All 64 events with improvement packs have a direct machine-readable mapping from
  race to its legal pack choice set by composing race→tier and tier→packs.

Successful JSON responses are cached locally and ignored by Git. No inscriptions or
rosters were requested during this coverage run.

## Initial hard-floor intersection

Twenty events both expose improvement-pack metadata and have at least 25 coaches
observed in NAF games. `single` means every tier has one pack; `choice set` means at
least one tier offers multiple legal alternatives.

| NAF ID | Event | Coaches | Country | Squad | Mapping |
|---:|---|---:|---|---|---|
| 11258 | XI Vic Bowl | 98 | Spain | no | single |
| 10924 | Danish Open (Danish National 2026) | 64 | Denmark | no | choice set |
| 10926 | Roccageddon 3° Ed! | 40 | Italy | no | choice set |
| 11033 | Alpine Team Bowl | 45 | Austria | no | choice set |
| 10585 | Barton Bowl V | 50 | England | no | choice set |
| 11488 | (Road to) Hungarian Premier | 36 | Hungary | yes | choice set |
| 10790 | Wibble Bowl 2026 | 42 | England | no | single |
| 11220 | The Three Counties Bloodbowl Doubles #Euro26 | 40 | England | no | choice set |
| 11151 | Maule Bowl V | 32 | France | yes | choice set |
| 10769 | Ashes Bowl 2026 | 27 | Ireland | no | choice set |
| 11201 | The Bloodbonnet Bowl Classic 2026 | 46 | United States | no | single |
| 11014 | O Rety'Mania IV: Good to Be Back | 30 | Poland | no | choice set |
| 10833 | Worcester Floodbowl | 34 | England | no | single |
| 11149 | Lëtz play: Moien Open 3 | 36 | Luxembourg | no | single |
| 11261 | HUBBLe Open | 32 | Finland | no | choice set |
| 10784 | PTG Bowl | 28 | England | no | single |
| 11237 | Risky Rollers Winter Cup 2026 | 25 | Australia | no | choice set |
| 10905 | MBBS Winter 2026 | 29 | Russia | no | choice set |
| 10744 | Savage Cup 2026 | 34 | Italy | no | choice set |
| 11313 | Highlander 3 | 26 | Canada | no | choice set |

Only two meet the preferred 60-coach threshold. This list therefore demonstrates that
a machine-readable 20-event corpus is possible, but does not by itself satisfy the
desired balance of size, region, squad/open format, treatment contrast, or connectivity.
Those criteria must be applied before freezing the corpus.

## Remaining work

1. Interpret Tourplay race, inducement, star, and improvement-pack type IDs.
2. Preserve multiple legal alternatives per race rather than collapsing them to the
   package selected by an observed roster.
3. Audit scoring, resurrection/progression, games, and bespoke rules against documents;
   event metadata is not assumed normative.
4. Review human-authored package labels and source documents where Tourplay may encode
   organiser instructions without enforcing them structurally.
5. Search beyond exact NAF-embedded Tourplay links using a linker validated against the
   exact seed set, especially for large and squad events.
6. Apply treatment-spread and coach-connectivity criteria before annotation.
