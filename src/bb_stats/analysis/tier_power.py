"""Conditional W/D/L simulation for the observed relative-tier schedule.

Nuisance predictions are cross-fitted once and held fixed.  This makes the simulation
fast and useful as an optimistic design diagnostic, not a full end-to-end power study.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from bb_stats.analysis.exploratory_signal import _load_games, literal_feature_map
from bb_stats.analysis.tier_signal import (
    _tier_value,
    balanced_event_folds,
    fit_ridge,
    observations,
    predict,
    tier_centers,
)


@dataclass(frozen=True)
class ScheduledMatch:
    event: str
    fold: int
    baseline_score: float
    tier_difference: float
    observed_score: float


def cross_fitted_schedule(
    naf_dir: Path, tourplay_dir: Path, resolved_dir: Path
) -> tuple[list[ScheduledMatch], float]:
    games, race_names = _load_games(naf_dir)
    features, links = literal_feature_map(tourplay_dir, resolved_dir)
    linked_events = set(links)
    folds = balanced_event_folds(games, linked_events)
    scheduled = []
    for fold, held_out in enumerate(folds):
        centers = tier_centers(features, held_out)
        training = observations(games, race_names, features, centers, "baseline", held_out)
        fitted = fit_ridge(training)
        held_games = [game for game in games if game.event in held_out]
        held_rows = observations(
            held_games, race_names, features, centers, "baseline", set()
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
            scheduled.append(
                ScheduledMatch(
                    event=row.game.event,
                    fold=fold,
                    baseline_score=min(1.0, max(0.0, 0.5 + predict(row, fitted))),
                    tier_difference=home_tier - away_tier,
                    observed_score=row.game.home_score,
                )
            )
    draws = sum(game.home_score == 0.5 for game in games) / len(games)
    return scheduled, draws


def sample_score(rng: random.Random, expected_score: float, draw_probability: float) -> float:
    lower = draw_probability / 2
    expected = min(1.0 - lower, max(lower, expected_score))
    win_probability = expected - lower
    loss_probability = 1.0 - draw_probability - win_probability
    value = rng.random()
    if value < loss_probability:
        return 0.0
    if value < loss_probability + draw_probability:
        return 0.5
    return 1.0


def tier_statistic(schedule: list[ScheduledMatch], outcomes: list[float]) -> dict[str, float]:
    event_errors: dict[str, list[tuple[float, float]]] = defaultdict(list)
    coefficients = []
    for fold in sorted({match.fold for match in schedule}):
        training = [index for index, match in enumerate(schedule) if match.fold != fold]
        numerator = sum(
            schedule[index].tier_difference
            * (outcomes[index] - schedule[index].baseline_score)
            for index in training
        )
        denominator = 10.0 + sum(
            schedule[index].tier_difference**2 for index in training
        )
        coefficient = numerator / denominator
        coefficients.append(coefficient)
        for index, match in enumerate(schedule):
            if match.fold != fold:
                continue
            base_error = (outcomes[index] - match.baseline_score) ** 2
            tier_prediction = match.baseline_score + coefficient * match.tier_difference
            tier_error = (outcomes[index] - tier_prediction) ** 2
            event_errors[match.event].append((base_error, tier_error))
    deltas = []
    for errors in event_errors.values():
        deltas.append(sum(base - tier for base, tier in errors) / len(errors))
    return {
        "equal_event_mse_improvement": sum(deltas) / len(deltas),
        "mean_coefficient": sum(coefficients) / len(coefficients),
        "events_improved": float(sum(delta > 0 for delta in deltas)),
    }


def simulate(
    schedule: list[ScheduledMatch],
    draw_probability: float,
    effects: tuple[float, ...] = (0.0, 0.01, 0.025, 0.05, 0.1),
    repetitions: int = 500,
) -> dict[str, object]:
    results: dict[float, list[dict[str, float]]] = defaultdict(list)
    for effect_index, effect in enumerate(effects):
        rng = random.Random(20260713 + effect_index)
        for _ in range(repetitions):
            outcomes = [
                sample_score(
                    rng,
                    match.baseline_score + effect * match.tier_difference,
                    draw_probability,
                )
                for match in schedule
            ]
            results[effect].append(tier_statistic(schedule, outcomes))
    null = sorted(item["equal_event_mse_improvement"] for item in results[0.0])
    threshold = null[int(0.95 * (len(null) - 1))]
    summaries = {}
    for effect, items in results.items():
        improvements = [item["equal_event_mse_improvement"] for item in items]
        coefficients = [item["mean_coefficient"] for item in items]
        summaries[str(effect)] = {
            "mean_mse_improvement": sum(improvements) / len(improvements),
            "mean_recovered_coefficient": sum(coefficients) / len(coefficients),
            "detection_probability": sum(value > threshold for value in improvements)
            / len(improvements),
        }
    return {
        "repetitions_per_effect": repetitions,
        "null_95th_percentile": threshold,
        "effects": summaries,
    }


def run(naf_dir: Path, tourplay_dir: Path, resolved_dir: Path, output: Path) -> dict[str, object]:
    schedule, draw_probability = cross_fitted_schedule(naf_dir, tourplay_dir, resolved_dir)
    observed = tier_statistic(schedule, [match.observed_score for match in schedule])
    simulation = simulate(schedule, draw_probability)
    report = {
        "status": "exploratory_conditional_power",
        "schedule_matches": len(schedule),
        "schedule_events": len({match.event for match in schedule}),
        "draw_probability": draw_probability,
        "observed_two_stage_statistic": observed,
        "simulation": simulation,
        "warnings": [
            "Nuisance predictions are cross-fitted once and fixed, making power optimistic.",
            "Draw probability is constant; the generator does not model race-specific draw rates.",
            "Tier remains predictive organizer judgment, not a causal treatment.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "tier_power.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
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
