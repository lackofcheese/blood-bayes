"""Exploratory, non-binding signal probes over NAF and literal Tourplay fields.

This is deliberately not the treatment-schema gate.  It asks whether event-by-race
residual variation is measurable and whether a deliberately crude representation of
machine-readable legal options predicts any of it under grouped event holdout.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

RESOURCE_FEATURES = (
    "treasury_budget",
    "legal_pack_count",
    "pack_currency_min",
    "pack_currency_max",
    "max_stacked_players",
    "primary_cost_min",
    "secondary_present",
    "secondary_cost_min",
    "star_present",
    "star_quantity_max",
    "extra_gold_max",
)
TIER_FEATURES = ("relative_tier",)
FEATURES = TIER_FEATURES + RESOURCE_FEATURES


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _minimum(values: list[float]) -> float:
    return min(values) if values else 0.0


def _maximum(values: list[float]) -> float:
    return max(values) if values else 0.0


def _race_key(name: str) -> str:
    aliases = {"elf union": "elven union"}
    key = " ".join(name.lower().replace("-", " ").split())
    return aliases.get(key, key)


@dataclass(frozen=True)
class Game:
    event: str
    home_coach: str
    away_coach: str
    home_race: str
    away_race: str
    home_score: float


def _load_games(naf_dir: Path) -> tuple[list[Game], dict[str, str]]:
    race_names = {row["race_id"]: row["name"] for row in _rows(naf_dir / "race.csv")}
    games = []
    for row in _rows(naf_dir / "match.csv"):
        if row["variant_id"] != "15" or row["home_result"] not in {"W", "D", "L"}:
            continue
        score = {"W": 1.0, "D": 0.5, "L": 0.0}[row["home_result"]]
        games.append(
            Game(
                event=row["event_id"],
                home_coach=row["home_coach_id"],
                away_coach=row["away_coach_id"],
                home_race=row["home_race_id"],
                away_race=row["away_race_id"],
                home_score=score,
            )
        )
    return games, race_names


def literal_feature_map(
    tourplay_dir: Path, resolved_dir: Path
) -> tuple[dict[tuple[str, str], dict[str, float]], dict[str, dict[str, str]]]:
    """Return literal legal-option summaries keyed by NAF event and race-name key."""

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
    packs = _rows(tourplay_dir / "improvement_pack.csv")
    options = _rows(resolved_dir / "resolved_improvement_option.csv")
    tier_packs: dict[str, list[dict[str, str]]] = defaultdict(list)
    pack_options: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in packs:
        tier_packs[row["tier_id"]].append(row)
    for row in options:
        pack_options[row["pack_id"]].append(row)

    candidates: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    for row in _rows(resolved_dir / "resolved_tier_race.csv"):
        link = links.get(row["tourplay_event_id"])
        tier = tiers.get(row["tier_id"])
        if link is None or tier is None or row["resolution_status"] != "resolved":
            continue
        legal_packs = tier_packs[row["tier_id"]]
        legal_options = [option for pack in legal_packs for option in pack_options[pack["pack_id"]]]

        def typed(
            key: str, options: list[dict[str, str]] = legal_options
        ) -> list[dict[str, str]]:
            return [option for option in options if option["resolved_enum_key"] == key]

        primary = typed("Primary")
        secondary = typed("Secondary")
        stars = typed("StarPlayer")
        extra_gold = typed("ExtraGold")
        max_level = category_max_level[(row["tourplay_event_id"], row["category_id"])]
        level = int(tier["level"])
        values = {
            "relative_tier": (level - 1) / (max_level - 1) if max_level > 1 else 0.0,
            "treasury_budget": _number(tier["treasury_budget"]),
            "legal_pack_count": float(len(legal_packs)),
            "pack_currency_min": _minimum([_number(pack["spp"]) for pack in legal_packs]),
            "pack_currency_max": _maximum([_number(pack["spp"]) for pack in legal_packs]),
            "max_stacked_players": _maximum(
                [_number(pack["max_stacked_players"]) for pack in legal_packs]
            ),
            "primary_cost_min": _minimum([_number(option["spp_cost"]) for option in primary]),
            "secondary_present": float(bool(secondary)),
            "secondary_cost_min": _minimum(
                [_number(option["spp_cost"]) for option in secondary]
            ),
            "star_present": float(bool(stars)),
            "star_quantity_max": _maximum(
                [_number(option["max_quantity"]) for option in stars]
            ),
            "extra_gold_max": _maximum([_number(option["max_cost"]) for option in extra_gold]),
        }
        key = (link["naf_tournament_id"], _race_key(row["resolved_display_name"]))
        candidates[key].append(values)
    result = {}
    for key, values in candidates.items():
        distinct = {tuple(value[name] for name in FEATURES) for value in values}
        if len(distinct) == 1:
            result[key] = values[0]
    return result, {row["naf_tournament_id"]: row for row in links.values()}


def candidate_connectivity(
    games: list[Game], linked_events: set[str], minimum_coaches: int = 25
) -> tuple[list[dict[str, object]], dict[str, object]]:
    event_coaches: dict[str, set[str]] = defaultdict(set)
    event_matches: Counter[str] = Counter()
    for game in games:
        if game.event not in linked_events:
            continue
        event_matches[game.event] += 1
        event_coaches[game.event].update((game.home_coach, game.away_coach))
    selected = {
        event for event in linked_events if len(event_coaches[event]) >= minimum_coaches
    }
    edges = []
    ordered = sorted(selected, key=int)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            shared = event_coaches[left] & event_coaches[right]
            if shared:
                edges.append(
                    {
                        "left_event_id": left,
                        "right_event_id": right,
                        "shared_coaches": len(shared),
                        "jaccard": len(shared) / len(event_coaches[left] | event_coaches[right]),
                    }
                )
    rows = [
        {
            "event_id": event,
            "match_count": event_matches[event],
            "coach_count": len(event_coaches[event]),
            "direct_degree": sum(
                edge["left_event_id"] == event or edge["right_event_id"] == event
                for edge in edges
            ),
            "shared_coach_memberships": sum(
                int(edge["shared_coaches"])
                for edge in edges
                if edge["left_event_id"] == event or edge["right_event_id"] == event
            ),
        }
        for event in ordered
    ]
    summary = {
        "minimum_coaches": minimum_coaches,
        "event_count": len(selected),
        "match_count": sum(event_matches[event] for event in selected),
        "edge_count": len(edges),
        "isolated_event_count": sum(row["direct_degree"] == 0 for row in rows),
    }
    return rows, {"summary": summary, "edges": edges}


def _training_effects(
    games: list[Game], excluded_events: set[str]
) -> tuple[dict[str, float], dict[str, float]]:
    coach_sum: Counter[str] = Counter()
    coach_n: Counter[str] = Counter()
    race_sum: Counter[str] = Counter()
    race_n: Counter[str] = Counter()
    for game in games:
        if game.event in excluded_events:
            continue
        coach_sum[game.home_coach] += game.home_score
        coach_sum[game.away_coach] += 1.0 - game.home_score
        coach_n[game.home_coach] += 1
        coach_n[game.away_coach] += 1
        race_sum[game.home_race] += game.home_score
        race_sum[game.away_race] += 1.0 - game.home_score
        race_n[game.home_race] += 1
        race_n[game.away_race] += 1
    coach = {key: (coach_sum[key] - 0.5 * n) / (n + 12.0) for key, n in coach_n.items()}
    race = {key: (race_sum[key] - 0.5 * n) / (n + 80.0) for key, n in race_n.items()}
    return coach, race


def residual_cells(
    games: list[Game], selected_events: set[str], race_names: dict[str, str], folds: int = 5
) -> list[dict[str, object]]:
    event_folds = {event: int(event) % folds for event in selected_events}
    accum: dict[tuple[str, str], list[float]] = defaultdict(list)
    for fold in range(folds):
        held_out = {event for event, value in event_folds.items() if value == fold}
        coach, race = _training_effects(games, held_out)
        for game in games:
            if game.event not in held_out:
                continue
            prediction = (
                0.5
                + coach.get(game.home_coach, 0.0)
                - coach.get(game.away_coach, 0.0)
                + race.get(game.home_race, 0.0)
                - race.get(game.away_race, 0.0)
            )
            prediction = min(1.0, max(0.0, prediction))
            residual = game.home_score - prediction
            accum[(game.event, game.home_race)].append(residual)
            accum[(game.event, game.away_race)].append(-residual)
    result = []
    ordered = sorted(accum.items(), key=lambda item: (int(item[0][0]), int(item[0][1])))
    for (event, race_id), values in ordered:
        mean = sum(values) / len(values)
        variance = (
            sum((value - mean) ** 2 for value in values) / (len(values) - 1)
            if len(values) > 1
            else 0.0
        )
        result.append(
            {
                "event_id": event,
                "race_id": race_id,
                "race_name": race_names.get(race_id, race_id),
                "games": len(values),
                "mean_residual": mean,
                "standard_error": math.sqrt(variance / len(values)),
            }
        )
    return result


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, vector, strict=True)]
    for column in range(len(vector)):
        pivot = max(range(column, len(vector)), key=lambda row: abs(augmented[row][column]))
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        if abs(divisor) < 1e-12:
            continue
        for item in range(column, len(vector) + 1):
            augmented[column][item] /= divisor
        for row in range(len(vector)):
            if row == column:
                continue
            factor = augmented[row][column]
            for item in range(column, len(vector) + 1):
                augmented[row][item] -= factor * augmented[column][item]
    return [augmented[index][-1] for index in range(len(vector))]


def _ridge(
    train: list[tuple[list[float], float, float]], size: int, penalty: float = 10.0
) -> list[float]:
    matrix = [[0.0] * size for _ in range(size)]
    vector = [0.0] * size
    for features, target, weight in train:
        for left in range(size):
            vector[left] += weight * features[left] * target
            for right in range(size):
                matrix[left][right] += weight * features[left] * features[right]
    for index in range(size):
        matrix[index][index] += penalty
    return _solve(matrix, vector)


def raw_feature_probe(
    cells: list[dict[str, object]],
    features: dict[tuple[str, str], dict[str, float]],
    feature_names: tuple[str, ...] = FEATURES,
) -> dict[str, object]:
    usable = [
        cell
        for cell in cells
        if int(cell["games"]) >= 4
        and (str(cell["event_id"]), _race_key(str(cell["race_name"]))) in features
    ]
    events = sorted({str(cell["event_id"]) for cell in usable}, key=int)
    squared_model: dict[str, list[float]] = defaultdict(list)
    squared_base: dict[str, list[float]] = defaultdict(list)
    coefficients: list[list[float]] = []
    for held_out in events:
        training_cells = [cell for cell in usable if str(cell["event_id"]) != held_out]
        race_target: dict[str, list[float]] = defaultdict(list)
        race_feature: dict[str, list[list[float]]] = defaultdict(list)
        for cell in training_cells:
            race_key = _race_key(str(cell["race_name"]))
            race_target[race_key].append(float(cell["mean_residual"]))
            race_feature[race_key].append(
                [features[(str(cell["event_id"]), race_key)][name] for name in feature_names]
            )
        target_mean = {key: sum(values) / len(values) for key, values in race_target.items()}
        feature_mean = {
            key: [sum(row[i] for row in rows) / len(rows) for i in range(len(feature_names))]
            for key, rows in race_feature.items()
        }
        scales = []
        for index in range(len(feature_names)):
            values = [
                features[(str(cell["event_id"]), _race_key(str(cell["race_name"])))][
                    feature_names[index]
                ]
                - feature_mean[_race_key(str(cell["race_name"]))][index]
                for cell in training_cells
            ]
            scale = math.sqrt(sum(value * value for value in values) / max(1, len(values)))
            scales.append(scale or 1.0)
        train = []
        for cell in training_cells:
            key = _race_key(str(cell["race_name"]))
            raw = features[(str(cell["event_id"]), key)]
            x = [
                (raw[name] - feature_mean[key][i]) / scales[i]
                for i, name in enumerate(feature_names)
            ]
            train.append((x, float(cell["mean_residual"]) - target_mean[key], float(cell["games"])))
        beta = _ridge(train, len(feature_names))
        coefficients.append(beta)
        for cell in usable:
            if str(cell["event_id"]) != held_out:
                continue
            key = _race_key(str(cell["race_name"]))
            if key not in target_mean:
                continue
            raw = features[(held_out, key)]
            x = [
                (raw[name] - feature_mean[key][i]) / scales[i]
                for i, name in enumerate(feature_names)
            ]
            target = float(cell["mean_residual"])
            baseline = target_mean[key]
            adjustment = sum(
                value * coefficient for value, coefficient in zip(x, beta, strict=True)
            )
            prediction = baseline + adjustment
            squared_base[held_out].append((target - baseline) ** 2)
            squared_model[held_out].append((target - prediction) ** 2)
    deltas = {
        event: sum(squared_base[event]) / len(squared_base[event])
        - sum(squared_model[event]) / len(squared_model[event])
        for event in squared_model
        if squared_model[event]
    }
    mean_beta = [sum(values) / len(values) for values in zip(*coefficients, strict=True)]
    return {
        "usable_cell_count": len(usable),
        "held_out_event_count": len(deltas),
        "equal_event_mean_mse_improvement": sum(deltas.values()) / len(deltas),
        "events_improved": sum(value > 0 for value in deltas.values()),
        "event_deltas": deltas,
        "features": list(feature_names),
        "mean_standardized_coefficients": dict(zip(feature_names, mean_beta, strict=True)),
    }


def permutation_benchmark(
    cells: list[dict[str, object]],
    features: dict[tuple[str, str], dict[str, float]],
    observed: float,
    feature_names: tuple[str, ...] = FEATURES,
    permutations: int = 199,
) -> dict[str, object]:
    """Shuffle cell outcomes within race and rerun the complete grouped probe."""

    rng = random.Random(20260713)
    by_race: dict[str, list[int]] = defaultdict(list)
    for index, cell in enumerate(cells):
        by_race[_race_key(str(cell["race_name"]))].append(index)
    null = []
    for _ in range(permutations):
        shuffled = [dict(cell) for cell in cells]
        for indices in by_race.values():
            values = [float(cells[index]["mean_residual"]) for index in indices]
            rng.shuffle(values)
            for index, value in zip(indices, values, strict=True):
                shuffled[index]["mean_residual"] = value
        shuffled_result = raw_feature_probe(shuffled, features, feature_names)
        null.append(float(shuffled_result["equal_event_mean_mse_improvement"]))
    return {
        "permutations": permutations,
        "scheme": "shuffle_event_race_cell_residuals_within_race",
        "p_value_one_sided": (1 + sum(value >= observed for value in null))
        / (permutations + 1),
        "null_mean": sum(null) / len(null),
        "null_95th_percentile": sorted(null)[int(0.95 * (len(null) - 1))],
    }


def run(naf_dir: Path, tourplay_dir: Path, resolved_dir: Path, output: Path) -> dict[str, object]:
    games, race_names = _load_games(naf_dir)
    feature_map, links = literal_feature_map(tourplay_dir, resolved_dir)
    candidate_rows, connectivity = candidate_connectivity(games, set(links))
    event_metadata = {row["event_id"]: row for row in _rows(naf_dir / "event.csv")}
    feature_counts = Counter(event for event, _race in feature_map)
    for row in candidate_rows:
        event_id = str(row["event_id"])
        metadata = event_metadata[event_id]
        link = links[event_id]
        row.update(
            {
                "event_name": metadata["name"],
                "start_date": metadata["start_date"],
                "nation": metadata["nation"],
                "is_squad": metadata["is_squad"],
                "tourplay_slug": link["tourplay_slug"],
                "literal_race_feature_count": feature_counts[event_id],
            }
        )
    selected = {str(row["event_id"]) for row in candidate_rows}
    cells = residual_cells(games, selected, race_names)
    probes = {}
    for name, feature_names in (
        ("tier_only", TIER_FEATURES),
        ("resources_only", RESOURCE_FEATURES),
        ("tier_plus_resources", FEATURES),
    ):
        probe = raw_feature_probe(cells, feature_map, feature_names)
        probe["permutation_benchmark"] = permutation_benchmark(
            cells,
            feature_map,
            float(probe["equal_event_mean_mse_improvement"]),
            feature_names,
        )
        probes[name] = probe
    weighted_residual = sum(
        int(cell["games"]) * float(cell["mean_residual"]) ** 2 for cell in cells
    ) / sum(int(cell["games"]) for cell in cells)
    sampling = sum(
        int(cell["games"]) * float(cell["standard_error"]) ** 2 for cell in cells
    ) / sum(int(cell["games"]) for cell in cells)
    report = {
        "status": "exploratory_non_binding",
        "warnings": [
            "Raw Tourplay fields are literal legal-option summaries, not schema-v0 treatments.",
            "Legal alternatives are not realized roster builds.",
            "Exact-linked events are a selected and non-representative subset of NAF events.",
            "Results are predictive reconnaissance, not causal pack-effect estimates.",
        ],
        "connectivity": connectivity["summary"],
        "residual_heterogeneity": {
            "cell_count": len(cells),
            "weighted_rms": math.sqrt(weighted_residual),
            "sampling_adjusted_rms": math.sqrt(max(0.0, weighted_residual - sampling)),
        },
        "feature_probes": probes,
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in (("candidate_events.csv", candidate_rows), ("residual_cells.csv", cells)):
        if rows:
            with (output / name).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    edges = connectivity["edges"]
    if edges:
        with (output / "event_overlap_edges.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(edges[0]))
            writer.writeheader()
            writer.writerows(edges)
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
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
