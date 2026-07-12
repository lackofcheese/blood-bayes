"""Shared names and field contracts for derived analytical tables.

These contracts deliberately contain opaque coach identifiers, never coach names or
contact details. Source-specific readers may see personal data, but derived tables and
reports must not reproduce it.
"""

from __future__ import annotations

NAF_SOURCE_FILES = (
    "CoachExport.csv",
    "naf_variants.csv",
    "naf_tournament_statistics_group.csv",
    "naf_game.csv",
    "naf_race.csv",
    "naf_tournament_statistics_list.csv",
    "naf_tournament.csv",
    "naf_coachranking_variant.csv",
    "naf_tournamentcoach.csv",
)

MATCH_FIELDS = (
    "match_id",
    "event_id",
    "played_on",
    "variant_id",
    "home_coach_id",
    "away_coach_id",
    "home_race_id",
    "away_race_id",
    "home_touchdowns",
    "away_touchdowns",
    "home_result",
    "away_result",
    "home_badly_hurt",
    "away_badly_hurt",
    "source_dirty",
)

EVENT_FIELDS = (
    "event_id",
    "name",
    "start_date",
    "end_date",
    "nation",
    "city",
    "event_type",
    "style",
    "scoring_text",
    "is_squad",
    "variant_id",
    "ruleset_id",
    "source_url",
    "notes_url",
    "ruleset_file_reference",
    "has_information_text",
)

ENTRY_FIELDS = ("event_id", "coach_id", "race_id")
COACH_FIELDS = ("coach_id", "country", "registration_date")
RACE_FIELDS = ("race_id", "name", "reroll_cost", "allows_apothecary", "is_counted")

# This registry separates an observed event from the pack that governed it. Multiple
# events may use one pack, and successive editions of one event may use different packs.
PACK_SOURCE_LINK_FIELDS = (
    "event_id",
    "pack_id",
    "source_system",
    "source_event_id",
    "source_url",
    "link_method",
    "link_confidence",
    "review_status",
    "evidence",
    "retrieved_at",
)

BB2020_VARIANT_ID = "13"
BB2025_VARIANT_ID = "15"
