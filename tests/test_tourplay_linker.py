from bb_stats.analysis.tourplay_linker import name_similarity, normalize


def test_normalize_can_remove_year_without_destroying_series() -> None:
    assert normalize("Danish Open (Danish National 2026)", True) == (
        "danish open danish national"
    )


def test_name_similarity_handles_year_and_punctuation() -> None:
    assert name_similarity("Waterbowl 2026", "Water Bowl - 2026") > 0.85
    assert name_similarity("REVA17", "Completely Different Cup") < 0.3
