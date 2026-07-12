import csv
import io
import json
import zipfile
from pathlib import Path

from bb_stats.analysis.tourplay_coverage import (
    ExactLink,
    classify_metadata,
    extract_exact_links,
    fetch_metadata,
    normalize_tourplay_url,
)


def _csv(headers: list[str], rows: list[list[str]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def _zip(path: Path) -> None:
    tournaments = _csv(
        [
            "tournamentid", "tournamentname", "naf_variantsid", "tournamenturl",
            "tournamentnotesurl", "tournamentinformation",
        ],
        [
            ["1", "Exact", "15", "HTTPS://TOURPLAY.NET/EN/blood-bowl/My_Event/news/", "", ""],
            [
                "2", "In text", "15", "", "",
                "Pack: https://www.tourplay.net/es/blood-bowl/second-event?x=1",
            ],
            ["3", "Wrong variant", "8", "https://tourplay.net/en/blood-bowl/old", "", ""],
            [
                "4", "No recorded game", "15",
                "https://tourplay.net/blood-bowl/future/settings", "", "",
            ],
        ],
    )
    games = _csv(
        ["tournamentid", "naf_variantsid"],
        [["1", "15"], ["2", "15"], ["3", "8"]],
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("dump/naf_tournament.csv", tournaments)
        archive.writestr("dump/naf_game.csv", games)


def test_normalize_tourplay_url() -> None:
    assert normalize_tourplay_url(
        "x https://TourPlay.net/en-GB/blood-bowl/A_TEST/classifications/?a=1"
    ) == [("a-test", "https://tourplay.net/en/blood-bowl/a-test")]
    assert normalize_tourplay_url(
        "https://tourplay.net/es/blood-bowl/ii-c ... owl-girona"
    ) == []


def test_extract_exact_links_from_synthetic_zip(tmp_path: Path) -> None:
    source = tmp_path / "naf.zip"
    _zip(source)
    links = extract_exact_links(source)
    actual = [
        (link.naf_tournament_id, link.tourplay_slug, link.evidence_field)
        for link in links
    ]
    assert actual == [
        ("1", "my-event", "tournamenturl"),
        ("2", "second-event", "tournamentinformation"),
    ]
    all_events = extract_exact_links(source, recorded_games_only=False)
    assert [link.tourplay_slug for link in all_events] == ["my-event", "second-event", "future"]


def _payload(pack_count: int = 1) -> dict[str, object]:
    packs = [
        {
            "id": index,
            "maxStackedPlayers": 2,
            "options": [{"improvementPackType": 0, "sppCost": 20, "maxStackQuantity": 1}],
        }
        for index in range(pack_count)
    ]
    return {
        "id": 99,
        "categories": [{
            "tiers": [{
                "treasuryBudget": 1100,
                "teamRaces": [3001, 3002],
                "inducements": [141],
                "improvementPacks": packs,
            }],
        }],
    }


def test_classification_single_and_choice_set_are_both_direct() -> None:
    direct = classify_metadata(_payload())
    assert direct["legal_pack_mapping"] == "direct"
    assert direct["pack_choice_structure"] == "single_only"
    assert direct["has_skill_costs"] is True
    assert direct["has_stacking"] is True
    multiple = classify_metadata(_payload(2))
    assert multiple["legal_pack_mapping"] == "direct"
    assert multiple["pack_choice_structure"] == "choice_set"
    assert multiple["has_multiple_pack_choices"] is True


def test_skill_cost_and_star_detection_are_semantic() -> None:
    payload = _payload()
    option = payload["categories"][0]["tiers"][0]["improvementPacks"][0]["options"][0]
    option.pop("sppCost")
    option["maxCost"] = 0
    assert classify_metadata(payload)["has_skill_costs"] is False
    option["improvementPackType"] = 11
    assert classify_metadata(payload)["has_stars"] is True


def _link(slug: str) -> ExactLink:
    return ExactLink(
        "1", "Event", slug, f"https://tourplay.net/en/blood-bowl/{slug}",
        "tournamenturl",
    )


def test_fetch_uses_cache_and_deduplicates_slugs(tmp_path: Path) -> None:
    calls: list[str] = []
    seen_headers: list[object] = []

    def transport(url: str, headers: object) -> tuple[int, bytes]:
        calls.append(url)
        seen_headers.append(headers)
        return 200, json.dumps(_payload()).encode()

    rows = fetch_metadata(
        [_link("one"), ExactLink("2", "Other", "one", "x", "tournamentinformation")],
        tmp_path, delay_seconds=0, transport=transport,
    )
    assert len(calls) == 1
    assert seen_headers[0]["Sec-Fetch-Mode"] == "cors"
    assert seen_headers[0]["Referer"].endswith("/one")
    assert [row["fetch_state"] for row in rows] == ["fetched", "fetched"]
    assert (tmp_path / "one.json").exists()
    def must_not_fetch(*_args: object) -> tuple[int, bytes]:
        raise AssertionError

    fetch_metadata([_link("one")], tmp_path, transport=must_not_fetch)


def test_cached_success_breaks_consecutive_block_sequence(tmp_path: Path) -> None:
    (tmp_path / "middle.json").write_text(json.dumps(_payload()), encoding="utf-8")
    calls: list[str] = []

    def blocked(url: str, _headers: object) -> tuple[int, bytes]:
        calls.append(url)
        return 423, b""

    rows = fetch_metadata(
        [_link("first"), _link("middle"), _link("last")],
        tmp_path,
        stop_after_blocked=2,
        delay_seconds=0,
        transport=blocked,
    )
    assert len(calls) == 2
    assert [row["http_status"] for row in rows] == [423, 200, 423]


def test_fetch_stops_after_consecutive_blocks_and_never_retries(tmp_path: Path) -> None:
    calls: list[str] = []
    sleeps: list[float] = []

    def blocked(url: str, _headers: object) -> tuple[int, bytes]:
        calls.append(url)
        return 423, b""

    rows = fetch_metadata(
        [_link("a"), _link("b"), _link("c")], tmp_path,
        stop_after_blocked=2, delay_seconds=0.25, transport=blocked, sleep=sleeps.append,
    )
    assert len(calls) == 2
    assert sleeps == [0.25]
    assert [row["fetch_state"] for row in rows] == ["http_error", "http_error", "not_fetched_limit"]


def test_transport_failures_count_toward_early_stop(tmp_path: Path) -> None:
    def unavailable(_url: str, _headers: object) -> tuple[int, bytes]:
        return 599, b""

    rows = fetch_metadata(
        [_link("a"), _link("b")],
        tmp_path,
        stop_after_blocked=1,
        delay_seconds=0,
        transport=unavailable,
    )
    assert [row["http_status"] for row in rows] == [599, 0]
