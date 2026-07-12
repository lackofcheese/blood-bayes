from bb_stats.analysis.exploratory_signal import Game
from bb_stats.analysis.tier_signal import Observation, balanced_event_folds, fit_ridge, predict


def test_balanced_event_folds_keep_events_whole() -> None:
    games = [
        Game(str(event), f"h{event}", f"a{event}", "1", "2", 1.0)
        for event in range(1, 11)
        for _ in range(event)
    ]
    folds = balanced_event_folds(games, {str(event) for event in range(1, 11)}, folds=3)
    assert set().union(*folds) == {str(event) for event in range(1, 11)}
    assert sum(len(fold) for fold in folds) == 10


def test_sparse_ridge_recovers_antisymmetric_signal() -> None:
    parameter = ("tier", "common")
    rows = [
        Observation(Game("1", "a", "b", "1", "2", 1.0), 0.2, ((parameter, 1.0),)),
        Observation(Game("1", "b", "a", "2", "1", 0.0), -0.2, ((parameter, -1.0),)),
    ] * 100
    fitted = fit_ridge(rows)
    assert 0.18 < fitted[parameter] < 0.2
    assert predict(rows[0], fitted) == -predict(rows[1], fitted)
