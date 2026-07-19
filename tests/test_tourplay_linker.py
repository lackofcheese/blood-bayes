import csv
from pathlib import Path

from bb_stats.analysis.tourplay_linker import name_similarity, normalize


def test_normalize_can_remove_year_without_destroying_series() -> None:
    assert normalize("Danish Open (Danish National 2026)", True) == (
        "danish open danish national"
    )


def test_name_similarity_handles_year_and_punctuation() -> None:
    assert name_similarity("Waterbowl 2026", "Water Bowl - 2026") > 0.85
    assert name_similarity("REVA17", "Completely Different Cup") < 0.3


def test_curated_review_registry_is_reconciled() -> None:
    root = Path(__file__).parents[1]
    with (root / "data/curated/tourplay_link_review.csv").open(newline="") as handle:
        reviews = list(csv.DictReader(handle))
    with (root / "data/curated/tourplay_reviewed_details.csv").open(newline="") as handle:
        details = list(csv.DictReader(handle))
    with (root / "data/curated/tourplay_wave2_plan.csv").open(newline="") as handle:
        wave2_plan = list(csv.DictReader(handle))
    with (root / "data/curated/tourplay_wave2_review.csv").open(newline="") as handle:
        wave2_review = list(csv.DictReader(handle))
    with (root / "data/curated/tourplay_wave2_details.csv").open(newline="") as handle:
        wave2_details = list(csv.DictReader(handle))
    assert len(reviews) == 30
    assert len({row["naf_event_id"] for row in reviews}) == len(reviews)
    assert all(bool(row["tourplay_slug"]) == (row["decision"] == "linked") for row in reviews)
    reviewed_links = {
        (row["naf_event_id"], row["tourplay_slug"])
        for row in reviews
        if row["decision"] == "linked"
    }
    assert all(
        (row["naf_event_id"], row["tourplay_slug"]) in reviewed_links for row in details
    )
    assert all(row["http_status"] == "200" for row in details)
    assert len(wave2_plan) == len(wave2_review) == 20
    assert {row["naf_event_id"] for row in wave2_plan} == {
        row["naf_event_id"] for row in wave2_review
    }
    assert all(row["decision"] == "linked" for row in wave2_review)
    assert len(wave2_details) == 20
    assert {row["naf_event_id"] for row in wave2_details} == {
        row["naf_event_id"] for row in wave2_review
    }
    assert all(row["http_status"] == "200" for row in wave2_details)
