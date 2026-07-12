"""Normalize cached Tourplay event metadata without network access.

The output deliberately preserves Tourplay's identifiers and enum values.  In
particular, every improvement pack attached to a tier remains a separate legal
alternative; this module never infers which alternative a coach selected.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tourplay-normalized-v1"

TABLE_FIELDS = {
    "tourplay_event_link": (
        "schema_version",
        "naf_tournament_id",
        "tourplay_slug",
        "tourplay_event_id",
        "rule_set",
        "is_naf",
        "fetch_state",
        "http_status",
        "evidence_field",
        "confidence",
        "source_file",
        "source_sha256",
    ),
    "category": (
        "schema_version",
        "tourplay_event_id",
        "category_id",
        "category_type",
        "hide_rosters",
        "same_race_limit",
        "max_registrations",
        "source_sha256",
    ),
    "tier": (
        "schema_version",
        "tourplay_event_id",
        "category_id",
        "tier_id",
        "level",
        "treasury_budget",
        "min_standard_players",
        "source_sha256",
    ),
    "tier_race": (
        "schema_version",
        "tourplay_event_id",
        "category_id",
        "tier_id",
        "race_id",
        "source_sha256",
    ),
    "improvement_pack": (
        "schema_version",
        "tourplay_event_id",
        "category_id",
        "tier_id",
        "pack_id",
        "pack_name",
        "pack_order",
        "spp",
        "cost_type",
        "swap_secondaries_for_primaries",
        "global_skill_repetitions",
        "max_stacked_players",
        "source_sha256",
    ),
    "improvement_option": (
        "schema_version",
        "tourplay_event_id",
        "category_id",
        "tier_id",
        "pack_id",
        "option_id",
        "improvement_pack_type",
        "option_order",
        "max_quantity",
        "mandatory_quantity",
        "max_stack_quantity",
        "max_repetitions_quantity",
        "max_cost",
        "spp_cost",
        "spp_repeat_cost",
        "spp_stack_cost",
        "max_ctv",
        "allow_extra_gold_for_pack_budget",
        "min_standard_players",
        "source_sha256",
    ),
    "tier_inducement": (
        "schema_version",
        "tourplay_event_id",
        "category_id",
        "tier_id",
        "inducement_id",
        "source_sha256",
    ),
    "star_rule": (
        "schema_version",
        "tourplay_event_id",
        "category_id",
        "tier_id",
        "pack_id",
        "option_id",
        "rule_kind",
        "star_player_id",
        "spp_cost",
        "source_sha256",
    ),
    "mercenary_rule": (
        "schema_version",
        "tourplay_event_id",
        "category_id",
        "tier_id",
        "pack_id",
        "option_id",
        "rule_kind",
        "mercenary_id",
        "spp_cost",
        "source_sha256",
    ),
    "quarantine": ("source_file", "tourplay_slug", "reason"),
}


def _scalar(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _mapping_list(value: object, field: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValueError(f"{field} must be a list of objects")
    return list(value)


def _id(value: object, field: str) -> object:
    if value is None or isinstance(value, (str, int)):
        return value
    raise ValueError(f"{field} must be a scalar identifier")


def _base(event_id: object, checksum: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tourplay_event_id": event_id,
        "source_sha256": checksum,
    }


def _append_star_rows(
    rows: list[dict[str, object]], context: dict[str, object], option: Mapping[str, Any]
) -> None:
    for source_key, kind in (
        ("bannedStarPlayers", "banned"),
        ("megaStarPlayers", "mega"),
    ):
        values = option.get(source_key) or []
        if not isinstance(values, list):
            raise ValueError(f"{source_key} must be a list")
        for star_id in values:
            rows.append(
                {
                    **context,
                    "rule_kind": kind,
                    "star_player_id": _id(star_id, source_key),
                    "spp_cost": None,
                }
            )
    custom = option.get("customSppStarPlayers") or []
    if not isinstance(custom, list) or not all(isinstance(item, Mapping) for item in custom):
        raise ValueError("customSppStarPlayers must be a list of objects")
    for item in custom:
        rows.append(
            {
                **context,
                "rule_kind": "custom_spp_cost",
                "star_player_id": _id(item.get("id"), "custom star id"),
                "spp_cost": item.get("sppCost"),
            }
        )


def _append_mercenary_rows(
    rows: list[dict[str, object]], context: dict[str, object], option: Mapping[str, Any]
) -> None:
    banned = option.get("bannedMercenaries") or []
    if not isinstance(banned, list):
        raise ValueError("bannedMercenaries must be a list")
    for mercenary_id in banned:
        rows.append(
            {
                **context,
                "rule_kind": "banned",
                "mercenary_id": _id(mercenary_id, "bannedMercenaries"),
                "spp_cost": None,
            }
        )
    custom = option.get("customSppMercenaries") or []
    if not isinstance(custom, list) or not all(isinstance(item, Mapping) for item in custom):
        raise ValueError("customSppMercenaries must be a list of objects")
    for item in custom:
        rows.append(
            {
                **context,
                "rule_kind": "custom_spp_cost",
                "mercenary_id": _id(item.get("id"), "custom mercenary id"),
                "spp_cost": item.get("sppCost"),
            }
        )


def normalize(
    coverage_path: Path, cache_dir: Path
) -> tuple[dict[str, list[dict[str, object]]], dict[str, int]]:
    """Return normalized tables and reconciliation counters."""
    document = json.loads(coverage_path.read_text(encoding="utf-8"))
    events = document.get("events") if isinstance(document, Mapping) else None
    if not isinstance(events, list):
        raise ValueError("coverage JSON must contain an events list")
    tables = {name: [] for name in TABLE_FIELDS}
    counts = {
        "coverage_rows": len(events),
        "normalized_events": 0,
        "missing_cache": 0,
        "malformed_cache": 0,
    }
    for link in sorted(
        events,
        key=lambda row: (str(row.get("naf_tournament_id", "")), str(row.get("tourplay_slug", ""))),
    ):
        slug = str(link.get("tourplay_slug", ""))
        source = cache_dir / f"{slug}.json"
        if not source.is_file():
            tables["quarantine"].append(
                {"source_file": source.name, "tourplay_slug": slug, "reason": "missing_cache"}
            )
            counts["missing_cache"] += 1
            continue
        raw = source.read_bytes()
        checksum = hashlib.sha256(raw).hexdigest()
        try:
            payload = json.loads(raw)
            if not isinstance(payload, Mapping):
                raise ValueError("payload must be an object")
            event_id = _id(payload.get("id"), "event id")
            categories = _mapping_list(payload.get("categories"), "categories")
            pending = {name: [] for name in TABLE_FIELDS if name != "quarantine"}
            pending["tourplay_event_link"].append(
                {
                    **_base(event_id, checksum),
                    "naf_tournament_id": link.get("naf_tournament_id"),
                    "tourplay_slug": slug,
                    "rule_set": payload.get("ruleSet"),
                    "is_naf": payload.get("isNaf"),
                    "fetch_state": link.get("fetch_state"),
                    "http_status": link.get("http_status"),
                    "evidence_field": link.get("evidence_field"),
                    "confidence": link.get("confidence"),
                    "source_file": source.name,
                }
            )
            for category in categories:
                category_id = _id(category.get("id"), "category id")
                pending["category"].append(
                    {
                        **_base(event_id, checksum),
                        "category_id": category_id,
                        "category_type": category.get("type"),
                        "hide_rosters": category.get("hideRosters"),
                        "same_race_limit": category.get("sameRaceLimit"),
                        "max_registrations": category.get("maxRegistrations"),
                    }
                )
                for tier in _mapping_list(category.get("tiers"), "tiers"):
                    tier_id = _id(tier.get("id"), "tier id")
                    context = {
                        **_base(event_id, checksum),
                        "category_id": category_id,
                        "tier_id": tier_id,
                    }
                    pending["tier"].append(
                        {
                            **context,
                            "level": tier.get("level"),
                            "treasury_budget": tier.get("treasuryBudget"),
                            "min_standard_players": tier.get("minStandardPlayers"),
                        }
                    )
                    team_races = tier.get("teamRaces") or []
                    if not isinstance(team_races, list):
                        raise ValueError("teamRaces must be a list")
                    for race_id in team_races:
                        pending["tier_race"].append({**context, "race_id": _id(race_id, "race id")})
                    inducements = tier.get("inducements") or []
                    if not isinstance(inducements, list):
                        raise ValueError("inducements must be a list")
                    for inducement_id in inducements:
                        pending["tier_inducement"].append(
                            {**context, "inducement_id": _id(inducement_id, "inducement id")}
                        )
                    for pack in _mapping_list(tier.get("improvementPacks"), "improvementPacks"):
                        pack_id = _id(pack.get("id"), "pack id")
                        pack_context = {**context, "pack_id": pack_id}
                        pending["improvement_pack"].append(
                            {
                                **pack_context,
                                "pack_name": pack.get("name"),
                                "pack_order": pack.get("order"),
                                "spp": pack.get("spp"),
                                "cost_type": pack.get("costType"),
                                "swap_secondaries_for_primaries": pack.get(
                                    "swapSecondariesForPrimaries"
                                ),
                                "global_skill_repetitions": pack.get("globalSkillRepetitions"),
                                "max_stacked_players": pack.get("maxStackedPlayers"),
                            }
                        )
                        for option in _mapping_list(pack.get("options"), "options"):
                            option_id = _id(option.get("id"), "option id")
                            option_context = {**pack_context, "option_id": option_id}
                            pending["improvement_option"].append(
                                {
                                    **option_context,
                                    "improvement_pack_type": option.get("improvementPackType"),
                                    "option_order": option.get("order"),
                                    "max_quantity": option.get("maxQuantity"),
                                    "mandatory_quantity": option.get("mandatoryQuantity"),
                                    "max_stack_quantity": option.get("maxStackQuantity"),
                                    "max_repetitions_quantity": option.get(
                                        "maxRepetitionsQuantity"
                                    ),
                                    "max_cost": option.get("maxCost"),
                                    "spp_cost": option.get("sppCost"),
                                    "spp_repeat_cost": option.get("sppRepeatCost"),
                                    "spp_stack_cost": option.get("sppStackCost"),
                                    "max_ctv": option.get("maxCtv"),
                                    "allow_extra_gold_for_pack_budget": option.get(
                                        "allowExtraGoldForPackBudget"
                                    ),
                                    "min_standard_players": option.get("minStandardPlayers"),
                                }
                            )
                            _append_star_rows(pending["star_rule"], option_context, option)
                            _append_mercenary_rows(
                                pending["mercenary_rule"], option_context, option
                            )
            for name, rows in pending.items():
                tables[name].extend(rows)
            counts["normalized_events"] += 1
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as error:
            tables["quarantine"].append(
                {"source_file": source.name, "tourplay_slug": slug, "reason": str(error)}
            )
            counts["malformed_cache"] += 1
    return tables, counts


def _write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _scalar(row.get(field)) for field in fields})


def write_output(coverage_path: Path, cache_dir: Path, output_dir: Path) -> dict[str, int]:
    tables, counts = normalize(coverage_path, cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".tourplay-stage-", dir=output_dir.parent) as temporary:
        stage = Path(temporary)
        for name, fields in TABLE_FIELDS.items():
            _write_csv(stage / f"{name}.csv", fields, tables[name])
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "coverage_sha256": hashlib.sha256(coverage_path.read_bytes()).hexdigest(),
            "tables": {name: len(rows) for name, rows in tables.items()},
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (stage / "reconciliation.json").write_text(
            json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        for staged in sorted(stage.iterdir()):
            os.replace(staged, output_dir / staged.name)
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument("cache_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    counts = write_output(args.coverage_json, args.cache_dir, args.output_dir)
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
