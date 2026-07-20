"""Preliminary schema-informed pack-feature signal probe.

This is a frozen pipeline rehearsal over Tourplay legal-option envelopes. It is not a
confirmatory pack-effect analysis and does not promote unreviewed pack annotations.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

from bb_stats.analysis.exploratory_signal import (
    _load_games,
    _number,
    _race_key,
    _rows,
    candidate_connectivity,
    permutation_benchmark,
    raw_feature_probe,
    residual_cells,
)

MAX_ROSTER_SIZE = 16
TIER_FEATURES = ("relative_tier",)
MECHANISM_FEATURES = (
    "team_gold_k",
    "primary_capacity_max",
    "secondary_capacity_max",
    "star_quantity_max",
    "extra_gold_k_max",
)
FEATURES = TIER_FEATURES + MECHANISM_FEATURES


def _bounded_quantity(value: str) -> float:
    quantity = max(0.0, _number(value))
    return min(float(MAX_ROSTER_SIZE), quantity)


def _advancement_capacity(
    pack: dict[str, str], options: list[dict[str, str]], kind: str
) -> float | None:
    matching = [option for option in options if option["resolved_enum_key"] == kind]
    if not matching:
        return 0.0
    capacities = []
    for option in matching:
        maximum = _bounded_quantity(option["max_quantity"])
        if pack["cost_type"] in {"1", "2"}:
            budget = _number(pack["spp"])
            cost = _number(option["spp_cost"])
            if budget <= 0 or cost <= 0:
                return None
            maximum = min(maximum, math.floor(budget / cost))
        capacities.append(maximum)
    return max(capacities, default=0.0)


def schema_informed_feature_map(
    tourplay_dir: Path, resolved_dir: Path
) -> tuple[dict[tuple[str, str], dict[str, float]], dict[str, dict[str, str]]]:
    """Return legal availability envelopes keyed by NAF event and normalized race name."""

    links = {
        row["tourplay_event_id"]: row
        for row in _rows(tourplay_dir / "tourplay_event_link.csv")
        if row["fetch_state"] == "cached" and row["http_status"] == "200"
    }
    tiers = {row["tier_id"]: row for row in _rows(tourplay_dir / "tier.csv")}
    category_max_level: dict[tuple[str, str], int] = defaultdict(int)
    for tier in tiers.values():
        key = (tier["tourplay_event_id"], tier["category_id"])
        category_max_level[key] = max(category_max_level[key], int(tier["level"]))

    tier_packs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for pack in _rows(tourplay_dir / "improvement_pack.csv"):
        tier_packs[pack["tier_id"]].append(pack)
    pack_options: dict[str, list[dict[str, str]]] = defaultdict(list)
    for option in _rows(resolved_dir / "resolved_improvement_option.csv"):
        if option["resolution_status"] == "resolved":
            pack_options[option["pack_id"]].append(option)

    candidates: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    for row in _rows(resolved_dir / "resolved_tier_race.csv"):
        link = links.get(row["tourplay_event_id"])
        tier = tiers.get(row["tier_id"])
        if link is None or tier is None or row["resolution_status"] != "resolved":
            continue
        primary_capacities = []
        secondary_capacities = []
        star_quantities = []
        extra_gold = []
        unsafe = False
        for pack in tier_packs[row["tier_id"]]:
            options = pack_options[pack["pack_id"]]
            primary = _advancement_capacity(pack, options, "Primary")
            secondary = _advancement_capacity(pack, options, "Secondary")
            if primary is None or secondary is None:
                unsafe = True
                break
            primary_capacities.append(primary)
            secondary_capacities.append(secondary)
            star_quantities.extend(
                _bounded_quantity(option["max_quantity"])
                for option in options
                if option["resolved_enum_key"] == "StarPlayer"
            )
            extra_gold.extend(
                _number(option["max_cost"])
                for option in options
                if option["resolved_enum_key"] == "ExtraGold"
            )
        if unsafe:
            continue
        max_level = category_max_level[(row["tourplay_event_id"], row["category_id"])]
        level = int(tier["level"])
        values = {
            "relative_tier": (level - 1) / (max_level - 1) if max_level > 1 else 0.0,
            "team_gold_k": _number(tier["treasury_budget"]),
            "primary_capacity_max": max(primary_capacities, default=0.0),
            "secondary_capacity_max": max(secondary_capacities, default=0.0),
            "star_quantity_max": max(star_quantities, default=0.0),
            "extra_gold_k_max": max(extra_gold, default=0.0),
        }
        key = (link["naf_tournament_id"], _race_key(row["resolved_display_name"]))
        candidates[key].append(values)

    result = {}
    for key, values in candidates.items():
        distinct = {tuple(value[name] for name in FEATURES) for value in values}
        if len(distinct) == 1:
            result[key] = values[0]
    return result, {row["naf_tournament_id"]: row for row in links.values()}


def run(naf_dir: Path, tourplay_dir: Path, resolved_dir: Path, output: Path) -> dict[str, object]:
    games, race_names = _load_games(naf_dir)
    feature_map, links = schema_informed_feature_map(tourplay_dir, resolved_dir)
    candidate_rows, connectivity = candidate_connectivity(
        games, set(links), minimum_coaches=40
    )
    selected = {str(row["event_id"]) for row in candidate_rows}
    cells = residual_cells(games, selected, race_names)

    probes = {}
    for name, feature_names in (
        ("tier_only", TIER_FEATURES),
        ("mechanisms_only", MECHANISM_FEATURES),
        ("tier_plus_mechanisms", FEATURES),
    ):
        probes[name] = raw_feature_probe(cells, feature_map, feature_names)
    mechanism = probes["mechanisms_only"]
    mechanism["permutation_benchmark"] = permutation_benchmark(
        cells,
        feature_map,
        float(mechanism["equal_event_mean_mse_improvement"]),
        MECHANISM_FEATURES,
    )

    report = {
        "status": "preliminary_non_binding",
        "protocol": "reports/PACK_SIGNAL_PROTOCOL.md",
        "warnings": [
            "Features are legal availability envelopes, not realized roster choices.",
            "The same outcomes informed earlier reconnaissance; this is not confirmatory.",
            "Unreviewed pack annotations are not promoted or used as authoritative values.",
        ],
        "connectivity": connectivity["summary"],
        "feature_coverage": {
            "event_race_envelopes": len(feature_map),
            "events_with_envelopes": len({event for event, _race in feature_map}),
            "selected_events": len(selected),
            "selected_events_with_envelopes": len(
                selected & {event for event, _race in feature_map}
            ),
            "residual_cells": len(cells),
        },
        "feature_probes": probes,
        "secondary_increment_over_tier": (
            float(probes["tier_plus_mechanisms"]["equal_event_mean_mse_improvement"])
            - float(probes["tier_only"]["equal_event_mean_mse_improvement"])
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    rows = [
        {"event_id": event, "race": race, **values}
        for (event, race), values in sorted(feature_map.items(), key=lambda item: item[0])
    ]
    if rows:
        with (output / "feature_envelopes.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("naf", type=Path)
    parser.add_argument("tourplay", type=Path)
    parser.add_argument("resolved", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.naf, args.tourplay, args.resolved, args.output), indent=2))


if __name__ == "__main__":
    main()
