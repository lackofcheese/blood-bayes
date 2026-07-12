"""Match-level exploratory test of relative Tourplay tier signal.

This is deliberately simpler than the planned thesis gate.  It uses an antisymmetric
ridge linear-probability model, grouped event folds, and literal relative tier only.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from bb_stats.analysis.exploratory_signal import (
    Game,
    _load_games,
    _race_key,
    literal_feature_map,
)

Parameter = tuple[str, str]


@dataclass(frozen=True)
class Observation:
    game: Game
    target: float
    columns: tuple[tuple[Parameter, float], ...]


def balanced_event_folds(games: list[Game], events: set[str], folds: int = 5) -> list[set[str]]:
    counts = Counter(game.event for game in games if game.event in events)
    result = [set() for _ in range(folds)]
    totals = [0] * folds
    for event in sorted(events, key=lambda item: (-counts[item], int(item))):
        index = min(range(folds), key=lambda item: (totals[item], item))
        result[index].add(event)
        totals[index] += counts[event]
    return result


def tier_centers(
    features: dict[tuple[str, str], dict[str, float]], excluded_events: set[str]
) -> dict[str, float]:
    values: dict[str, list[float]] = defaultdict(list)
    for (event, race), feature in features.items():
        if event not in excluded_events:
            values[race].append(feature["relative_tier"])
    return {race: sum(items) / len(items) for race, items in values.items()}


def _tier_value(
    game: Game,
    race_id: str,
    race_names: dict[str, str],
    features: dict[tuple[str, str], dict[str, float]],
    centers: dict[str, float],
) -> float | None:
    race = _race_key(race_names.get(race_id, race_id))
    feature = features.get((game.event, race))
    if feature is None or race not in centers:
        return None
    return feature["relative_tier"] - centers[race]


def observations(
    games: list[Game],
    race_names: dict[str, str],
    features: dict[tuple[str, str], dict[str, float]],
    centers: dict[str, float],
    model: str,
    excluded_events: set[str],
    injection: float = 0.0,
    supported_races: set[str] | None = None,
    include_coach_race: bool = False,
) -> list[Observation]:
    result = []
    for game in games:
        if game.event in excluded_events:
            continue
        columns: list[tuple[Parameter, float]] = [
            (("coach", game.home_coach), 1.0),
            (("coach", game.away_coach), -1.0),
            (("race", game.home_race), 1.0),
            (("race", game.away_race), -1.0),
        ]
        if include_coach_race:
            columns.extend(
                (
                    (("coach_race", f"{game.home_coach}:{game.home_race}"), 1.0),
                    (("coach_race", f"{game.away_coach}:{game.away_race}"), -1.0),
                )
            )
        home_tier = _tier_value(game, game.home_race, race_names, features, centers)
        away_tier = _tier_value(game, game.away_race, race_names, features, centers)
        tier_difference = 0.0
        if home_tier is not None and away_tier is not None:
            tier_difference = home_tier - away_tier
            if model == "common":
                columns.append((("tier", "common"), tier_difference))
            if model == "heterogeneous":
                if supported_races is None or game.home_race in supported_races:
                    columns.append((("tier_race", game.home_race), home_tier))
                if supported_races is None or game.away_race in supported_races:
                    columns.append((("tier_race", game.away_race), -away_tier))
        target = game.home_score - 0.5 + injection * tier_difference
        result.append(Observation(game, target, tuple(columns)))
    return result


def _penalty(parameter: Parameter) -> float:
    return {
        "coach": 12.0,
        "coach_race": 30.0,
        "race": 80.0,
        "tier": 10.0,
        "tier_race": 80.0,
    }[parameter[0]]


def fit_ridge(
    rows: list[Observation], iterations: int = 30, tolerance: float = 1e-9
) -> dict[Parameter, float]:
    """Fit a sparse ridge model by exact cyclic coordinate updates."""

    columns: dict[Parameter, list[tuple[int, float]]] = defaultdict(list)
    for index, row in enumerate(rows):
        for parameter, value in row.columns:
            if value:
                columns[parameter].append((index, value))
    coefficients = {parameter: 0.0 for parameter in columns}
    residuals = [row.target for row in rows]
    ordered = sorted(columns)
    for _ in range(iterations):
        largest_change = 0.0
        for parameter in ordered:
            old = coefficients[parameter]
            entries = columns[parameter]
            numerator = sum(value * (residuals[index] + value * old) for index, value in entries)
            denominator = _penalty(parameter) + sum(value * value for _index, value in entries)
            new = numerator / denominator
            change = new - old
            if change:
                coefficients[parameter] = new
                for index, value in entries:
                    residuals[index] -= value * change
                largest_change = max(largest_change, abs(change))
        if largest_change < tolerance:
            break
    return coefficients


def predict(row: Observation, coefficients: dict[Parameter, float]) -> float:
    return sum(coefficients.get(parameter, 0.0) * value for parameter, value in row.columns)


def _evaluate(
    rows: list[Observation], coefficients: dict[Parameter, float]
) -> tuple[float, int]:
    squared = [(row.target - predict(row, coefficients)) ** 2 for row in rows]
    return sum(squared), len(squared)


def cross_validate(
    games: list[Game],
    race_names: dict[str, str],
    features: dict[tuple[str, str], dict[str, float]],
    linked_events: set[str],
    injection: float = 0.0,
    include_coach_race: bool = False,
) -> dict[str, object]:
    event_folds = balanced_event_folds(games, linked_events)
    event_counts = Counter()
    event_errors: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    tier_coefficients = []
    deviation_scales = []
    for held_out in event_folds:
        centers = tier_centers(features, held_out)
        race_event_support: dict[str, set[str]] = defaultdict(set)
        for (event, race_name) in features:
            if event not in held_out:
                race_event_support[race_name].add(event)
        supported_names = {
            race for race, events in race_event_support.items() if len(events) >= 5
        }
        supported_races = {
            race_id
            for race_id, race_name in race_names.items()
            if _race_key(race_name) in supported_names
        }
        fitted = {}
        for model in ("baseline", "common", "heterogeneous"):
            train = observations(
                games,
                race_names,
                features,
                centers,
                model,
                held_out,
                injection,
                supported_races,
                include_coach_race,
            )
            fitted[model] = fit_ridge(train)
        tier_coefficients.append(fitted["common"].get(("tier", "common"), 0.0))
        deviations = [
            value
            for (kind, _key), value in fitted["heterogeneous"].items()
            if kind == "tier_race"
        ]
        deviation_scales.append(
            math.sqrt(sum(value * value for value in deviations) / len(deviations))
            if deviations
            else 0.0
        )
        for model in ("baseline", "common", "heterogeneous"):
            held_rows = observations(
                [game for game in games if game.event in held_out],
                race_names,
                features,
                centers,
                model,
                set(),
                injection,
                supported_races,
                include_coach_race,
            )
            for row in held_rows:
                home_tier = _tier_value(
                    row.game, row.game.home_race, race_names, features, centers
                )
                away_tier = _tier_value(
                    row.game, row.game.away_race, race_names, features, centers
                )
                if home_tier is None or away_tier is None:
                    continue
                event_counts[row.game.event] += model == "baseline"
                error = (row.target - predict(row, fitted[model])) ** 2
                event_errors[row.game.event][model].append(error)
    event_results = {}
    for event, errors in event_errors.items():
        means = {model: sum(values) / len(values) for model, values in errors.items()}
        event_results[event] = {
            "matches": event_counts[event],
            "baseline_mse": means["baseline"],
            "common_improvement": means["baseline"] - means["common"],
            "heterogeneous_improvement": means["baseline"] - means["heterogeneous"],
        }
    summary = {}
    event_coaches: dict[str, set[str]] = defaultdict(set)
    for game in games:
        if game.event in event_results:
            event_coaches[game.event].update((game.home_coach, game.away_coach))
    for threshold in (0, 25, 40, 60):
        eligible = [
            value
            for event, value in event_results.items()
            if value["matches"] > 0
            and len(event_coaches[event]) >= threshold
        ]
        summary[str(threshold)] = {
            "event_count": len(eligible),
            "common_mean_improvement": sum(item["common_improvement"] for item in eligible)
            / len(eligible),
            "common_match_weighted_improvement": sum(
                item["matches"] * item["common_improvement"] for item in eligible
            )
            / sum(item["matches"] for item in eligible),
            "common_events_improved": sum(item["common_improvement"] > 0 for item in eligible),
            "heterogeneous_mean_improvement": sum(
                item["heterogeneous_improvement"] for item in eligible
            )
            / len(eligible),
            "heterogeneous_match_weighted_improvement": sum(
                item["matches"] * item["heterogeneous_improvement"] for item in eligible
            )
            / sum(item["matches"] for item in eligible),
            "heterogeneous_events_improved": sum(
                item["heterogeneous_improvement"] > 0 for item in eligible
            ),
        }
    return {
        "injected_effect": injection,
        "include_coach_race": include_coach_race,
        "evaluable_event_count": len(event_results),
        "evaluable_match_count": sum(event_counts.values()),
        "mean_common_tier_coefficient": sum(tier_coefficients) / len(tier_coefficients),
        "mean_race_deviation_rms": sum(deviation_scales) / len(deviation_scales),
        "threshold_summaries": summary,
        "events": event_results,
    }


def run(naf_dir: Path, tourplay_dir: Path, resolved_dir: Path, output: Path) -> dict[str, object]:
    games, race_names = _load_games(naf_dir)
    features, links = literal_feature_map(tourplay_dir, resolved_dir)
    linked_events = set(links)
    observed = cross_validate(games, race_names, features, linked_events)
    coach_race_sensitivity = cross_validate(
        games, race_names, features, linked_events, include_coach_race=True
    )
    rehearsal = [
        cross_validate(games, race_names, features, linked_events, injection=effect)
        for effect in (0.025, 0.05, 0.1)
    ]
    report = {
        "status": "exploratory_non_binding",
        "model": "antisymmetric ridge linear probability",
        "warnings": [
            "Relative tier is organizer judgment and compensation, not a causal treatment.",
            "The injection rehearsal measures recovery amid observed noise; it is not power.",
            "All preprocessing and coefficient fitting exclude complete held-out events.",
        ],
        "observed": observed,
        "coach_race_sensitivity": coach_race_sensitivity,
        "injection_rehearsal": rehearsal,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "tier_signal.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
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
