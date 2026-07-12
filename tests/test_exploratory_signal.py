from bb_stats.analysis.exploratory_signal import Game, _race_key, candidate_connectivity


def test_race_key_applies_reviewed_alias() -> None:
    assert _race_key("Elf Union") == "elven union"
    assert _race_key("Shambling  Undead") == "shambling undead"


def test_candidate_connectivity_uses_direct_selected_event_overlap() -> None:
    games = [
        Game("1", "a", "b", "1", "2", 1.0),
        Game("2", "b", "c", "1", "2", 0.5),
        Game("3", "x", "y", "1", "2", 0.0),
    ]
    rows, result = candidate_connectivity(games, {"1", "2", "3"}, minimum_coaches=2)
    assert result["summary"]["event_count"] == 3
    assert result["summary"]["edge_count"] == 1
    assert result["summary"]["isolated_event_count"] == 1
    assert {row["event_id"] for row in rows} == {"1", "2", "3"}
