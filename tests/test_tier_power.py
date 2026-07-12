import random

from bb_stats.analysis.tier_power import ScheduledMatch, sample_score, tier_statistic


def test_sample_score_respects_extreme_expected_score() -> None:
    rng = random.Random(1)
    low = [sample_score(rng, 0.0, 0.2) for _ in range(1000)]
    high = [sample_score(rng, 1.0, 0.2) for _ in range(1000)]
    assert abs(sum(low) / len(low) - 0.1) < 0.03
    assert abs(sum(high) / len(high) - 0.9) < 0.03


def test_tier_statistic_recovers_injected_linear_signal() -> None:
    schedule = [
        ScheduledMatch(str(index), index % 5, 0.5, (-1.0) ** index, 0.5)
        for index in range(100)
    ]
    outcomes = [match.baseline_score + 0.1 * match.tier_difference for match in schedule]
    result = tier_statistic(schedule, outcomes)
    assert 0.08 < result["mean_coefficient"] < 0.1
    assert result["equal_event_mse_improvement"] > 0
