from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

from bb_stats.analysis.event_catalog import (
    CATALOG_FIELDS,
    build_catalog,
    repeat_series_key,
    write_catalog,
)


def _csv(rows: list[list[str]]) -> bytes:
    output = io.StringIO(newline="")
    csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL).writerows(rows)
    return output.getvalue().encode()


def _synthetic_zip(path: Path) -> None:
    tournaments = [
        [
            "tournamentid",
            "tournamentname",
            "tournamentcity",
            "tournamentnation",
            "tournamenturl",
            "tournamentnotesurl",
            "tournamentstartdate",
            "tournamentenddate",
            "tournamenttype",
            "tournamentscoring",
            "tournamentinformation",
            "tournamentemail",
            "tournamentcontact",
            "tournamentaddress1",
            "tournament_squad",
            "geolongitude",
            "geolattitude",
            "naf_variantsid",
            "tournament_ruleset_file",
        ],
        [
            "1", "Example Cup 2025", "Brisbane", "Australia", "https://event", "",
            "2025-01-01", "2025-01-02", "OPEN", "2/1/0", "rules",
            "secret@example.test", "Person", "Private street", "0", "1", "2", "15",
            "pack.pdf",
        ],
        [
            "2", "Example Cup 2026", "Sydney", "Australia", "", "https://notes",
            "2026-01-01", "2026-01-02", "INVITE", "", "", "other@example.test",
            "Other", "Other street", "1", "3", "4", "15", "",
        ],
        [
            "3", "Old Cup", "London", "UK", "", "", "2020-01-01", "2020-01-02",
            "OPEN", "", "", "", "", "", "0", "", "", "13", "",
        ],
    ]
    entrants = [
        ["naftournament", "nafcoach", "race"],
        ["1", "private-a", "1"],
        ["1", "private-b", "2"],
        ["1", "private-no-show", "99"],
        ["2", "private-b", "2"],
        ["2", "private-c", "3"],
        ["3", "private-a", "1"],
    ]
    games = [
        [
            "gameid", "tournamentid", "naf_variantsid", "homecoachid", "awaycoachid",
            "racehome", "raceaway",
        ],
        ["g1", "1", "15", "private-a", "private-b", "1", "2"],
        ["g2", "1", "15", "private-b", "private-a", "2", "1"],
        ["g3", "2", "15", "private-b", "private-c", "2", "3"],
        ["g4", "3", "13", "private-a", "private-old", "1", "4"],
    ]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("dump/naf_tournament.csv", _csv(tournaments))
        archive.writestr("dump/naf_tournamentcoach.csv", _csv(entrants))
        archive.writestr("dump/naf_game.csv", _csv(games))


def test_repeat_series_key_is_explicitly_name_and_year_based() -> None:
    assert repeat_series_key("Café Cup 2025") == "cafe cup"
    assert repeat_series_key("Café Cup 2026") == "cafe cup"


def test_catalog_aggregates_overlap_without_exposing_coaches(tmp_path: Path) -> None:
    source = tmp_path / "naf.zip"
    _synthetic_zip(source)
    rows, summary = build_catalog(source)

    assert len(rows) == 2
    by_id = {row["event_id"]: row for row in rows}
    assert by_id["1"]["match_count"] == "2"
    assert by_id["1"]["coach_count"] == "2"
    assert by_id["1"]["race_count"] == "2"
    assert by_id["1"]["registered_entry_count"] == "3"
    assert by_id["1"]["registered_coach_count"] == "3"
    assert by_id["1"]["registered_race_count"] == "3"
    assert by_id["1"]["overlap_event_degree"] == "1"
    assert by_id["1"]["max_shared_coaches_with_one_event"] == "1"
    assert by_id["2"]["connectivity_component_size"] == "2"
    assert by_id["1"]["repeat_series_event_count_heuristic"] == "2"
    assert by_id["1"]["has_ruleset_file_reference"] == "true"
    assert summary["unique_coach_count"] == 3
    assert summary["connectivity_component_count"] == 1

    serialized = json.dumps({"rows": rows, "summary": summary})
    secrets = (
        "private-a",
        "private-b",
        "private-c",
        "secret@example.test",
        "Private street",
    )
    for secret in (*secrets, "private-no-show"):
        assert secret not in serialized
    assert tuple(rows[0]) == CATALOG_FIELDS


def test_write_catalog_creates_deterministic_safe_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "naf.zip"
    output = tmp_path / "out"
    _synthetic_zip(source)
    write_catalog(source, output)

    first = (output / "candidate_events.csv").read_bytes()
    write_catalog(source, output)
    assert (output / "candidate_events.csv").read_bytes() == first
    assert (output / "connectivity_summary.json").exists()
    markdown = (output / "connectivity_summary.md").read_text()
    assert "not verified tournament-pack linkage" in markdown
    assert "private-a" not in markdown
